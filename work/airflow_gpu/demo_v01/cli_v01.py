#!/usr/bin/env python3
"""
GPU资源管理器 CLI工具 v0.1
命令行界面，用于查看和管理GPU资源
"""

import argparse
import sys
from datetime import datetime
from tabulate import tabulate
from gpu_resource_manager_v01 import GPUResourceManagerV01


def cmd_init(args):
    """初始化资源管理系统"""
    print("初始化GPU资源管理系统...")
    manager = GPUResourceManagerV01()
    print("✓ 初始化完成！")


def cmd_status(args):
    """显示资源状态"""
    manager = GPUResourceManagerV01()
    summary = manager.get_resource_summary()
    
    print("\n" + "=" * 80)
    print("GPU资源状态")
    print("=" * 80)
    
    # 准备表格数据
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
    
    # 显示表格
    headers = ['服务器', 'GPU可用/总数', 'GPU利用率', 'CPU可用/总数', 'CPU利用率', '运行任务数']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    # 显示总计
    print("\n总计:")
    print(f"  GPU: {summary['total_available_gpus']}/{summary['total_gpus']} 可用")
    print(f"  CPU: {summary['total_available_cpus']}/{summary['total_cpus']} 可用")
    print(f"  运行任务: {summary['total_running_tasks']}")
    print()


def cmd_detail(args):
    """显示详细信息"""
    manager = GPUResourceManagerV01()
    status = manager.get_detailed_status()
    
    print("\n" + "=" * 80)
    print("GPU资源详细信息")
    print("=" * 80)
    
    for server in status['servers']:
        print(f"\n服务器: {server['server_name']} (ID: {server['server_id']})")
        print(f"  总GPU数: {server['total_gpus']}")
        print(f"  可用GPU ID: {server['available_gpus']}")
        print(f"  总CPU数: {server['total_cpus']}")
        print(f"  可用CPU数: {server['available_cpus']}")
        
        if server['running_tasks']:
            print(f"  运行中的任务 ({len(server['running_tasks'])}):")
            for task in server['running_tasks']:
                print(f"    - 任务ID: {task['task_id']}")
                print(f"      GPU: {task['allocated_gpus']}")
                print(f"      CPU: {task['allocated_cpus']}")
                print(f"      开始时间: {task['start_time']}")
        else:
            print(f"  运行中的任务: 无")
    
    print(f"\n最后更新时间: {status['last_updated']}")
    print()


def cmd_allocate(args):
    """分配资源"""
    task_id = args.task_id
    gpus = args.gpus
    cpus = args.cpus
    
    print(f"\n尝试分配资源:")
    print(f"  任务ID: {task_id}")
    print(f"  GPU数量: {gpus}")
    print(f"  CPU数量: {cpus}")
    print()
    
    manager = GPUResourceManagerV01()
    
    try:
        result = manager.allocate_resources(task_id, gpus, cpus)
        
        if result:
            print("\n✓ 资源分配成功!")
            print(f"  服务器: {result['server_name']}")
            print(f"  GPU IDs: {result['gpu_ids']}")
            print(f"  GPU设备字符串: {result['gpu_devices']}")
            print(f"  CPU数量: {result['cpu_count']}")
            print(f"\n使用提示:")
            print(f"  export CUDA_VISIBLE_DEVICES={result['gpu_devices']}")
            print(f"\n释放资源:")
            print(f"  python cli_v01.py --release {task_id}")
            print()
            return 0
        else:
            print("\n✗ 资源分配失败: 没有足够的可用资源")
            print("\n建议:")
            print("  1. 查看当前资源状态: python cli_v01.py --status")
            print("  2. 等待其他任务完成")
            print("  3. 减少资源需求")
            print()
            return 1
            
    except ValueError as e:
        print(f"\n✗ 参数错误: {e}")
        print()
        return 1


def cmd_release(args):
    """释放资源"""
    task_id = args.task_id
    
    print(f"\n尝试释放资源: {task_id}")
    
    manager = GPUResourceManagerV01()
    success = manager.release_resources(task_id)
    
    if success:
        print("✓ 资源释放成功!")
        print()
        return 0
    else:
        print("✗ 资源释放失败: 未找到该任务")
        print("\n建议:")
        print("  1. 检查任务ID是否正确")
        print("  2. 查看详细信息: python cli_v01.py --detail")
        print()
        return 1


def cmd_reset(args):
    """重置资源"""
    # 确认操作
    if not args.yes:
        print("\n⚠️  警告: 这将清除所有运行中任务的记录!")
        response = input("确定要重置吗? (yes/no): ")
        if response.lower() != 'yes':
            print("操作已取消")
            return 0
    
    print("\n重置资源管理系统...")
    manager = GPUResourceManagerV01()
    success = manager.reset_resources()
    
    if success:
        print("✓ 重置完成!")
        return 0
    else:
        print("✗ 重置失败")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='GPU资源管理器 CLI v0.1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 初始化系统
  %(prog)s --init
  
  # 查看资源状态
  %(prog)s --status
  
  # 查看详细信息
  %(prog)s --detail
  
  # 分配资源 (任务ID, GPU数量, CPU数量)
  %(prog)s --allocate task_001 4 32
  
  # 释放资源
  %(prog)s --release task_001
  
  # 重置系统 (危险操作!)
  %(prog)s --reset
        """
    )
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 或使用参数方式（更简单）
    parser.add_argument('--init', action='store_true', help='初始化资源管理系统')
    parser.add_argument('--status', action='store_true', help='显示资源状态')
    parser.add_argument('--detail', action='store_true', help='显示详细信息')
    parser.add_argument('--allocate', nargs=3, metavar=('TASK_ID', 'GPUS', 'CPUS'),
                       help='分配资源 (任务ID GPU数量 CPU数量)')
    parser.add_argument('--release', metavar='TASK_ID', help='释放资源')
    parser.add_argument('--reset', action='store_true', help='重置资源状态（危险！）')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认（用于reset）')
    
    args = parser.parse_args()
    
    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    # 执行相应的命令
    try:
        if args.init:
            return cmd_init(args)
        
        elif args.status:
            return cmd_status(args)
        
        elif args.detail:
            return cmd_detail(args)
        
        elif args.allocate:
            # 解析参数
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
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

