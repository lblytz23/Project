from collections import OrderedDict
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Union

import psutil
import tensorflow as tf
import tensorflow_datasets as tfds
from omegaconf import DictConfig
from packaging import version

from .decoder.dataaug_params import DataaugParamHolder
from .decoder.disparity import DisparityDecoder
from .decoder.environment import EnvironmentDecoder
from .decoder.image import ImageDecoder
from .decoder.semesage import SemesageDecoder
from .decoder.ssd import SSDDecoder
from .decoder.yolo import YOLODecoder
from .encode import DatasetBuilder

def model_type_to_decoder(model_type: str):
    _DECODER_TBL = {
        "image": ImageDecoder,
        "semseg": SemesageDecoder,
        "SSD": SSDDecoder,
        "disp": DisparityDecoder,
        "YOLO": YOLODecoder,
        "env": EnvironmentDecoder,
        "debris": SemesageDecoder,
    }
    return _DECODER_TBL[model_type]

class DatasetDecoder:
    SHUFFLE_BUFFER_DIV = 4  # シャッフル用バッファサイズ決め用
    SHUFFLE_BUFFER_TH = 10000  # シャッフル用バッファ閾値

    def __init__(
        self,
        config: Union[Dict[str, Any], DictConfig],
        outputs: List[str],
        dataset_path: str,
        normalize_mode: str = "training",
        for_training_label: bool = False,
        use_condition_input: bool = False,
        random_condition_input: bool = False,
    ) -> None:
        # モデル用のデータセット読み込み用(読み込み用&モデル用config)
        self.config = config["model"]["input"]["name"]
        self.outputs = outputs
        self.dataaug_config = dict()

        # データセットに含まれる情報、モデル用の形状の内容かどうかを一先着確認
        self.use_condition_input = use_condition_input
        self.random_condition_input = random_condition_input

        self.ds_task_cfg = {
            "task_name": config["dataset_map"]["task_name"] for task_name in self.outputs
        }
        self.ds_builder = DatasetBuilder(
            config["dataset_info"]["name"], config["dataset_info"]["version"], dataset_path, self.ds_task_cfg
        )
        ds_info = self.ds_builder.info

        # データセット情報(サイズ) = データの入力サイズ計算用
        input_data_feat = ds_info.features[self.input_names[0]]
        input_data_shape = (input_data_feat.shape[0], input_data_feat.shape[1])

        shape = config["model"]["input"]["shape"]
        padded_h = (shape[0] + (os - shape[0] % os) % os)
        padded_w = (shape[1] + (os - shape[1] % os) % os)
        self.model_input_size = (padded_h, padded_w)

        self.model_task_cfg = dict()
        self.decoder_dict = dict()
        # DA用function設定(モデルごとのタスク分)
        for task_name in self.input_names:
            model_task_cfg = config["dataset_map"]["task_name"]["preproc_function"]["args"]
            self.model_task_cfg[task_name] = model_task_cfg
        self.decoder_dict[task_name] = model_type_to_decoder("image")(
            task_name=task_name,
            ds_preproc_args=ds_preproc_args,
            model_config=model_task_cfg,
            normalize_mode=normalize_mode,
        )

    @property
    def info(self):
        # データセットの情報, 各labelのshapeやsplit毎のデータ数等
        return self.ds_builder.info


    def _set_dataset_options(self, dataset):
        # 下記のdataset optionの内から、dataset loading最適化に有効な
        # 从以下的dataset选项中选择，有效优化数据加载。
        # https://github.com/google-research/simclr/blob/ceb0a5839afecbc2ee18f1d76c3f2/tf2/data.py#L79-L82
        # https://www.tensorflow.org/guide/data_performance_analysis#g3_are_you_reaching_high_cpu_utilization
        # (参考链接，查看高CPU使用率的分析方法)
        if version.parse(tf.__version__) < version.parse("2.4.0"):
            options = tf.data.Options()
            if version.parse(tf.__version__) < version.parse("2.2.0"):
                options.experimental_distribute.auto_shard_policy = tf.data.experimental.AutoShardPolicy.OFF
            dataset = dataset.with_options(options)

        return dataset

    def _get_da_param(self, samples, da_config, for_training_dataaug):
        # DA用パラメタ決め、各labelに同じDAの設定を与えるようにする
        # 设置用于DA的参数，确保对每个标签应用相同的DA设置。
        disparity_os = None
        for task_name, model_task_cfg in self.model_task_cfg.items():
            if model_task_cfg.get("type", None) == "disp":
                # 入力画像のサイズ比はデータセットのfeaturesのshapeを参照して決定する
                # 输入图像的尺寸比通过参考数据集的features的shape来决定
                disp_shape = self.ds_info.features[task_name].shape
                disparity_os = (self.dataset_size[0] // disp_shape[0], self.dataset_size[1] // disp_shape[1])

        samples["da_params"] = DataaugParamHolder(
            da_config, self.dataset_size, self.model_input_size, self.input_names, disparity_os, for_training_dataaug
        )

        return samples

    def _preprocess_on_image(self, samples):
        # batch化前のデータにDA処理適用
        # 在batch化之前对数据应用DA处理
        da_params = samples.pop("da_params")
        for task_name in self.input_names + self.output_names:
            decoder = self.decoder_dict[task_name]
            samples[task_name] = decoder.preprocess_on_image(samples[task_name], da_params)

        return samples

    def _preprocess_on_batch(self, samples, batch_size):
        # batch化後のデータにDA処理適用、現状仕様において遅れることになるので非推奨
        # 在batch化之后对数据应用DA处理，由于目前的实现可能导致延迟，因此不推荐使用
        for task_name in self.input_names + self.output_names:
            decoder = self.decoder_dict[task_name]
            samples[task_name] = decoder.preprocess_on_batch(samples[task_name], batch_size)

        return samples

    def _split_in_out(self, samples, with_metadata=False, inputs_to_tuple=False):
        # モデルのinput/label/metadataで分割
        # 按模型的input/label/metadata进行分割
        model_inputs = OrderedDict([(task_name, samples[task_name]) for task_name in self.input_names])
        model_labels = OrderedDict([(task_name, samples[task_name]) for task_name in self.output_names])

        if self.use_condition_input:
            model_inputs[self.condition_input_cfg["name"]] = samples[self.condition_input_cfg["name"]]

        if inputs_to_tuple:
            model_inputs = tuple(model_inputs.values())

        if with_metadata:
            return model_inputs, model_labels, samples.get("metadata", None)
        else:
            return model_inputs, model_labels

    def get_data(
        self,
        split_name: str,
        batch_size: int,
        dataaug_config: Optional[Union[Dict[str, Any], DictConfig]] = None,
        for_training_dataaug: bool = False,
        shuffle: bool = False,
        shuffle_seed: Optional[int] = None,
        repeat: bool = False,
        use_cache: bool = False,
        with_split_info: bool = False,
        with_metadata: bool = False,
        inputs_to_tuple: bool = False,
    ) -> Union[tf.data.Dataset, Tuple[tf.data.Dataset, tfds.core.SplitInfo]]:
        # 指定されたsplitの読み出し/DA適用
        # 读取指定的split/应用DA
        dataaug_config = dict() if dataaug_config is None else dataaug_config

        # データロード
        # 数据加载
        dataset = self.ds_builder.load(
            split_name,
            shuffle_files=shuffle,
            read_config=tfds.ReadConfig(
                try_autocache=use_cache,
                shuffle_seed=shuffle_seed,
                shuffle_reshuffle_each_iteration=shuffle,
            )
        )

        split_info = self.info.splits[split_name]

        dataset = dataset.apply(self._set_dataset_options)
        if repeat:
            dataset = dataset.repeat()
        else:
            dataset = dataset.repeat(1)

        if shuffle:  # sample間のシャッフル
            # データシャッフルについてはここを参考: https://www.tensorflow.org/datasets/determinism
            # 参考链接关于数据集的确定性: https://www.tensorflow.org/datasets/determinism
            num_examples = split_info.num_examples
            if num_examples > self.SHUFFLE_BUFFER_TH:
                # 使用メモリ削減のため、データ数割ると制限かける
                # 为了减少内存使用，按数据量限制缓冲区大小
                buffer_size = num_examples // self.SHUFFLE_BUFFER_DIV
            else:
                buffer_size = num_examples

            dataset = dataset.shuffle(
                buffer_size=buffer_size,
                seed=shuffle_seed,
                reshuffle_each_iteration=shuffle,
            )

        # dataset map用にsamples以外の引数は全て事前に評価しておく。
        # 为dataset的map操作准备，所有非samples的参数都要事先评估好。
        get_da_param_fn = partial(
            self._get_da_param, da_config=dataaug_config, for_training_dataaug=for_training_dataaug
        )
        preprocess_on_image_fn = self._preprocess_on_image
        preprocess_on_batch_fn = partial(self._preprocess_on_batch, batch_size=batch_size)
        split_in_out_fn = partial(self._split_in_out, with_metadata=with_metadata, inputs_to_tuple=inputs_to_tuple)

        if version.parse(tf.__version__) < version.parse("2.4.0"):
            num_parallel_calls = tf.data.experimental.AUTOTUNE
        else:
            num_parallel_calls = tf.data.AUTOTUNE

        dataset = (
            dataset.map(get_da_param_fn, num_parallel_calls=num_parallel_calls)
            .prefetch(num_parallel_calls)
            .map(preprocess_on_image_fn, num_parallel_calls=num_parallel_calls)
            .batch(batch_size)
            .map(preprocess_on_batch_fn, num_parallel_calls=num_parallel_calls)
            .map(split_in_out_fn, num_parallel_calls=num_parallel_calls)
        )

        if with_split_info:
            return dataset, split_info
        else:
            return dataset
