# 🚀 5分間クイックスタート

## ステップ1：依存関係のインストール (30秒)

```bash
cd demo_v01
pip install -r requirements_v01.txt
```

## ステップ2：初期化 (10秒)

```bash
python cli_v01.py --init
```

## ステップ3：状態の確認 (5秒)

```bash
python cli_v01.py --status
```

## ステップ4：リソースの割り当て (5秒)

```bash
python cli_v01.py --allocate my_first_task 4 32
```

## ステップ5：変化の確認 (5秒)

```bash
python cli_v01.py --status
```

## ステップ6：リソースの解放 (5秒)

```bash
python cli_v01.py --release my_first_task
```

## 🎉 完了！

基本的な使用方法を習得しました！

---

## 次のステップ

### 完全なデモの実行
```bash
python demo_example.py
```

### テストの実行
```bash
python test_v01.py
```

### ドキュメントの読解
```bash
cat README_v01.md
```

---

## よく使うコマンド早見表

```bash
# 状態の確認
python cli_v01.py --status

# 詳細の確認
python cli_v01.py --detail

# リソースの割り当て (タスクID GPU数 CPU数)
python cli_v01.py --allocate <task_id> <gpus> <cpus>

# リソースの解放
python cli_v01.py --release <task_id>

# システムのリセット
python cli_v01.py --reset
```

---

**v0.2の準備はできましたか？** 🎯

`反復開発計画.md` で次のステップを確認しましょう！

