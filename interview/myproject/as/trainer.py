import inspect
import os
import time
from typing import List

import psutil

# tf2.4のデフォルトではこのlimitが64GBで、a100x4などの学習方法だと足りないので変更
# (默认情况下，tf2.4的此限制为64GB，学习方法如a100x4时会不足，因此进行更改)
os.environ["TF_GPU_HOST_MEM_LIMIT_IN_MB"] = str(psutil.virtual_memory().total // 1024**2)

import tensorflow as tf
from omegaconf import DictConfig
from tensorflow.keras import optimizers
from tensorflow.keras.callbacks import LearningRateScheduler, TensorBoard
from tensorflow.keras.callbacks.experimental import BackupAndRestore
from tensorflow.keras.mixed_precision import experimental as mixed_precision
from tensorflow.keras.models import Model

from datasets.decode import DatasetDecoder
from metrics import metrics
from models.asura import AsuraNet
from scheduler.lr_scheduler import CosineDecay, PolynomialDecay, StepDecay, WarmupDecay

# utils.callbacksの中でModelcheckpointGCSの存在はlossesや他の関数よりも先にGPUメモリが確保される。た だのclassで原因不明
# (在utils.callbacks中，ModelcheckpointGCS的存在确保在losses和其他函数之前先保留GPU内存。仅在class时原因不明)
from utils.callbacks import ModelcheckpointGCS
from utils import gpu_setting, model_op

gpu_setting.set_memory_growth()

from losses import losses
from utils.callbacks import ConvSymmetrizer, EpochCounter, ModelcheckpointGCS

# import tensorflow.profiler.experimental as profiler

@tf.function
def train(cfg):
    """train関数
    (训练函数)
    """
    # configチェック
    # (检查配置)
    _check_config(cfg)

    # 返り値にtrainする場合とtrainしない場合の名前が無指定の名前がコンフリクトしていく
    # (返回值有train和不train的情况时，无指定的名称会冲突)
    tf.keras.backend.clear_session()

    # マルチGPU対応
    # (支持多GPU)
    gpu_list = ["/device:GPU:{}".format(i) for i in range(cfg["gpu_count"])] if cfg["gpu_count"] > 0 else None
    strategy = tf.distribute.MirroredStrategy(gpu_list)
    with strategy.scope():
        # mixed precision
        if cfg["mixed_precision"] is not None:
            policy = mixed_precision.Policy(cfg["mixed_precision"])
            mixed_precision.set_policy(policy)

        # モデル設定
        # (设置模型)
        print("model compile...")
        model = AsuraNet(
            config=cfg["model"],
            mode="training",
            backbone_weight=cfg["backbone_weight"],
            sharpness_da_params=cfg["da"]["sharpness"],
        )

        # 学習対象モデルのinput/outputを設定
        # WARNING: 条件分けが仕様上仕様OFFが、該当した場合この行ごと削除されることにする
        # (警告：基于条件分割，本行将被删除，如果指定为“关闭”，否则应用本行)
        model_inputs = cfg["model"]["input"]["name"]
        model_outputs = list(cfg["task_weight"].keys())
        model = _reconstruction_model_io(model, model_inputs, model_outputs)

        # load weight
        # (加载权重)
        _load_weight(model, cfg["init_weight_path"])

        # freeze weight
        # (冻结权重)
        _freeze_weight(model, cfg)

        # loss/metricsのvariableがstrategy.scope()の外で作られるのを防ぐためここでインスタンス生成
        # (为了防止在strategy.scope()外部生成loss/metrics的变量，此处生成实例)
        losses_list, loss_weights_list, metrics_list = _get_compile_lists(cfg)

        # optimizer設定
        # (设置优化器)
        optimizer = _get_optimizer(cfg["lr"])

        # コンパイル
        # (编译)
        model.compile(loss=losses_list, loss_weights=loss_weights_list, optimizer=optimizer, metrics=metrics_list)

        # データ用意
        # (准备数据)
        print("data generating...")
        (train_dataset, train_data_num), (val_dataset, val_data_num) = _get_dataset(cfg, list(model.output.keys()))

        # callbacks
        # (回调)
        5
        callbacks = [
            _callback_tensorboard(cfg),  # tensorboardコールバック設定 (设置tensorboard回调)
            _callback_scheduler(cfg),  # スケジューラコールバック設定 (设置调度器回调)
            EpochCounter(train_data_num // cfg["batch_size"], cfg["epoch"]),  # 学習エポック数カウンターコールバック設定 (设置训练epochs回调)
            ConvSymmetrizer(model, cfg["batch_size"]),  # 対称性込みのデータ拡張コールバック設定 (设置包含对称性的扩展数据回调)0
            _callback_backup(cfg),  # バックアップ用コールバック設定 (设置备份用回调)
        ]

        if cfg.get("save_chkpt_period", None) is not None:
            callbacks.append(_callback_checkpoint(cfg))  # check pointのコールバック設定 (设置检查点的回调)

        # model.summary()
        # logdir = "/home/luan_bo/asura/scripts/logs/profiler"

        # 学習開始
        # (开始训练)
        start_time = time.time()
        # tf.profiler.experimental.start(logdir)
        # train_dataset = train_dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
        history = model.fit(
            train_dataset,
            validation_data=val_dataset,
            validation_steps=val_data_num // cfg["val_batch_size"],
            epochs=cfg["epoch"],
            steps_per_epoch=train_data_num // cfg["batch_size"],
            callbacks=callbacks,
            verbose=2,
        )
        # tf.profiler.experimental.stop()
        print("time: {}".format(time.time() - start_time))

        # freezeを強制解除してから保存
        # (解除冻结再保存)
        _unfreeze_weight(model, cfg)
        model_path = os.path.join(cfg["model_path"], "model.h5")
        model_op.save_weights(model, model_path)

        return model, history

def _check_config(cfg):
    if not tf.io.gfile.exists(cfg["dataset_path"]):
        raise FileNotFoundError(cfg["dataset_path"])

    if cfg["gpu_count"] != 0:
        if cfg["batch_size"] % cfg["gpu_count"] != 0:
            raise ValueError()

def _get_dataset(cfg, outputs):
    """trainとvalのdataset生成データ取得
    (获取train和val数据集生成数据)
    フルスクラッチ学習時にメモリエラーが起きるため、デフォルトはuse_cache=Falseにする
    (由于在全新训练时可能会发生内存错误，默认设置为use_cache=False)
    """
    decoder = DatasetDecoder(cfg, outputs, cfg["dataset_path"], normalize_mode="training", for_training_label=True)

    train_dataset, train_split_info = decoder.get_data(
        cfg["tfds_load_split_train"],
        cfg["batch_size"],
        dataaug_config=cfg["da"],
        for_training_data=True,
        shuffle=True,
        repeat=True,
        use_cache=False,
        with_split_info=True,
    )

    val_dataset, val_split_info = decoder.get_data(
        cfg["tfds_load_split_val"],
        cfg["val_batch_size"],
        dataaug_config=cfg["da"],
        for_training_data=False,
        shuffle=True,
        repeat=True,
        use_cache=False,
        with_split_info=True,
    )

    train_example_num = train_split_info.num_examples
    val_example_num = val_split_info.num_examples

    return (train_dataset, train_example_num), (val_dataset, val_example_num)

def _freeze_weight(model, config):
    """コンフィグのtrainbale設定をモデルへ反映する
    (将配置中的trainable设置应用到模型中)
    """
    for layer in model.layers:
        # backbone
        if config["model"]["backbone"]["type"] in layer.name:
            model.get_layer(layer.name).trainable = config["trainable"]["backbone"]

        # decoder
        if "decoder" in layer.name:
            model.get_layer(layer.name).trainable = config["trainable"]["decoder"]

        # trunk
        if "semaseg_trunk" in layer.name:
            model.get_layer(layer.name).trainable = config["trainable"]["semaseg_trunk"]

def _unfreeze_weight(model, config):
    """コンフィグのtrainbale設定をモデルへ反映する
    (将配置中的trainable设置应用到模型中)
    """
    for layer in model.layers:
        # backbone
        if config["model"]["backbone"]["type"] in layer.name:
            model.get_layer(layer.name).trainable = True

        # decoder
        if "decoder" in layer.name:
            model.get_layer(layer.name).trainable = True

        # trunk
        if "semaseg_trunk" in layer.name:
            model.get_layer(layer.name).trainable = True

def _reconstruction_model_io(
    model: tf.keras.models.Model,
    model_input_names: List[str],
    model_output_names: List[str],
) -> tf.keras.models.Model:
    """学習対象モデルのinput/outputを変更
    (更改学習对象模型的输入/输出)
    Args:
        model (tf.keras.models.Model): 変更対象のモデル (要更改的模型)
        model_input_names (List[str]): 学習時input名のリスト (训练时的输入名称列表)
        model_output_names (List[str]): 学習時output名のリスト (训练时的输出名称列表)
    Returns:
        tf.keras.models.Model: input/output変更後のモデル (更改input/output后的模型)
    """
    # 学習に使うinputを追加
    # (添加训练用输入)
    orig_model_inputs = [tensor for _name, tensor in zip(model.input_names, model.inputs)]
    target_model_inputs = []
    for input_name in model_input_names:
        if input_name in orig_model_inputs.keys():
            target_model_inputs.append(orig_model_inputs[input_name])

    # 学習に使うoutputを追加
    # (添加训练用输出)
    target_model_outputs = {}
    for output_name in model_output_names:
        if output_name in model.output.keys():
            target_model_outputs[output_name] = model.output[output_name]

    re_model = Model(target_model_inputs, target_model_outputs)

    return re_model

def _load_weight(model, init_weight_path):
    # load weight
    # (加载权重)
    if init_weight_path is not None:
        model_op.load_weights(model, init_weight_path, by_name=True)

def _get_initial_epoch(init_weight_path):
    initial_epoch = 0
    if init_weight_path is not None:
        if "chkpt." in init_weight_path:
            initial_epoch = int(re.findall(r"chkpt.[0-9]{4}", init_weight_path)[0])

    return initial_epoch

def _get_compile_lists(cfg):
    losses_list = {}
    loss_weights_list = {}
    metrics_list = {}

    for output_name, weight in cfg["task_weight"].items():
        output_config = cfg["model"]["output"][output_name]

        # loss設定
        # (设置损失函数)
        loss_config = output_config["loss"]
        loss_name = loss_config["func"]
        loss_func = losses.name_to_class(loss_name)

        if inspect.isclass(loss_func):
            # lossの引数設定
            # (设置损失函数的参数)
            loss_args = dict(loss_config.get("args", {}))

            if "unique_args" in loss_config.keys():
                unique_args_config = loss_config["unique_args"]
                if loss_name in unique_args_config.keys():
                    loss_args.update(dict(unique_args_config[loss_name]))

            losses_list[output_name] = loss_func(**loss_args)
        else:
            losses_list[output_name] = loss_func

        # loss weight設定
        # (设置损失权重)
        loss_weights_list[output_name] = weight

        # metrics設定
        # (设置度量标准)
        metrics_func = metrics.name_to_class(output_config["metrics"]["func"])
        if inspect.isclass(metrics_func):
            metrics_args = output_config["metrics"].get("args", {})
            metrics_list[output_name] = metrics_func(**metrics_args)
        else:
            metrics_list[output_name] = metrics_func

    return losses_list, loss_weights_list, metrics_list

def _get_optimizer(conf_lr):
    # optimizer設定 今はSGDのみ
    # (优化器设置，目前仅支持SGD)
    optimizer = optimizers.SGD(
        lr=conf_lr["base"], momentum=conf_lr["optimizer"]["momentum"], nesterov=conf_lr["optimizer"]["nesterov"]
    )
    return optimizer

def _callback_checkpoint(cfg: DictConfig) -> ModelCheckpointGCS:
    """check point保存用callback
    (检查点保存用回调)
    weightのみ保存され、optimizerや学習中の情報は保存されない。
    (仅保存权重，不保存优化器和训练过程中的信息)
    ウイのfreeze/unfreeze状態によってchkpt内weightのshapeが変わるので読み込み時注意
    (由于freeze/unfreeze状态，chkpt内的权重形状会发生变化，读取时需注意)
    Args:
        cfg (DictConfig): 学習用config (训练配置)
    Returns:
        ModelCheckpointGCS: check point保存用callback (检查点保存用回调)
    """
    chkpt_path = os.path.join(cfg["model_path"], "chkpt.{epoch:04d}.h5")
    chkpt_cb = ModelCheckpointGCS(
        chkpt_path, save_weights_only=True, save_best_only=False, verbose=1, period=cfg["save_chkpt_period"]
    )
    return chkpt_cb

def _callback_backup(cfg: DictConfig) -> BackupAndRestore:
    """backup設定用callback
    (备份设置用回调)
    optimizer等の情報含むchkptが保存され、エラー等から再開する場合はbackupから学習状態を復元する
    (保存包括优化器等信息的chkpt，如果由于错误等情况重新开始，将从备份中恢复学习状态)
    学習終了時にbackup以下のファイルは削除される
    (学习结束时，删除备份目录下的文件)
    Args:
        cfg (DictConfig): 学習用config (训练配置)
    Returns:
        BackupAndRestore: backup設定用callback (备份设置用回调)
    """
    backup_path = os.path.join(cfg["model_path"], "backup")
    backup_cb = BackupAndRestore(backup_path)
    return backup_cb

def _callback_tensorboard(cfg: DictConfig) -> TensorBoard:
    """loss/metrics記録用callback
    (损失/指标记录回调)
    Args:
        cfg (DictConfig): 学習用config (训练配置)
    Returns:
        TensorBoard: loss/metrics記録用callback (损失/指标记录回调)
    """
    tb_cb = TensorBoard(log_dir=cfg["model_path"], histogram_freq=0)
    return tb_cb

def _callback_scheduler(cfg: DictConfig) -> LearningRateScheduler:
    """lr減衰設定用callback
    (学习率衰减设置用回调)
    step decay/polynomial decayに対応
    (支持step decay/polynomial decay)
    Args:
        cfg (DictConfig): 学習用config (训练配置)
    Raises:
        ValueError: lr policyが不明な場合 (当lr policy未知时抛出ValueError)
    Returns:
        LearningRateScheduler: lr減衰設定用callback (学习率衰减设置用回调)
    """
    if cfg["lr"]["scheduler"]["policy"] == "step":
        schedule = StepDecay(initialAlpha=cfg["lr"]["base"], **cfg["lr"]["scheduler"]["step_params"])
    elif cfg["lr"]["scheduler"]["policy"] == "poly":
        schedule = PolynomialDecay(
            maxEpochs=cfg["epoch"], initialAlpha=cfg["lr"]["base"], **cfg["lr"]["scheduler"]["poly_params"]
        )
    elif cfg["lr"]["scheduler"]["policy"] == "cosine":
        schedule = CosineDecay(maxEpochs=cfg["epoch"], initialAlpha=cfg["lr"]["base"])
    elif cfg["lr"]["scheduler"]["policy"] == "warmup":
        schedule = WarmupDecay(
            base_lr=cfg["lr"]["base"], max_epochs=cfg["epoch"], **cfg["lr"]["scheduler"]["warmup_params"]
        )
    else:
        raise ValueError("Unknown learning policy.")

    lr_cb = LearningRateScheduler(schedule)
    return lr_cb
