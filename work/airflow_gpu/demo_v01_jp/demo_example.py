#!/usr/bin/env python3
"""
GPU リソースマネージャー v0.1 - 使用デモ

このスクリプトは GPUResourceManagerV01 の使用方法をデモします
"""

import time
from gpu_resource_manager_v01 import GPUResourceManagerV01


def demo_basic_usage():
    """デモ：基本的な使用方法"""
    print("\n" + "=" * 70)
    print("デモ1: 基本的な使用方法")
    print("=" * 70)
    
    # マネージャーを作成
    manager = GPUResourceManagerV01()
    
    # 初期状態を確認
    print("\nステップ1: 初期状態を確認")
    summary = manager.get_resource_summary()
    print(f"  利用可能GPU: {summary['total_available_gpus']}/{summary['total_gpus']}")
    print(f"  利用可能CPU: {summary['total_available_cpus']}/{summary['total_cpus']}")
    
    # リソースを割り当て
    print("\nステップ2: タスクAにリソースを割り当て")
    result_a = manager.allocate_resources("task_a", 4, 32)
    if result_a:
        print(f"  ✓ タスクAは {result_a['server_name']} に割り当てられました")
        print(f"  ✓ GPU: {result_a['gpu_ids']}")
    
    # 更新後の状態を確認
    print("\nステップ3: 更新後の状態を確認")
    summary = manager.get_resource_summary()
    print(f"  利用可能GPU: {summary['total_available_gpus']}/{summary['total_gpus']}")
    print(f"  実行中タスク: {summary['total_running_tasks']}")
    
    # リソースを解放
    print("\nステップ4: リソースを解放")
    success = manager.release_resources("task_a")
    print(f"  解放結果: {'✓ 成功' if success else '✗ 失敗'}")
    
    # リソースが解放されたことを確認
    print("\nステップ5: リソース解放を確認")
    summary = manager.get_resource_summary()
    print(f"  利用可能GPU: {summary['total_available_gpus']}/{summary['total_gpus']}")
    print(f"  実行中タスク: {summary['total_running_tasks']}")


def demo_multiple_tasks():
    """デモ：マルチタスクシナリオ"""
    print("\n" + "=" * 70)
    print("デモ2: マルチタスクシナリオ")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    # 3つのタスクを割り当て
    print("\n3人のユーザーが同時にリソースをリクエストするシミュレーション:")
    tasks = [
        ("user_a_training", 4, 32),
        ("user_b_inference", 2, 16),
        ("user_c_experiment", 2, 16),
    ]
    
    allocated_tasks = []
    
    for task_id, gpus, cpus in tasks:
        print(f"\n  ユーザーリクエスト: {task_id} ({gpus} GPUs, {cpus} CPUs)")
        result = manager.allocate_resources(task_id, gpus, cpus)
        if result:
            allocated_tasks.append(task_id)
            print(f"    ✓ 割り当て成功: {result['server_name']}, GPU {result['gpu_ids']}")
        else:
            print(f"    ✗ 割り当て失敗: リソース不足")
    
    # 現在のリソース使用状況を表示
    print("\n現在のリソース使用状況:")
    summary = manager.get_resource_summary()
    for server in summary['servers']:
        if server['running_tasks'] > 0:
            print(f"  {server['server_name']}: "
                  f"{server['available_gpus']}/{server['total_gpus']} GPU利用可能, "
                  f"{server['running_tasks']}個のタスクを実行中")
    
    # リソースを順次解放
    print("\nリソースを順次解放:")
    for task_id in allocated_tasks:
        print(f"  解放: {task_id}")
        manager.release_resources(task_id)
        time.sleep(0.5)  # タスク完了時間をシミュレート
    
    print("\nすべてのリソースが解放されました")


def demo_resource_insufficient():
    """デモ：リソース不足シナリオ"""
    print("\n" + "=" * 70)
    print("デモ3: リソース不足の処理")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    # 大量のリソースを割り当て
    print("\n利用可能なリソースを超えるタスクの割り当てを試行:")
    
    allocated = 0
    for i in range(20):  # 20個のタスクの割り当てを試行
        result = manager.allocate_resources(f"task_{i:02d}", 2, 16)
        if result:
            allocated += 1
        else:
            print(f"\n  第{i+1}回の割り当て失敗: リソース不足")
            print(f"  正常に割り当てられたタスク: {allocated} 個")
            break
    
    # リソース使用状況を表示
    summary = manager.get_resource_summary()
    gpu_used = summary['total_gpus'] - summary['total_available_gpus']
    gpu_util = gpu_used / summary['total_gpus'] * 100
    
    print(f"\n現在のリソース状態:")
    print(f"  GPU 使用率: {gpu_util:.1f}% ({gpu_used}/{summary['total_gpus']})")
    print(f"  実行中タスク: {summary['total_running_tasks']}")
    
    # クリーンアップ
    print("\nすべてのタスクをクリーンアップ中...")
    for i in range(allocated):
        manager.release_resources(f"task_{i:02d}")
    
    print("✓ クリーンアップ完了")


def demo_api_usage():
    """デモ：APIとして使用"""
    print("\n" + "=" * 70)
    print("デモ4: Python API の使用")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    print("\nトレーニングタスクをシミュレーション:")
    
    # 1. リソースを割り当て
    print("  1. GPU リソースを割り当て...")
    allocation = manager.allocate_resources("training_job", 4, 32)
    
    if allocation is None:
        print("    ✗ リソース割り当て失敗")
        return
    
    print(f"    ✓ 割り当て成功: GPU {allocation['gpu_ids']} を使用")
    
    # 2. 環境変数を設定
    print("\n  2. トレーニング環境を設定...")
    import os
    os.environ['CUDA_VISIBLE_DEVICES'] = allocation['gpu_devices']
    print(f"    CUDA_VISIBLE_DEVICES={allocation['gpu_devices']}")
    
    # 3. トレーニングをシミュレート
    print("\n  3. トレーニング開始...")
    print("    Epoch 1/10...")
    time.sleep(0.5)
    print("    Epoch 5/10...")
    time.sleep(0.5)
    print("    Epoch 10/10...")
    print("    ✓ トレーニング完了")
    
    # 4. リソースを解放
    print("\n  4. リソースを解放...")
    success = manager.release_resources("training_job")
    print(f"    {'✓' if success else '✗'} リソース解放完了")


def demo_detailed_info():
    """デモ：詳細情報の表示"""
    print("\n" + "=" * 70)
    print("デモ5: 詳細情報の表示")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    # いくつかのタスクを割り当て
    print("\nテストタスクを作成中...")
    manager.allocate_resources("job_1", 4, 32)
    manager.allocate_resources("job_2", 2, 16)
    
    # 詳細な状態を確認
    print("\n詳細な状態を確認:")
    status = manager.get_detailed_status()
    
    for server in status['servers']:
        print(f"\nサーバー: {server['server_name']}")
        print(f"  利用可能 GPU ID: {server['available_gpus']}")
        print(f"  利用可能 CPU: {server['available_cpus']}")
        
        if server['running_tasks']:
            print(f"  実行中のタスク:")
            for task in server['running_tasks']:
                print(f"    - {task['task_id']}")
                print(f"      GPU: {task['allocated_gpus']}")
                print(f"      CPU: {task['allocated_cpus']}")
                print(f"      開始: {task['start_time']}")
    
    # クリーンアップ
    print("\nクリーンアップ中...")
    manager.release_resources("job_1")
    manager.release_resources("job_2")


def main():
    """すべてのデモを実行"""
    print("\n" + "=" * 70)
    print("GPU リソースマネージャー v0.1 - 完全デモ")
    print("=" * 70)
    
    try:
        # 各デモを実行
        demo_basic_usage()
        time.sleep(1)
        
        demo_multiple_tasks()
        time.sleep(1)
        
        demo_resource_insufficient()
        time.sleep(1)
        
        demo_api_usage()
        time.sleep(1)
        
        demo_detailed_info()
        
        print("\n" + "=" * 70)
        print("✓ すべてのデモが完了しました！")
        print("=" * 70)
        print("\nヒント:")
        print("  - README_v01.md で詳しい使用方法を確認")
        print("  - test_v01.py でテストを実行")
        print("  - cli_v01.py で日常的な操作を実行")
        print()
        
    except Exception as e:
        print(f"\n✗ デモ中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # クリーンアップを確実に実行
        print("\n環境をクリーンアップ中...")
        manager = GPUResourceManagerV01()
        manager.reset_resources()


if __name__ == '__main__':
    main()
