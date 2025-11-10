# GPU リソースマネージャー v0.1 - 最小実行可能プロダクト

## 📋 概要

これは GPU リソース管理システムの最初のバージョン（v0.1）で、コア機能であるリソース割り当てと解放を実装しています。

**バージョンの特徴**:
- ✅ コアアルゴリズム：First Fit（最初に適合）
- ✅ データストレージ：JSON ファイル
- ✅ 並行制御：ファイルロック（シングルマシン版）
- ✅ ユーザーインターフェース：コマンドラインツール（CLI）
- ✅ テストカバレッジ：15 個のユニットテスト

**適用シナリオ**: 概念実証、アルゴリズムテスト、学習理解

---

## 🚀 クイックスタート

### 1. 依存関係のインストール

```bash
pip install -r requirements_v01.txt
```

### 2. システムの初期化

```bash
python cli_v01.py --init
```

### 3. リソース状態の確認

```bash
python cli_v01.py --status
```

期待される出力：
```
================================= GPU リソース状態 =================================
┌─────────────┬──────────────┬───────────┬──────────────┬───────────┬──────────┐
│ サーバー    │ GPU利用可/合計│ GPU使用率 │ CPU利用可/合計│ CPU使用率 │ 実行中タスク│
├─────────────┼──────────────┼───────────┼──────────────┼───────────┼──────────┤
│ gpu-server-0│    8/8       │   0.0%    │   64/64      │   0.0%    │     0    │
│ gpu-server-1│    8/8       │   0.0%    │   64/64      │   0.0%    │     0    │
│ gpu-server-2│    8/8       │   0.0%    │   64/64      │   0.0%    │     0    │
│ gpu-server-3│    8/8       │   0.0%    │   64/64      │   0.0%    │     0    │
└─────────────┴──────────────┴───────────┴──────────────┴───────────┴──────────┘

合計:
  GPU: 32/32 利用可能
  CPU: 256/256 利用可能
  実行中タスク: 0
```

### 4. リソースの割り当て

```bash
# タスクに4つのGPUと32個のCPUを割り当て
python cli_v01.py --allocate my_task_001 4 32
```

出力：
```
リソース割り当てを試行中:
  タスクID: my_task_001
  GPU数: 4
  CPU数: 32

✓ リソース割り当て成功:
  サーバー: gpu-server-0
  GPU ID: [0, 1, 2, 3]
  CPU数: 32

✓ リソース割り当て成功！
  サーバー: gpu-server-0
  GPU ID: [0, 1, 2, 3]
  GPUデバイス文字列: 0,1,2,3
  CPU数: 32

使用ヒント:
  export CUDA_VISIBLE_DEVICES=0,1,2,3

リソース解放:
  python cli_v01.py --release my_task_001
```

### 5. 状態の再確認

```bash
python cli_v01.py --status
```

リソースが使用されていることが確認できます。

### 6. リソースの解放

```bash
python cli_v01.py --release my_task_001
```

出力：
```
リソース解放を試行中: my_task_001
✓ リソース解放完了: my_task_001
✓ リソース解放成功！
```

---

## 📚 詳細な使用方法

### 詳細情報の表示

```bash
python cli_v01.py --detail
```

各サーバーの詳細情報が表示されます：
- 利用可能な GPU の具体的な ID
- 実行中タスクの詳細情報
- タスク開始時刻

### システムのリセット

```bash
python cli_v01.py --reset
```

**警告**：すべての実行中タスクの記録がクリアされます！

---

## 🧪 テストの実行

すべてのユニットテストを実行：

```bash
python test_v01.py
```

期待される出力：
```
test_01_init (__main__.TestGPUResourceManagerV01) ... ok
test_02_allocate_success (__main__.TestGPUResourceManagerV01) ... ok
test_03_allocate_invalid_gpus (__main__.TestGPUResourceManagerV01) ... ok
...
test_15_gpu_devices_format (__main__.TestGPUResourceManagerV01) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.XXXs

OK

========================================================================
テストサマリー
========================================================================
総テスト数: 15
成功: 15
失敗: 0
エラー: 0

✓ すべてのテストに合格！
```

---

## 💡 使用例

### 例1：シングルユーザー学習タスク

```bash
# 1. リソースの割り当て
python cli_v01.py --allocate training_resnet50 4 32

# 2. 割り当てられたGPUを使用（実際のトレーニングスクリプト内）
export CUDA_VISIBLE_DEVICES=0,1,2,3
python train_resnet50.py --batch-size 128

# 3. トレーニング完了後にリソースを解放
python cli_v01.py --release training_resnet50
```

### 例2：マルチタスクシナリオ

```bash
# ユーザーAがリソースを割り当て
python cli_v01.py --allocate user_a_task 4 32

# ユーザーBがリソースを割り当て
python cli_v01.py --allocate user_b_task 4 32

# 現在の状態を確認
python cli_v01.py --status

# ユーザーAが完了して解放
python cli_v01.py --release user_a_task

# ユーザーCがAが解放したリソースを使用可能
python cli_v01.py --allocate user_c_task 4 32
```

### 例3：Python API の使用

```python
from gpu_resource_manager_v01 import GPUResourceManagerV01

# マネージャーを作成
manager = GPUResourceManagerV01()

# リソースを割り当て
result = manager.allocate_resources("my_task", 4, 32)

if result:
    print(f"割り当て成功、使用GPU: {result['gpu_ids']}")
    
    # トレーニングコード...
    import os
    os.environ['CUDA_VISIBLE_DEVICES'] = result['gpu_devices']
    
    # トレーニング完了後に解放
    manager.release_resources("my_task")
else:
    print("リソース不足、後で再試行してください")
```

---

## 📊 システムアーキテクチャ

```
demo_v01/
├── gpu_resource_manager_v01.py  # コアリソース管理クラス（~280行）
├── cli_v01.py                   # コマンドラインツール（~230行）
├── test_v01.py                  # ユニットテスト（~300行）
├── README_v01.md               # このファイル
├── requirements_v01.txt        # 依存リスト
├── resource_status.json        # リソース状態ファイル（自動生成）
└── .resource.lock              # ロックファイル（自動生成）
```

### データ構造

**resource_status.json**:
```json
{
  "servers": [
    {
      "server_id": 0,
      "server_name": "gpu-server-0",
      "total_gpus": 8,
      "available_gpus": [4, 5, 6, 7],
      "total_cpus": 64,
      "available_cpus": 32,
      "running_tasks": [
        {
          "task_id": "task_001",
          "allocated_gpus": [0, 1, 2, 3],
          "allocated_cpus": 32,
          "start_time": "2025-11-04T10:30:00"
        }
      ]
    }
  ],
  "last_updated": "2025-11-04T10:30:05",
  "version": "0.1"
}
```

---

## 🎯 コアアルゴリズム

### First Fit アルゴリズム

```python
def allocate_resources(task_id, required_gpus, required_cpus):
    """
    すべてのサーバーを走査し、要件を満たす最初のサーバーに割り当て
    
    時間複雑度：O(N) - Nはサーバー数（4）
    空間複雑度：O(1)
    """
    for server in servers:
        if (len(server.available_gpus) >= required_gpus and
            server.available_cpus >= required_cpus):
            # リソースを割り当て
            allocated_gpus = server.available_gpus[:required_gpus]
            server.available_gpus = server.available_gpus[required_gpus:]
            server.available_cpus -= required_cpus
            
            # タスクを記録
            server.running_tasks.append(task_info)
            
            return allocation_result
    
    return None  # リソース不足
```

---

## ⚠️ 既知の制限

### v0.1の制限

1. **シングルマシン展開**: 1台のマシンでのみ実行可能（ファイルロックの制限）
2. **Airflow統合なし**: 手動でタスク管理が必要
3. **Webインターフェースなし**: コマンドラインツールのみ
4. **シンプルなロックメカニズム**: 一部の状況で信頼性が不十分な場合あり
5. **監視機能なし**: リアルタイム監視とアラートなし

### 適用シナリオ

✅ **適している**:
- 概念実証
- アルゴリズムテスト
- 学習と理解
- シングルユーザー環境

❌ **適していない**:
- 本番環境
- マルチマシン展開
- 高並行性シナリオ
- 監視が必要なシナリオ

---

## 🔄 アップグレードパス

v0.1完了後、以下にアップグレード可能：

### v0.2 - Airflow統合版
- ✅ Apache Airflow統合
- ✅ Airflow Variables使用
- ✅ シンプルなWeb監視インターフェース
- ✅ 自動化されたタスクスケジューリング

### v0.3 - プレプロダクション版
- ✅ SSHリモート実行
- ✅ Dockerコンテナ統合
- ✅ Redis分散ロック
- ✅ 完全な監視ダッシュボード

### v1.0 - プロダクション版
- ✅ 高可用性アーキテクチャ
- ✅ 完全な監視とアラート
- ✅ CI/CDプロセス
- ✅ セキュリティ強化

---

## 🐛 トラブルシューティング

### 問題1: ロック取得タイムアウト

**症状**: コマンド実行時に「✗ ロック取得タイムアウト」と表示

**原因**: 
- 別のプロセスがリソースマネージャーを使用中
- 前回の操作が異常終了し、ロックが解放されていない

**解決方法**:
```bash
# ロックファイルを削除
rm .resource.lock

# コマンドを再実行
python cli_v01.py --status
```

### 問題2: resource_status.json が破損

**症状**: JSONパースエラーが発生

**解決方法**:
```bash
# システムをリセット
python cli_v01.py --reset --yes
```

### 問題3: リソースリーク

**症状**: タスクは完了したが、リソースが解放されていない

**原因**: release呼び出しを忘れた

**解決方法**:
```bash
# すべてのタスクを確認
python cli_v01.py --detail

# 手動で解放
python cli_v01.py --release <task_id>

# またはシステムをリセット（すべてのタスクをクリア）
python cli_v01.py --reset
```

---

## 📖 APIリファレンス

### GPUResourceManagerV01 クラス

#### `__init__()`
リソースマネージャーを初期化

#### `allocate_resources(task_id, required_gpus, required_cpus, prefer_server_id=None)`
リソースを割り当て

**パラメータ**:
- `task_id` (str): タスクの一意識別子
- `required_gpus` (int): GPU数（2-8）
- `required_cpus` (int): CPU数（1-64）
- `prefer_server_id` (int, optional): 優先サーバーID

**戻り値**: dict または None

#### `release_resources(task_id)`
リソースを解放

**パラメータ**:
- `task_id` (str): タスク識別子

**戻り値**: bool

#### `get_resource_summary()`
リソースサマリーを取得

**戻り値**: dict

#### `get_detailed_status()`
詳細な状態を取得

**戻り値**: dict

#### `reset_resources()`
すべてのリソースをリセット

**戻り値**: bool

---

## 🎓 学習リソース

### 推奨読書順序

1. 📖 このREADME（クイックスタート）
2. 📐 基礎設計ドキュメント.md（アーキテクチャの理解）
3. 🔬 詳細設計ドキュメント.md（アルゴリズムの深掘り）
4. 💻 ソースコードコメント（実装の詳細）

### 練習の提案

1. ✅ すべての例を実行
2. ✅ テストコードを読んで実行
3. ✅ 設定の変更を試す（サーバー数、GPU数）
4. ✅ 新機能の実装（リソース予約など）

---

## 📝 ライセンス

MIT License

---

## 🚀 次のステップ

v0.1の学習とテスト完了後：

1. 📊 パフォーマンステストの実行
2. 🐛 発見された問題の修正
3. 📚 v0.2計画の読解
4. 🎯 v0.2開発の開始

---

**お使いいただきありがとうございます！** 🎉

*問題がある場合は、《反復開発計画.md》または《クイックスタートガイド.md》を参照してください*

