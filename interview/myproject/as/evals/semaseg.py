import os
from importlib import import_module

import numpy as np
import tensorflow.compat.v1 as tf
from tensorflow.keras.callbacks import ProgbarLogger

from datasets.decode import DatasetDecoder
from datasets.decoder.dataaug_params import DataaugParamHolder
from datasets.utils import image_utils
from evals import utils as Utils
from evaluator import AsuraEvaluator as evaluator
from postprocess import semaseg

"""  
スコア計算
"""  
# 日语: スコア計算
# 中文: 评分计算

def _calculate_score(pred, label, ignore_label, num_classes):
    conf = Utils.calculate_conf_matrix(pred, label, ignore_label, num_classes)
    class_score = Utils.get_class_score(conf, num_classes)
    return class_score, conf

"""
ローカルpngへ画像出力
"""
# 日语: ローカルpngへ画像出力
# 中文: 输出图像到本地png

def _save_vis_to_img(out_dir, inputs, preds, cfg, Labels, filenames):
    out_img_dir = os.path.join(out_dir, "image")
    if not os.path.isdir(out_img_dir):
        os.makedirs(out_img_dir)

    for idx, (input, pred) in enumerate(zip(inputs, preds)):
        filename = filenames[idx]
        Utils.save_annotation(
            input,
            pred,
            Labels,
            out_img_dir,
            filename + "_pred",
            add_colormap=True,
            overlay_ratio=cfg["overlay_ratio"],
            input_scale_values=True,
            input_normalize_mode=cfg["model_mode"],
        )
        Utils.flush_progress_bar("save image", (idx + 1) / len(inputs))
    print("")

"""
eval
"""
# 日语: eval
# 中文: 评估

def eval(cfg):
    Labels = import_module("labels." + cfg["dataset_map"][cfg["task"]]["preproc_func"]["args"]["label"])

    if not tf.gfile.Exists(cfg["dataset_path"]):
        raise FileNotFoundError(cfg["dataset_path"])

    out_dir = os.path.join(cfg["out_dir"], cfg["task"])

    # product用 concatされるタスクの場合モデル出力の一部分を使うか決める
    # 日语: product用 concatされるタスクの場合モデル出力の一部分を使うか決める
    # 中文: 对于被concat的任务，决定是否使用模型输出的一部分
    concatenated = False
    model_output = cfg["task"]

    if cfg["model_mode"] == "product" and "output_concatenate" in cfg["model"].keys():
        for concat_name, concat_cfg in cfg["model"]["output_concatenate"].items():
            if concat_cfg["type"] == "semaseg_concat" and cfg["task"] in concat_cfg["tasks"]:
                concatenated = True
                task_idx = concat_cfg["tasks"].index(cfg["task"])

    # 条件输入を使うかどうか
    # 日语: 条件入力を使うかどうか
    # 中文: 是否使用条件输入
    use_condition_input = ("condition_input" in cfg["model"].keys()) and cfg.get("use_condition_input", False)

    # 評価用クラスをインスタンス化
    # 日语: 評価用クラスをインスタンス化
    # 中文: 实例化评估类
    sema_evaluator = evaluator(
        cfg,
        weight_path=cfg["init_weight_path"],
        output_list=[model_output],
        quantized=cfg["quantized"],
        use_condition_input=use_condition_input,
    )

    # データ取得 (labelを取得するため)
    # 日语: データ取得 (labelを取得するため)
    # 中文: 获取数据（用于获取标签）
    eval_preproc_params = cfg.get("eval_preproc_params", {})
    da_config = {
        "crop": {"position": eval_preproc_params.get("crop", None)},
        "padding": {"position": eval_preproc_params.get("padding", None)},
    }

    inputs_to_tuple = cfg["model_mode"] != "predict"
    decoder = DatasetDecoder(
        cfg,
        cfg["task"],
        cfg["dataset_path"],
        normalize_mode=cfg["model_mode"],
        use_condition_input=use_condition_input,
    )

    if cfg["batch_size"] != 1:
        cfg["batch_size"] = 1  # 未対応のためdetection以外のタスクはbatch sizeを1にする
        # 日语: 未対応のためdetection以外のタスクはbatch sizeを1にする
        # 中文: 由于不支持，将检测以外的任务的批次大小设为1

    dataset = decoder.get_data(
        cfg["task"],
        cfg["dataset_path"],
        cfg["batch_size"],
        dataaug_config=da_config,
        init_metadata=True,
        inputs_to_tuple=inputs_to_tuple,
        shuffle=cfg["shuffle"],
        shuffle_seed=cfg["shuffle_seed"],
    )

    ds_info = decoder.info

    data_num = ds_info.splits[cfg["tfs_load_split_eval"]].num_examples
    if cfg["num_samples"] is not None:
        data_num = min(data_num, cfg["num_samples"])
        dataset = dataset.unbatch().batch(cfg["batch_size"], drop_remainder=True)
    dataset, inputs, labels, filenames = Utils.get_datasets(cfg["task"], dataset)

    progbar = ProgbarLogger(count_mode="steps")

    preds = sema_evaluator.predict(dataset, steps=len(labels) / cfg["batch_size"], verbose=1, callbacks=[progbar])

    if concatenated:
        preds = preds[:, :, :, :, task_idx]

    labels = np.array(labels)
    inputs = np.array(inputs)

    # 特にcrop位置の指定忘れがぱば入力量のpaddingした部分をcrop
    # 日语: 特にcrop位置の指定忘れがぱば入力量のpaddingした部分をcrop
    # 中文: 尤其是忘记指定crop位置时裁剪输入填充部分
    input_name = cfg["model"]["input"]["name"][0]
    input_img_size = ds_info.features[input_name].shape[0:2]
    padding_img_size = (sema_evaluator.padded_input_img_w, sema_evaluator.padded_input_img_h)
    da_padding_param = DataaugParamHolder(da_config, input_img_size, padding_img_size).padding.params

    pred_crop_box = cfg.get("pred_crop_box", None)
    if pred_crop_box is None:
        pred_crop_box = (
            da_padding_param.top,
            da_padding_param.left,
            da_padding_param.pre_shape[0],
            da_padding_param.pre_shape[1],
        )

    label_crop_box = cfg.get("label_crop_box", None)
    if label_crop_box is None:
        label_crop_box = (
            da_padding_param.top,
            da_padding_param.left,
            da_padding_param.pre_shape[0],
            da_padding_param.pre_shape[1],
        )

    # 後処理 (クロップ)
    # 日语: 後処理 (クロップ)
    # 中文: 后处理（裁剪）
    post_preds = semaseg.Post(pred_crop_box=pred_crop_box, scale=cfg["pred_scaling"], pred_th=cfg["pred_th"])
    post_inputs = semaseg.Post(label_crop_box=label_crop_box, scale=cfg["pred_scaling"])
    post_labels = semaseg.Post(label_crop_box=label_crop_box, scale=cfg["pred_scaling"])

    preds = post_preds.process(preds)
    inputs = post_inputs.process(inputs)
    labels = post_labels.process(labels)

    if preds.shape != labels.shape:
        raise ValueError

    if cfg["save_pred_img"]:
        # tensorboardログ保存
        if cfg["vis_vflip_images"]:
            _inputs = image_utils.vertical_flip_image(inputs)
            _preds = np.squeeze(image_utils.vertical_flip_image(preds[..., np.newaxis]), axis=-1)
        else:
            _inputs = inputs
            _preds = preds

        if cfg["save_tb"]:
            _inputs = np.array([image_utils.scale_image(_input, scale_value=0.5, resize_method="nearest") for _input in _inputs])
            _preds = np.squeeze([image_utils.scale_image(_pred[..., np.newaxis], scale_value=0.5, resize_method="nearest") for _pred in _preds], axis=-1)

            Utils.save_annotations_to_tb(
                _inputs,
                _preds,
                Labels,
                "pred_image/",
                filenames,
                out_dir,
                overlay_ratio=cfg["overlay_ratio"],
                input_scale_values=True,
                input_normalize_mode=cfg["model_mode"],
            )
        # png保存
        else:
            _save_vis_to_img(out_dir, _inputs, _preds, cfg, Labels, filenames)

    if cfg["save_label_img"]:
        # tensorboardログ保存
        if cfg["vis_vflip_images"]:
            _inputs = image_utils.vertical_flip_image(inputs)
            _labels = np.squeeze(image_utils.vertical_flip_image(labels[..., np.newaxis]), axis=-1)
        else:
            _inputs = inputs
            _labels = labels

        if cfg["save_tb"]:
            Utils.save_annotations_to_tb(
                _inputs,
                np.where(_labels == 255, 0, _labels),
                Labels,
                "label_image/",
                filenames,
                out_dir,
                overlay_ratio=cfg["overlay_ratio"],
                input_scale_values=True,
                input_normalize_mode=cfg["model_mode"],
            )
        # png保存
        else:
            _save_vis_to_img(out_dir, _inputs, labels, cfg, Labels, filenames)

    ignore_label = cfg["dataset_map"][cfg["task"]]["preproc_func"]["args"]["ignore_label"]
    num_classes = cfg["dataset_map"][cfg["task"]]["preproc_func"]["args"]["num_classes"]
    class_score, conf_matrix = _calculate_score(preds, labels, ignore_label, num_classes)

    Utils.print_iou(class_score[0])

    if cfg["save_tb"]:
        Utils.save_score_data_to_tb(out_dir, "metrics", Utils.get_classname_list(Labels), class_score)
    else:
        Utils.save_score_data(os.path.join(out_dir, "score.csv"), Utils.get_classname_list(Labels), class_score)

