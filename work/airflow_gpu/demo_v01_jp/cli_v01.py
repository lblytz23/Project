#!/usr/bin/env python3
"""
GPU リソースマネージャー CLI ツール v0.1
コマンドラインインターフェース、GPU リソースの表示と管理用
"""

import argparse
import sys
from datetime import datetime
from tabulate import tabulate
from gpu_resource_manager_v01 import GPUResourceManagerV01


def cmd_init(args):
    """リソース管理システムを初期化"""
    print("GPU リソース管理システムを初期化中...")
    manager = GPUResourceManagerV01()
    print("✓ 初期化完了！")


def cmd_status(args):
    """リソース状態を表示"""
    manager = GPUResourceManagerV01()
    summary = manager.get_resource_summary()
    
    print("\n" + "=" * 80)
    print("GPU リソース状態")
    print("=" * 80)
    
    # テーブルデータを準備
    table_data = []
    for server in summary['servers']:
        table_data.append([
            server['server_name'],
            f"{server['available_gpus']}/{server['total_gpus']}",
            server['gpu_utilization'],
            f"{server['available_cpus']}/{server['total_cpus']}",
            server['cpu_utilization'],
            server['running_tasks']
        ])
    
    # テーブルを表示
    headers = ['サーバー', 'GPU利用可/合計', 'GPU使用率', 'CPU利用可/合計', 'CPU使用率', '実行中タスク数']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    # 合計を表示
    print("\n合計:")
    print(f"  GPU: {summary['total_available_gpus']}/{summary['total_gpus']} 利用可能")
    print(f"  CPU: {summary['total_available_cpus']}/{summary['total_cpus']} 利用可能")
    print(f"  実行中タスク: {summary['total_running_tasks']}")
    print()


def cmd_detail(args):
    """詳細情報を表示"""
    manager = GPUResourceManagerV01()
    status = manager.get_detailed_status()
    
    print("\n" + "=" * 80)
    print("GPU リソース詳細情報")
    print("=" * 80)
    
    for server in status['servers']:
        print(f"\nサーバー: {server['server_name']} (ID: {server['server_id']})")
        print(f"  総 GPU 数: {server['total_gpus']}")
        print(f"  利用可能 GPU ID: {server['available_gpus']}")
        print(f"  総 CPU 数: {server['total_cpus']}")
        print(f"  利用可能 CPU 数: {server['available_cpus']}")
        
        if server['running_tasks']:
            print(f"  実行中のタスク ({len(server['running_tasks'])}):")
            for task in server['running_tasks']:
                print(f"    - タスク ID: {task['task_id']}")
                print(f"      GPU: {task['allocated_gpus']}")
                print(f"      CPU: {task['allocated_cpus']}")
                print(f"      開始時刻: {task['start_time']}")
        else:
            print(f"  実行中のタスク: なし")
    
    print(f"\n最終更新時刻: {status['last_updated']}")
    print()


def cmd_allocate(args):
    """リソースを割り当て"""
    task_id = args.task_id
    gpus = args.gpus
    cpus = args.cpus
    
    print(f"\nリソース割り当てを試行中:")
    print(f"  タスク ID: {task_id}")
    print(f"  GPU 数: {gpus}")
    print(f"  CPU 数: {cpus}")
    print()
    
    manager = GPUResourceManagerV01()
    
    try:
        result = manager.allocate_resources(task_id, gpus, cpus)
        
        if result:
            print("\n✓ リソース割り当て成功！")
            print(f"  サーバー: {result['server_name']}")
            print(f"  GPU ID: {result['gpu_ids']}")
            print(f"  GPU デバイス文字列: {result['gpu_devices']}")
            print(f"  CPU 数: {result['cpu_count']}")
            print(f"\n使用ヒント:")
            print(f"  export CUDA_VISIBLE_DEVICES={result['gpu_devices']}")
            print(f"\nリソース解放:")
            print(f"  python cli_v01.py --release {task_id}")
            print()
            return 0
        else:
            print("\n✗ リソース割り当て失敗: 利用可能なリソースが不足しています")
            print("\n提案:")
            print("  1. 現在のリソース状態を確認: python cli_v01.py --status")
            print("  2. 他のタスクが完了するまで待機")
            print("  3. リソース要求を減らす")
            print()
            return 1
            
    except ValueError as e:
        print(f"\n✗ パラメータエラー: {e}")
        print()
        return 1


def cmd_release(args):
    """リソースを解放"""
    task_id = args.task_id
    
    print(f"\nリソース解放を試行中: {task_id}")
    
    manager = GPUResourceManagerV01()
    success = manager.release_resources(task_id)
    
    if success:
        print("✓ リソース解放成功！")
        print()
        return 0
    else:
        print("✗ リソース解放失敗: タスクが見つかりません")
        print("\n提案:")
        print("  1. タスク ID が正しいか確認")
        print("  2. 詳細情報を確認: python cli_v01.py --detail")
        print()
        return 1


def cmd_reset(args):
    """リソースをリセット"""
    # 操作を確認
    if not args.yes:
        print("\n⚠️  警告: 実行中のすべてのタスク記録がクリアされます！")
        response = input("リセットしてもよろしいですか? (yes/no): ")
        if response.lower() != 'yes':
            print("操作がキャンセルされました")
            return 0
    
    print("\nリソース管理システムをリセット中...")
    manager = GPUResourceManagerV01()
    success = manager.reset_resources()
    
    if success:
        print("✓ リセット完了！")
        return 0
    else:
        print("✗ リセット失敗")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='GPU リソースマネージャー CLI v0.1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # システムを初期化
  %(prog)s --init
  
  # リソース状態を確認
  %(prog)s --status
  
  # 詳細情報を確認
  %(prog)s --detail
  
  # リソースを割り当て (タスクID, GPU数, CPU数)
  %(prog)s --allocate task_001 4 32
  
  # リソースを解放
  %(prog)s --release task_001
  
  # システムをリセット (危険な操作!)
  %(prog)s --reset
        """
    )
    
    # サブコマンドを作成
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # またはパラメータ方式（よりシンプル）
    parser.add_argument('--init', action='store_true', help='リソース管理システムを初期化')
    parser.add_argument('--status', action='store_true', help='リソース状態を表示')
    parser.add_argument('--detail', action='store_true', help='詳細情報を表示')
    parser.add_argument('--allocate', nargs=3, metavar=('TASK_ID', 'GPUS', 'CPUS'),
                       help='リソースを割り当て (タスクID GPU数 CPU数)')
    parser.add_argument('--release', metavar='TASK_ID', help='リソースを解放')
    parser.add_argument('--reset', action='store_true', help='リソース状態をリセット（危険！）')
    parser.add_argument('--yes', '-y', action='store_true', help='自動確認（reset用）')
    
    args = parser.parse_args()
    
    # パラメータがない場合、ヘルプを表示
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    # 対応するコマンドを実行
    try:
        if args.init:
            return cmd_init(args)
        
        elif args.status:
            return cmd_status(args)
        
        elif args.detail:
            return cmd_detail(args)
        
        elif args.allocate:
            # パラメータを解析
            task_id, gpus, cpus = args.allocate
            args.task_id = task_id
            args.gpus = int(gpus)
            args.cpus = int(cpus)
            return cmd_allocate(args)
        
        elif args.release:
            args.task_id = args.release
            return cmd_release(args)
        
        elif args.reset:
            return cmd_reset(args)
        
        else:
            parser.print_help()
            return 0
            
    except Exception as e:
        print(f"\n✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
