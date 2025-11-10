"""
GPU リソースマネージャー設定テンプレート
このファイルを config.py としてコピーし、実際の状況に応じて変更してください
"""

# ============================================================
# 基本設定 - 変更必須
# ============================================================

# サーバー設定
TOTAL_SERVERS = 4        # GPU サーバーは何台ありますか？
GPUS_PER_SERVER = 8      # 各サーバーに GPU は何個ありますか？
CPUS_PER_SERVER = 64     # 各サーバーに CPU は何個ありますか？

# 例：
# - 2台のサーバー、各4GPU、32CPU：TOTAL_SERVERS=2, GPUS_PER_SERVER=4, CPUS_PER_SERVER=32
# - 8台のサーバー、各8GPU、128CPU：TOTAL_SERVERS=8, GPUS_PER_SERVER=8, CPUS_PER_SERVER=128


# ============================================================
# ファイルパス設定 - オプション変更
# ============================================================

import os

# 方案1：現在のディレクトリを使用（デフォルト、テストに適している）
DATA_DIR = "."
RESOURCE_FILE = "resource_status.json"
LOCK_FILE = ".resource.lock"

# 方案2：固定ディレクトリを使用（本番環境推奨）
# DATA_DIR = "/var/lib/gpu_manager"           # Linux
# DATA_DIR = "C:\\ProgramData\\GPUManager"    # Windows
# RESOURCE_FILE = os.path.join(DATA_DIR, "resource_status.json")
# LOCK_FILE = os.path.join(DATA_DIR, ".resource.lock")

# 方案3：ユーザーホームディレクトリを使用
# from pathlib import Path
# DATA_DIR = str(Path.home() / ".gpu_manager")
# RESOURCE_FILE = os.path.join(DATA_DIR, "resource_status.json")
# LOCK_FILE = os.path.join(DATA_DIR, ".resource.lock")


# ============================================================
# サーバー設定 - オプション変更
# ============================================================

# サーバー命名スキーム
# 方案1：デフォルト命名（gpu-server-0, gpu-server-1, ...）
def get_server_name(server_id):
    return f"gpu-server-{server_id}"

# 方案2：実際のホスト名を使用
# def get_server_name(server_id):
#     server_names = ["node01", "node02", "node03", "node04"]
#     return server_names[server_id]

# 方案3：IPアドレスを使用
# def get_server_name(server_id):
#     server_ips = ["192.168.1.11", "192.168.1.12", "192.168.1.13", "192.168.1.14"]
#     return server_ips[server_id]

# 方案4：混合設定（異なるサーバー構成）
# サーバーの構成が異なる場合、各サーバーの具体的な設定を定義
CUSTOM_SERVERS = None  # None に設定すると統一設定を使用

# コメントを解除して変更し、カスタム設定を使用
# CUSTOM_SERVERS = [
#     {"id": 0, "name": "high-gpu-01", "gpus": 8, "cpus": 128},
#     {"id": 1, "name": "high-gpu-02", "gpus": 8, "cpus": 128},
#     {"id": 2, "name": "low-gpu-01",  "gpus": 4, "cpus": 64},
#     {"id": 3, "name": "low-gpu-02",  "gpus": 4, "cpus": 64},
# ]


# ============================================================
# リソース制限設定 - オプション変更
# ============================================================

# GPU 数の制限
MIN_GPUS = 2             # 最小で何個の GPU が必要ですか？（1 に設定すると単一 GPU タスクを許可）
MAX_GPUS = GPUS_PER_SERVER  # 最大で何個の GPU を許可しますか？

# CPU 数の制限
MIN_CPUS = 1             # 最小で何個の CPU が必要ですか？
MAX_CPUS = CPUS_PER_SERVER  # 最大で何個の CPU を許可しますか？


# ============================================================
# ロック設定 - Windows ユーザーは変更必須
# ============================================================

import sys

# ロックメカニズムの選択
# オプション1: 'fcntl' - Linux/Unix（デフォルト）
# オプション2: 'filelock' - クロスプラットフォーム（pip install filelock が必要）
# オプション3: 'simple' - シンプルなフラグファイルロック

if sys.platform == 'win32':
    LOCK_TYPE = 'filelock'  # Windows では filelock を推奨
else:
    LOCK_TYPE = 'fcntl'     # Linux では fcntl を推奨

# ロックタイムアウト時間（秒）
LOCK_TIMEOUT = 60        # ロック取得の最大待機時間


# ============================================================
# 表示設定 - オプション変更
# ============================================================

# CLI テーブル表示言語
USE_JAPANESE = True       # True=日本語、False=英語

# テーブル表示形式
TABLE_FORMAT = 'grid'    # オプション：'grid', 'simple', 'plain', 'fancy_grid'


# ============================================================
# 高度な設定 - 通常は変更不要
# ============================================================

# バージョン番号
VERSION = "0.1"

# ログレベル
LOG_LEVEL = "INFO"       # DEBUG, INFO, WARNING, ERROR

# 状態ファイルエンコーディング
FILE_ENCODING = "utf-8"

# JSON インデント
JSON_INDENT = 2


# ============================================================
# 設定検証
# ============================================================

def validate_config():
    """設定が適切かどうかを検証"""
    errors = []
    
    if TOTAL_SERVERS < 1:
        errors.append(f"サーバー数は >= 1 である必要があります、現在: {TOTAL_SERVERS}")
    
    if GPUS_PER_SERVER < 1:
        errors.append(f"各サーバーのGPU数は >= 1 である必要があります、現在: {GPUS_PER_SERVER}")
    
    if CPUS_PER_SERVER < 1:
        errors.append(f"各サーバーのCPU数は >= 1 である必要があります、現在: {CPUS_PER_SERVER}")
    
    if MIN_GPUS < 1 or MIN_GPUS > MAX_GPUS:
        errors.append(f"GPU最小値は 1-{MAX_GPUS} の間である必要があります、現在: {MIN_GPUS}")
    
    if CUSTOM_SERVERS:
        if len(CUSTOM_SERVERS) != TOTAL_SERVERS:
            errors.append(f"カスタムサーバー数({len(CUSTOM_SERVERS)})がTOTAL_SERVERS({TOTAL_SERVERS})と一致しません")
    
    if LOCK_TYPE not in ['fcntl', 'filelock', 'simple']:
        errors.append(f"無効なロックタイプ: {LOCK_TYPE}")
    
    if errors:
        print("❌ 設定エラー:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


# ============================================================
# 設定情報の表示
# ============================================================

def show_config():
    """現在の設定を表示"""
    print("\n" + "=" * 60)
    print("GPU リソースマネージャー設定")
    print("=" * 60)
    print(f"\nサーバー設定:")
    print(f"  サーバー数: {TOTAL_SERVERS}")
    print(f"  各サーバーGPU数: {GPUS_PER_SERVER}")
    print(f"  各サーバーCPU数: {CPUS_PER_SERVER}")
    print(f"  総GPU数: {TOTAL_SERVERS * GPUS_PER_SERVER}")
    print(f"  総CPU数: {TOTAL_SERVERS * CPUS_PER_SERVER}")
    
    print(f"\nファイルパス:")
    print(f"  データディレクトリ: {DATA_DIR if DATA_DIR != '.' else '現在のディレクトリ'}")
    print(f"  状態ファイル: {RESOURCE_FILE}")
    print(f"  ロックファイル: {LOCK_FILE}")
    
    print(f"\nリソース制限:")
    print(f"  GPU範囲: {MIN_GPUS}-{MAX_GPUS}")
    print(f"  CPU範囲: {MIN_CPUS}-{MAX_CPUS}")
    
    print(f"\nロック設定:")
    print(f"  ロックタイプ: {LOCK_TYPE}")
    print(f"  ロックタイムアウト: {LOCK_TIMEOUT}秒")
    
    if CUSTOM_SERVERS:
        print(f"\nカスタムサーバー設定:")
        for srv in CUSTOM_SERVERS:
            print(f"  {srv['name']}: {srv['gpus']} GPUs, {srv['cpus']} CPUs")
    
    print("\n" + "=" * 60 + "\n")


# ============================================================
# 使用例
# ============================================================

if __name__ == "__main__":
    print("\n設定テンプレート使用説明：")
    print("1. このファイルを config.py としてコピー")
    print("2. 実際の状況に応じて設定を変更")
    print("3. メインプログラムでインポート: from config import *")
    print("4. 検証を実行: python config.py")
    
    print("\n現在の設定:")
    show_config()
    
    print("設定検証:")
    if validate_config():
        print("✅ 設定は有効です！")
    else:
        print("❌ 設定にエラーがあります、修正してから使用してください")
