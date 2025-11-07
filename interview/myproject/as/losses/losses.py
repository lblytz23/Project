import tensorflow.compat.v1 as tf
from tensorflow.keras import backend as K
from tensorflow.keras import losses as tf_losses
from utils.callbacks import EpochCounter

from . import yolo_loss

def name_to_class(name):
    LOSS_TBL = {
        "weighted_categorical_crossentropy": WeightedCategoricalCrossentropy,
        "weighted_binary_crossentropy": WeightedBinaryCrossentropy,
        "weighted_evidential_loss": WeightedEvidentialLoss,
        "categorical_crossentropy": tf_losses.categorical_crossentropy,
        "huber_loss": HuberLoss,
        "multibox_loss": MultiboxLoss,
        "anchorbox_loss": yolo_loss.AnchorBoxLoss,
    }
    return LOSS_TBL[name]

def weighted_categorical_crossentropy(ignore_label=255, balancing_weight=[]):
    """
    A weighted version of keras.objectives.categorical_crossentropy

    Variables:
        weights: numpy array of shape (C,), where C is the number of classes

    Usage:
        weights = np.array([0.5,2,10]) # Class one at 0.5, class 2 twice the normal weights, class 3 10x.
        loss = weighted_categorical_crossentropy(weights)
        model.compile(loss=loss, optimizer='adam')
    """
    def loss(y_true, y_logit):
        y_pred = K.softmax(y_logit)
        y_pred = K.clip(y_pred, K.epsilon(), 1 - K.epsilon())

        weights = tf.to_float(tf.not_equal(tf.to_int32(y_true), ignore_label)) * 1.0
        if balancing_weight:
            weights += tf.to_float(tf.equal(tf.to_int32(y_true), ignore_label)) * 0.0
            for idx, weight in enumerate(balancing_weight):
                weights += tf.to_float(tf.equal(tf.to_int32(y_true), idx)) * float(weight)

        num_classes = tf.shape(y_pred)[-1]
        y_true_one_hot = tf.squeeze(y_true)
        y_true_one_hot = tf.one_hot(tf.to_int32(y_true_one_hot), depth=num_classes, dtype="float32")

        # calc
        loss = y_true_one_hot * K.log(y_pred) * weights
        loss = -K.sum(loss, -1)
        return loss

    return loss


# 重み付きLossの基底クラス
class LossBase(tf.keras.losses.Loss):
    def __init__(self, ignore_label=255, balancing_weight=[], **kwargs):
        super(LossBase, self).__init__(**kwargs)
        self.ignore_label = ignore_label
        self.balancing_weight = balancing_weight

    def get_weights(self, y_true):
        weights = tf.to_float(tf.not_equal(tf.to_int32(y_true), self.ignore_label)) * 1.0
        if self.balancing_weight:
            weights += tf.to_float(tf.equal(tf.to_int32(y_true), self.ignore_label)) * 0.0
            for idx, weight in enumerate(self.balancing_weight):
                weights += tf.to_float(tf.equal(tf.to_int32(y_true), idx)) * float(weight)
        return weights

    def get_config(self):
        config = super(LossBase, self).get_config()
        config.update({
            "ignore_label": self.ignore_label,
            "balancing_weight": self.balancing_weight,
        })
        return config
    
    @staticmethod
    def get_one_hot(y_true, num_classes):
        y_true_one_hot = tf.squeeze(y_true)
        y_true_one_hot = tf.one_hot(tf.to_int32(y_true_one_hot), depth=num_classes, dtype="float32")
        return y_true_one_hot

# 重み付きCrossEntropy
class WeightedCategoricalCrossentropy(LossBase):
    def __init__(self, **kwargs):
        super(WeightedCategoricalCrossentropy, self).__init__(**kwargs)

    def call(self, y_true, y_logit):
        y_pred = K.softmax(y_logit)
        y_pred = K.clip(y_pred, K.epsilon(), 1 - K.epsilon())
        weights = self.get_weights(y_true)

        num_classes = tf.shape(y_pred)[-1]
        y_true_one_hot = LossBase.get_one_hot(y_true, num_classes)

        # calc
        loss = y_true_one_hot * K.log(y_pred) * weights
        loss = -K.sum(loss, -1)
        return loss

# 重み付きBinaryCrossEntropy
class WeightedBinaryCrossentropy(LossBase):
    def __init__(self, **kwargs):
        super(WeightedBinaryCrossentropy, self).__init__(**kwargs)

    def call(self, y_true, y_logit):
        y_pred = K.sigmoid(y_logit)
        y_pred = K.clip(y_pred, K.epsilon(), 1 - K.epsilon())
        weights = self.get_weights(y_true)

        # calc
        loss = (y_true * K.log(y_pred) + (1 - y_true) * K.log(1 - y_pred)) * weights
        loss = -K.sum(loss, -1)
        return loss


# 適切な損失を指定するだけでよく、logit側に分布のディリクレ強度を持たせるLoss。
class WeightedEvidentialLoss(LossBase):
    def __init__(self, burn_in_epoch, regularize, loss_type, **kwargs):
        super(WeightedEvidentialLoss, self).__init__(**kwargs)
        self._burn_in_epoch = burn_in_epoch
        self._regularize = regularize

        # Loss関数の選択
        if loss_type == "L2norm":
            self.loss_fun = WeightedEvidentialLoss.evidential_l2_loss
        elif loss_type == "CrossEntropy":
            self.loss_fun = WeightedEvidentialLoss.evidential_ce_loss
        else:
            print("evidential loss type is set by unexpected value, as {}.".format(loss_type))
            raise ValueError()

    def call(self, y_true, y_logit):
        epoch = EpochCounter.get_epoch()

        # バーンイン期間の進捗率、バーンイン期間は徐々に正則化を付与する
        burn_in_rate = K.min((1.0, epoch / self._burn_in_epoch))

        weights = self.get_weights(y_true)
        num_classes = tf.shape(y_logit)[-1]
        y_true_one_hot = LossBase.get_one_hot(y_true, num_classes)

        loss = self.loss_fun(self._loss_type)(y_true_one_hot, weights, y_logit, burn_in_rate, self._regularize)
        return loss

    # L2ノルムベースのEvidential-Loss
    @staticmethod
    def evidential_l2_loss(y_true_one_hot, weights, logit, regularize):
        alpha = WeightedEvidentialLoss.calc_alpha(logit)
        s = K.sum(alpha, axis=-1, keepdims=True)
        p = alpha / s
        p = K.clip(p, K.epsilon(), 1 - K.epsilon())
        loss = K.sum(y_true_one_hot * (tf.math.digamma(s) - tf.math.digamma(alpha)) * weights, axis=-1)
        loss += regularize * WeightedEvidentialLoss.kl_to_uniform(y_true_one_hot, alpha)
        return loss

    # クロスエントロピーのベースのEvidential-Loss
    @staticmethod
    def evidential_ce_loss(y_true_one_hot, weights, logit, regularize):
        alpha = WeightedEvidentialLoss.calc_alpha(logit)
        s = K.sum(alpha, axis=-1, keepdims=True)
        p = alpha / s
        p = K.clip(p, K.epsilon(), 1 - K.epsilon())
        loss = K.sum(y_true_one_hot * (tf.math.digamma(s) - tf.math.digamma(alpha)) * weights, axis=-1)
        loss += regularize * WeightedEvidentialLoss.kl_to_uniform(y_true_one_hot, alpha)
        return loss

    # LogitからDirichlet分布のpseudo concentration度数に変換する計算
    @staticmethod
    def calc_alpha(logit):
        alpha = K.exp(logit) + K.constant(1.0)
        return alpha

    # 一様分布とのKLダイバージェンス
    @staticmethod
    def kl_to_uniform(one_hot_y, alpha):
        alpha_hat = one_hot_y + (1.0 - one_hot_y) * alpha
        s_hat = K.sum(alpha_hat, axis=-1, keepdims=True)
        term1 = K.sum(tf.math.lgamma(s_hat), axis=-1)
        term2 = -K.sum(tf.math.lgamma(alpha_hat), axis=-1)
        term3 = K.sum((alpha_hat - 1.0) * (tf.math.digamma(alpha_hat) - tf.math.digamma(s_hat)), axis=-1)
        kl = tf.add(term1, tf.add(term2, term3))
        return kl
    
    # HuberLoss
class HuberLoss(tf.keras.losses.Loss):
    def __init__(self, max_num, clip_delta=1.0, **kwargs):
        super(HuberLoss, self).__init__(**kwargs)
        self.clip_delta = clip_delta
        self.max_num = max_num

    def call(self, y_true, y_pred):
        mask_cond = tf.logical_and(tf.less(0.0, y_true), tf.less(y_true, self.max_num))
        disps_mask = tf.where(mask_cond, y_pred, y_true)

        error = y_true - disps_mask
        cond = tf.keras.backend.abs(error) < self.clip_delta

        squared_loss = 0.5 * tf.keras.backend.square(error)
        linear_loss = self.clip_delta * (tf.keras.backend.abs(error) - 0.5 * self.clip_delta)

        return tf.where(cond, squared_loss, linear_loss)

    def get_config(self):
        config = super(HuberLoss, self).get_config()
        config.update({"clip_delta": self.clip_delta})
        return config
    

# MultiboxLoss
class MultiboxLoss(tf.keras.losses.Loss):
    """Multibox loss with some helper functions.

    # Arguments
        num_classes: Number of classes including background.
        alpha: Weight of L1-smooth loss.
        neg_pos_ratio: Max ratio of negative to positive boxes in loss.
        background_label_id: Id of background label.
        negatives_for_hard: Number of negative boxes to consider if there is no positive boxes in batch.
    """

    def __init__(
            self, 
            num_classes, 
            alpha=1.0, 
            neg_pos_ratio=3.0, 
            background_label_id=0, 
            negatives_for_hard=100.0, 
            fixed_height=None, 
            **kwargs
    ):
        super(MultiboxLoss, self).__init__(**kwargs)

        self.num_classes = num_classes
        self.alpha = alpha
        self.neg_pos_ratio = neg_pos_ratio
        if background_label_id != 0:
            raise Exception("Only 0 as background label is supported.")
        self.background_label_id = background_label_id
        self.negatives_for_hard = negatives_for_hard
        self.fixed_height = fixed_height

    def _l1_smooth_loss(self, y_true, y_pred):
        """Compute L1-smooth loss.

        # Arguments
            y_true: Ground truth bounding boxes, tensor of shape (?, num_boxes, 4).
            y_pred: Predicted bounding boxes, tensor of shape (?, num_boxes, 4).
        """
        abs_loss = tf.abs(y_true - y_pred)
        sq_loss = 0.5 * (y_true - y_pred) ** 2
        l1_loss = tf.where(tf.less(abs_loss, 1.0), sq_loss, abs_loss - 0.5)
        return tf.reduce_sum(l1_loss, -1)

    def _softmax_loss(self, y_true, y_pred):
        """Compute softmax loss.

        # Arguments
            y_true: Ground truth targets, tensor of shape (?, num_boxes, num_classes).
            y_pred: Predicted logits, tensor of shape (?, num_boxes, num_classes).
        """
        y_pred = tf.maximum(tf.minimum(y_pred, 1 - 1e-15), 1e-15)
        return -tf.reduce_sum(y_true * tf.log(y_pred), axis=-1)

    def call(self, y_true, y_pred):
        """Compute multibox loss.

        # Arguments
            y_true: Ground truth targets, tensor of shape (?, num_boxes, 4 + num_classes + 8).
            priors in ground truth are fictitious, y_true[:, :, -8] has 1 if prior should be penalized or on otherwise is assigned to some ground truth box.
            y_true[:, :, -7:] are all 0.
            y_pred: Predicted logits, tensor of shape (?, num_boxes, 4 + num_classes + 8).
        """
        batch_size = tf.shape(y_true)[0]
        num_boxes = tf.to_float(tf.shape(y_true)[1])

        # loss for all priors
        conf_loss = self._softmax_loss(y_true[:, :, 4:-8], y_pred[:, :, 4:-8])
        if self.fixed_height is None:
            loc_loss = self._l1_smooth_loss(y_true[:, :, :4], y_pred[:, :, :4])
        else:
            # heightのLossは無視
            loc_loss = self._l1_smooth_loss(y_true[:, :, :3], y_pred[:, :, :3])

        # get positives loss
        num_pos = tf.reduce_sum(y_true[:, :, -8] * (1 - y_true[:, :, -7]) * (1 - y_true[:, :, -6]), axis=-1)
        pos_loc_loss = tf.reduce_sum(loc_loss * y_true[:, :, -8] * (1 - y_true[:, :, -7]) * (1 - y_true[:, :, -6]), axis=-1)
        pos_conf_loss = tf.reduce_sum(conf_loss * y_true[:, :, -8] * (1 - y_true[:, :, -7]) * (1 - y_true[:, :, -6]), axis=-1)

        # get negatives loss, we penalize only confidence here
        num_neg = tf.minimum(self.neg_pos_ratio * num_pos, num_boxes - num_pos)
        pos_num_neg_mask = tf.greater(num_neg, 0)
        has_min = tf.to_float(tf.reduce_any(pos_num_neg_mask))
        num_neg = tf.concat(axis=0, values=[num_neg, (1 - has_min) * self.negatives_for_hard])
        num_neg_batch = tf.reduce_min(tf.boolean_mask(num_neg, tf.greater(num_neg, 0)))
        num_neg_batch = tf.to_int32(num_neg_batch)
        confs_start = 4 + self.background_label_id + 1
        confs_end = confs_start + self.num_classes - 1
        max_confs = tf.reduce_max(y_pred[:, :, confs_start:confs_end], axis=2)
        _, indices = tf.nn.top_k(max_confs * (1 - y_true[:, :, -8]), k=num_neg_batch)
        batch_idx = tf.expand_dims(tf.range(0, batch_size), 1)
        batch_idx = tf.tile(batch_idx, (1, num_neg_batch))
        full_indices = tf.reshape(batch_idx, [-1]) * tf.to_int32(num_boxes) + tf.reshape(indices, [-1])
        neg_conf_loss = tf.gather(tf.reshape(conf_loss, [-1]), full_indices)
        neg_conf_loss = tf.reshape(neg_conf_loss, [batch_size, num_neg_batch]) 
        neg_conf_loss = tf.reduce_sum(neg_conf_loss, axis=1)

        # loss is sum of positives and negatives
        total_loss = pos_conf_loss + neg_conf_loss
        total_loss /= num_pos + tf.to_float(num_neg_batch)
        num_pos = tf.where(tf.not_equal(num_pos, 0), num_pos, tf.ones_like(num_pos))
        total_loss += (self.alpha * pos_loc_loss) / num_pos
        return total_loss

    def get_config(self):
        config = super(MultiboxLoss, self).get_config()
        config.update({
            "num_classes": self.num_classes,
            "alpha": self.alpha,
            "neg_pos_ratio": self.neg_pos_ratio,
            "background_label_id": self.background_label_id,
            "negatives_for_hard": self.negatives_for_hard,
            "fixed_height": self.fixed_height,
        })
        return config