from collections import namedtuple
from importlib import import_module

import numpy as np
import tensorflow as tf
from PIL import Image, ImageDraw

from ..utils import image_utils
from ..abstract import PreprocJson

class PreprocLabelImage(PreprocJson):
    """前処理パイプライン(セマセグ用)

    Examples:
    # データセット用config内に以下の様に記載して使用
    dataset_map: 
        (task name): 
            meta_data: *TARGET_FILE_JSON
            preproc_func:  # 前処理時の設定
                type: json2labelImg
                args: 
                    label: labels_road   # クラスID辞書
                    ignore_label: 255   # 無視ラベルのID（例えば、labels以外の部分）
                    num_classes: 2   # クラス数
                    skip_ghost: True   # ゴースト画像の場合、invisibleをネガティブとして描画（省略の場合False）
                    repl_invisible: True   # 無視ラベルの描画をスキップ（省略の場合False）
                    skip_road_marking: True   # 前処理の際に道路標示ラベルの描画をスキップ（省略の場合False）
            feature_config:  # データセットのinfo用設定
                type: image
                args: 
                    shape: [312, 980, 1]  # 前処理後のshape
    """
    
    # 前処理（Annotation->ラベル画像）
    def _preproc(self, pcoll):
        bname, element = pcoll
        label_data = element["label_data"]

        annotation = label_data.label
        preproc_args = self._get_preproc_args(label_data.task_name)
        label_def = import_module("labels." + preproc_args["label"])
        skip_ghost = preproc_args.get("skip_ghost", False)
        repl_invisible = preproc_args.get("repl_invisible", False)
        skip_road_marking = preproc_args.get("skip_road_marking", False)

        label_img = annot2labelImg(
            annotation,
            label_def.name2label,
            "trainIds",
            skip_ghost=skip_ghost,
            repl_invisible=repl_invisible,
            skip_road_marking=skip_road_marking,
        )

        label_img = np.array(label_img, dtype=np.uint8)
        if label_img.ndim == 2:
            label_img = np.expand_dims(label_img, axis=-1)  # [height, width] -> [height, width, 1]

        label_data.label = label_img
        element["label_data"] = label_data

        return (bname, element)
    
    # 垂直方向反転
    def _vertical_flip(self, pcoll):
        bname, element = pcoll
        label_data = element["label_data"]
        dataaug_params = element["dataaug_params"]

        label = label_data.label
        if dataaug_params.vertical_flip.should_flip:
            label = image_utils.vertical_flip_image(label)

        label_data.label = label
        element["label_data"] = label_data

        return (bname, element)
    
    # スケール
    def _scale(self, pcoll):
        bname, element = pcoll
        label_data = element["label_data"]
        dataaug_params = element["dataaug_params"]

        label = label_data.label
        scale_value = dataaug_params.scale.params.value
        if scale_value != 1.0:
            label = image_utils.scale_image(label, scale_value=scale_value, resize_method="nearest")
            label = tf.cast(label, dtype=tf.uint8)

        label_data.label = label
        element["label_data"] = label_data

        return (bname, element)

    # クロップ
    def _crop(self, pcoll):
        bname, element = pcoll
        label_data = element["label_data"]
        dataaug_params = element["dataaug_params"]

        label = label_data.label
        label = image_utils.crop_image(label, dataaug_params.crop.params)

        label_data.label = label
        element["label_data"] = label_data

        return (bname, element)

    # 間引き
    def _shrink(self, pcoll):
        bname, element = pcoll
        label_data = element["label_data"]
        dataaug_params = element["dataaug_params"]
        shrink_params = dataaug_params.shrink.params

        label = label_data.label
        if shrink_params.exec_mode is not None:
            label = image_utils.shrink_image(label, shrink_params)

        label_data.label = label
        element["label_data"] = label_data

        return (bname, element)
    
    # pooling
    def _pooling(self, pcoll):
        bname, element = pcoll
        label_data = element["label_data"]
        dataaug_params = element["dataaug_params"]
        pooling_params = dataaug_params.pooling.params

        label = label_data.label
        if pooling_params.exec_mode is not None:
            # ラベルについてはnearestでpooling後の画像サイズと合う形にする
            # kernel_size/strideからpooling後shape判断+resize
            new_height = int(((label.shape[0] - pooling_params.kernel_size[0]) / pooling_params.strides[0]) + 1)
            new_width = int(((label.shape[1] - pooling_params.kernel_size[1]) / pooling_params.strides[1]) + 1)
            label = image_utils.scale_image(label, new_size=(new_height, new_width), resize_method="nearest")

        label_data.label = label
        element["label_data"] = label_data

        return (bname, element)

    # 後処理
    def _postproc(self, pcoll):
        bname, element = pcoll
        label_data = element["label_data"]
        dataaug_params = element["dataaug_params"]
        postproc_params = dataaug_params.postproc.params

        label = label_data.label
        if label.assess is True:
            pass

        label_data.label = label
        element["label_data"] = label_data

        return (bname, element)

# Convert the given annotation to a label image
def annot2labelImg(
    annotation,
    name2label,
    encoding,
    outline=None,
    scale=1,
    crop_box=(),
    skip_ghost=False,
    repl_invisible=False,
    skip_road_marking=False,
):
    # the size of the image
    width = round((annotation.imgWidth / scale))
    height = round((annotation.imgHeight / scale))
    size = (width, height)

    # the background
    if encoding == "ids":
        background = name2label["unlabeled"].id
    elif encoding == "trainIds":
        background = name2label["unlabeled"].trainId
    elif encoding == "color":
        background = name2label["unlabeled"].color
    else:
        print("Unknown encoding '{}'".format(encoding))
        return None

    # this is the image that we want to create
    if encoding == "color":
        labelImg = Image.new("RGBA", size, background)
    else:
        labelImg = Image.new("L", size, background)

    # a drawer to draw into the image
    drawer = ImageDraw.Draw(labelImg)

    # loop over all objects
    for obj in annotation.objects:
        label = obj.label
        polygon = obj.polygon

        # If the object is deleted, skip it
        if obj.deleted:
            continue

        # If the label is not known, but ends with a 'group' (e.g. cargroup)
        # try to remove the s and see if that works
        if (label not in name2label) and label.endswith("group"):
            label = label[: -len("group")]

        if obj.drivindDivision == "Unable to drive.":
            if label == "sidewalk":
                label = "sidewalk unable to drive"
            elif label == "terrain":
                label = "terrain unable to drive"

        # # 高濃度moku以外はじく
        # if label == "smoke" and obj.Steam != "HighDensity":
        #     continue
        # ghost系ラベルは描画しない
        ghost_labels = [
            "smoke",
            "wiper streak",
            "splash",
            "aeb",
            "invisible",
        ]
        if skip_ghost:
            if label in ghost_labels:
                continue

        # 単独アノテのinvisibleはネガティブクラス扱い
        if repl_invisible:
            if annotation.AnnotationPattern.get("SingleAnotation", "none") != "none" and label == "invisible":
                label = "not ghost"

        # 白線&路面標示系ラベルは描画しない
        lane_label = [
            "line solid white - ego lane",
            "line solid yellow - ego lane",
            "line solid other - ego lane",
            "line dashed white - ego lane",
            "line dashed yellow - ego lane",
            "line dashed other - ego lane",
            "line solid white - other lane",
            "line solid yellow - other lane",
            "line solid other - other lane",
            "line dashed white - other lane",
            "line dashed yellow - other lane",
            "line dashed other - other lane",
            "line solid white - unknown",
            "line solid yellow - unknown",
            "line solid other - unknown",
            "line dashed white - unknown",
            "line dashed yellow - unknown",
            "line dashed other - unknown",
        ]

        road_marking_label = [
            "road marking crosswalk",
            "road marking stopline",
            "road marking arrow",
            "road marking diamond",
            "road marking text stop",
            "road marking text other",
            "road marking other",
        ]
        if skip_road_marking:
            if label in lane_label or label in road_marking_label:
                continue

        if label not in name2label:
            raise ValueError("Label '{}' not known.".format(label))

        # If the ID is negative that polygon should not be drawn
        if name2label[label].id < 0:
            continue

        if encoding == "ids":
            val = name2label[label].id
        elif encoding == "trainIds":
            val = name2label[label].trainId
        elif encoding == "color":
            val = name2label[label].color

        try:
            Point = namedtuple("Point", ["x", "y"])
            polygon_scale = [Point(round(pol[0] / scale), round(pol[1] / scale)) for pol in polygon]

            # If polygon_scale does not contain at least 2 coordinates that polygon should not be drawn
            if len(set(polygon_scale)) < 2:
                continue

            if outline:
                drawer.polygon(polygon_scale, fill=val, outline=outline)
            else:
                drawer.polygon(polygon_scale, fill=val)
        except Exception as e:
            print(f"Failed to draw polygon with label {label}, \n exception: {e}")

    if crop_box:
        scaled_crop_box = tuple(int(crop / scale) for crop in crop_box)
        labelImg = labelImg.crop(scaled_crop_box)

    # moku上面角
    pad = 624 - labelImg.height
    if pad > 0:
        new_labelImg = Image.new(labelImg.mode, (labelImg.width, 624), background)
        new_labelImg.paste(labelImg, (0, pad))
        labelImg = new_labelImg

    return labelImg
