from typing import Dict

import numpy as np
import tensorflow as tf

from ..utils.preproc_params import (
    CornerClassIdDef,
    CropParamHolder,
    FlipPrm,
    PaddingParamHolder,
    RotateParamHolder,
    ScaleParamHolder,
)
from .abstract import AbstractDecoder

# YOLOラベルDA用
class YOLODecoder(AbstractDecoder):
    def __init__(self, for_training_label=False, **kwargs):
        super().__init__(**kwargs)

        self.for_training_label = for_training_label
        self.anchors = self.reshape_anchors(self.model_config["anchors"])
        self.num_classes = self.model_config["num_classes"]
        self.class_3d = self.model_config["class_3d"]
        self.max_boxes = self.model_config["max_boxes"]
        self.scales = self.model_config["scales"]
        self.multi_anchor_assign = self.model_config.get("multi_anchor_assign", False)
        self.multi_anchor_assign_th = self.model_config.get("multi_anchor_assign_th", 0.4)
        self.corner_eps = self.model_config.get("corner_eps", 0.0)
        # x/y/w/h/corner_cos_alpha/corner_sin_alpha/conf
        self.out_elem_num = self.model_config["out_elem_num"]
        if not self.for_training_label and (self.out_elem_num == 7):
            print(
                "out_elem_num of '{}' will be set to 6 if out_elem_num == 7 at eval mode".format(
                    self.__class__.__name__
                )
            )
            self.out_elem_num = 6
        else:
            self.out_elem_num = 5  # x/y/w/h/conf
        self.corner_class_id_def = CornerClassIdDef(**self.ds_preproc_args["class_ids"]) if self.class_3d else None
        self.min_train_bbox_area = self.ds_preproc_args.get("min_train_bbox_area", 0.0)
        self.min_train_bbox_height = self.ds_preproc_args.get("min_train_bbox_height", 0.0)
        self.enable_ignore_flag = self.ds_preproc_args.get("enable_ignore_flag", False)

    def reshape_anchors(self, anchors):
        """
        # Arguments
            anchors(list): [w0,h0, w1,h1, ..., wn,hn].
        # Returns
            anchors(np.array): [[w0,h0], [w1,h1], ..., [wn,hn]].
        """
        anchors = [float(x) for x in anchors]

        return np.array(anchors, np.float32).reshape(-1, 2)

    def _pre_data_augmentation(
        self,
        sample: Dict[str, tf.Tensor],
    ) -> Dict[str, tf.Tensor]:
        # bbox/corner_x=0.0への相対座標、class_id=0が含まれている想定(corner_xはclass_3d=True時のみ処理)
        # tfdsのbboxは(ymin,xmin,ymax,xmax)の並びなので、(xmin,ymin,xmax,ymax)に順番入れ替えておく
        update_values = {
            "bbox": tf.gather(sample["bbox"], [1, 0, 3, 2], axis=-1),
        }
        return self.update_sample_values(sample, update_values)

    def _scale(
        self,
        sample: Dict[str, tf.Tensor],
        scale_param: ScaleParamHolder,
    ) -> Dict[str, tf.Tensor]:
        # 相対座標で処理するため何もしない
        return sample

    def _rotate(
        self,
        sample: Dict[str, tf.Tensor],
        rotate_param: RotateParamHolder,
    ) -> Dict[str, tf.Tensor]:
        # bboxを回転させる
        def _rotate(bbox, rotate_prm, corner_x=None):
            # pre_size_w = rotate_prm.pre_shape[1]
            # pre_size_h = rotate_prm.pre_shape[0]
            # pre_size_tile = tf.cast(tf.tile([pre_size_w, pre_size_h], [2]), bbox.dtype)
            # post_size_w = rotate_prm.post_shape[1]
            # post_size_h = rotate_prm.post_shape[0]
            # post_size_tile = tf.cast(tf.tile([post_size_w, post_size_h], [2]), bbox.dtype)

            # _bbox = bbox * pre_size_tile  # 相対座標 -> 絶対座標
            # _points = tf.stack([  # 回転前bboxの原点座標計算
            #     tf.stack([_bbox[..., 0], _bbox[..., 1]], axis=0),  # [x_min, y_min]
            #     tf.stack([_bbox[..., 2], _bbox[..., 1]], axis=0),  # [x_max, y_min]
            #     tf.stack([_bbox[..., 2], _bbox[..., 3]], axis=0),  # [x_max, y_max]
            #     tf.stack([_bbox[..., 0], _bbox[..., 3]], axis=0)  # [x_min, y_max]
            # ], axis=0)
            # _transform_matrix = tf.tile(rotate_prm.affine_matrix[tf.newaxis], [4, 1, 1])  # 4x3x3
            # _points = tf.matmul(_transform_matrix, points)  # 回転後の原点/終点座標計算
            # _min_points = tf.reduce_min(_points, axis=0)  # 回転後座標から最大/最小値を更新 3(x,y,1) xbbox数
            # _max_points = tf.reduce_max(_points, axis=0)  # 回転後座標から最大/最小値を更新 3(x,y,1) xbbox数
            # rotate_bbox = tf.stack([min_points[0], min_points[1], max_points[0], max_points[1]], axis=-1)  # 絶対座標
            # rotate_bbox /= post_size_tile  # 絶対座標 -> 相対座標
            # rotate_bbox = tf.clip_by_value(rotate_bbox, 0.0, 1.0)
            # rotate_bbox.set_shape(bbox.get_shape())
            # if corner_x is not None:
            #     _corner_x = corner_x * tf.cast(pre_size_w, corner_x.dtype)  # 相対座標 -> 絶対座標
            #     _points = tf.stack([  # 回転前bboxの原点座標計算
            #         tf.stack([_corner_x, _bbox[..., 1]], axis=0),  # [corner_x, y_min]
            #         tf.stack([_corner_x, _bbox[..., 3]], axis=0),  # [corner_x, y_max]
            #     ], axis=0)
            #     _corner_x = tf.matmul(_transform_matrix, points)  # 回転後の原点座標計算
            #     _corner_x = tf.reduce_mean(_corner_x[..., 0], axis=-1)  # 変換後座標の中心を新しいcorner_xにする
            #     rotate_corner_x = (min_points[0] + max_points[0]) / 2  # 絶対座標→相対座標
            #     rotate_corner_x.set_shape(corner_x.get_shape())
            # else:
            #     rotate_corner_x = None
            # return rotate_bbox, rotate_corner_x
            print("WARNING: rotate data augmentation(yolo) is not implemented.")
            return bbox, corner_x

        bbox = sample["bbox"]
        corner_x = sample["corner_x"] if self.class_3d else None
        radian = rotate_param.params.radian

        rotate_cond = tf.logical_and(tf.not_equal(radian, 0.0), tf.not_equal(len(bbox), 0))
        rotated_bbox, rotated_corner_x = tf.case(
            [(rotate_cond, lambda: _rotate(bbox, rotate_param.params, corner_x))], default=lambda: (bbox, corner_x)
        )

        if self.class_3d:
            update_values = {
                "bbox": rotated_bbox,
                "corner_x": rotated_corner_x,
            }
        else:
            update_values = {"bbox": rotated_bbox}
        return self.update_sample_values(sample, update_values)

    def _crop(
        self,
        sample: Dict[str, tf.Tensor],
        crop_param: CropParamHolder,
    ) -> Dict[str, tf.Tensor]:
        # bbox_utilsに移行予定
        def _crop(bbox, prm, corner_x=None, corner_class_id=None, corner_class_id_def=None):
            offset_x = tf.cast(prm.cut_offset_x, bbox.dtype)
            offset_y = tf.cast(prm.cut_offset_y, bbox.dtype)
            pre_size_w = tf.cast(prm.pre_shape[1], bbox.dtype)
            pre_size_h = tf.cast(prm.pre_shape[0], bbox.dtype)
            post_size_w = tf.cast(prm.post_shape[1], bbox.dtype)
            post_size_h = tf.cast(prm.post_shape[0], bbox.dtype)
            
            offset_tile = tf.tile([offset_x, offset_y], [2])
            pre_size_tile = tf.tile([pre_size_w, pre_size_h], [2])
            post_size_tile = tf.tile([post_size_w, post_size_h], [2])

            # prm系は絶対座標で来るので変換後は相対座標で処理
            bbox = ((bbox * pre_size_tile - offset
