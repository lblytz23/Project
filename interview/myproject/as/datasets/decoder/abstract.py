from abc import ABCMeta, abstractmethod
from typing import Dict, Union

import tensorflow as tf

from ..utils.preproc_params import (
    BrightnessPrm,
    CropParamHolder,
    CutoutPrm,
    FlipPrm,
    NoisePrm,
    PaddingParamHolder,
    RotateParamHolder,
    ScaleParamHolder,
    SharpnessPrm,
)

from .dataaug_params import DataaugParamHolder

class AbstractDecoder(metaclass=ABCMeta):
    def __init__(self, task_name, ds_preproc_args, model_config, **kwargs):
        self.task_name = task_name
        self.ds_preproc_args = ds_preproc_args
        self.model_config = model_config
        self.kwargs = kwargs

    def update_sample_values(self, src_dict, update_values):
        # tfの何か機能でlabel(dict value)を直接更新ができないので、新しいdictを生成して返す
        # https://stackoverflow.com/questions/67167182/modifying-python-objects-while-constructing-tensorflow-graph
        return dict(src_dict, **update_values)

    # DataAugmentationの前にしたい処理
    @abstractmethod
    def _pre_data_augmentation(
        self,
        sample,
    ):
        pass

    # 明るさ
    def _brightness(
        self,
        sample,
        brightness_param: Dict[str, BrightnessPrm],
    ):
        return sample

    # sharpness/ほかし
    def _sharpness_or_blur(
        self,
        sample,
        sharpness_param: Dict[str, SharpnessPrm],
    ):
        return sample

    # noise
    def _noise(
        self,
        sample,
        noise_param: Dict[str, NoisePrm],
    ):
        return sample

    # cutout
    def _cutout(
        self,
        sample,
        cutout_param: Dict[str, CutoutPrm],
    ):
        return sample

    # スケーリング
    @abstractmethod
    def _scale(
        self,
        sample,
        scale_param: ScaleParamHolder,
    ):
        pass

    # 回転
    @abstractmethod
    def _rotate(
        self,
        sample,
        rotate_param: RotateParamHolder,
    ):
        pass

    # crop
    @abstractmethod
    def _crop(
        self,
        sample,
        crop_param: CropParamHolder,
    ):
        pass

    # mean pixel埋め
    @abstractmethod
    def _mean_padding(
        self,
        sample,
        padding_param: PaddingParamHolder,
    ):
        pass

    # 水平flip
    @abstractmethod
    def _horizontal_flip(
        self,
        sample,
        flip_param: FlipPrm,
    ):
        pass

    # DataAugmentationの後にしたい処理
    @abstractmethod
    def _post_data_augmentation(
        self,
        sample,
        post_shape: tf.Tensor,
    ):
        pass

    # 画像前処理
    # preproc内のsampleはyolo/ssdはDict[str, tf.Tensor]、その他はtf.Tensor
    # 抽象/継承class型でアノテーションするのはdtypy的にめんどくさい…簡便の為暫くはこれで
    @tf.function
    def preprocess_on_image(
        self,
        sample: Union[tf.Tensor, Dict[str, tf.Tensor]],
        da_params: DataaugParamHolder,
    ) -> Union[tf.Tensor, Dict[str, tf.Tensor]]:
        sample = self._pre_data_augmentation(sample)
        sample = self._brightness(sample, da_params.brightness)
        sample = self._sharpness_or_blur(sample, da_params.sharpness)
        sample = self._noise(sample, da_params.noise)
        # da後に実施する場合、暫定で先に抜けてその後にimage daの最後に移動。ベストはrandom_crop->resizeの順。
        sample = self._scale(sample, da_params.scale)
        sample = self._cutout(sample, da_params.cutout)
        sample = self._rotate(sample, da_params.rotate)
        sample = self._crop(sample, da_params.crop)
        sample = self._mean_padding(sample, da_params.padding)
        sample = self._horizontal_flip(sample, da_params.flip)

        return sample
