#!/usr/bin/env python3
"""
GPU资源管理器 v0.1 - 使用演示

这个脚本演示了如何使用GPUResourceManagerV01
"""

import time
from gpu_resource_manager_v01 import GPUResourceManagerV01


def demo_basic_usage():
    """演示：基本使用"""
    print("\n" + "=" * 70)
    print("演示1: 基本使用")
    print("=" * 70)
    
    # 创建管理器
    manager = GPUResourceManagerV01()
    
    # 查看初始状态
    print("\n步骤1: 查看初始状态")
    summary = manager.get_resource_summary()
    print(f"  可用GPU: {summary['total_available_gpus']}/{summary['total_gpus']}")
    print(f"  可用CPU: {summary['total_available_cpus']}/{summary['total_cpus']}")
    
    # 分配资源
    print("\n步骤2: 分配资源给任务A")
    result_a = manager.allocate_resources("task_a", 4, 32)
    if result_a:
        print(f"  ✓ 任务A分配在 {result_a['server_name']}")
        print(f"  ✓ GPU: {result_a['gpu_ids']}")
    
    # 查看更新后的状态
    print("\n步骤3: 查看更新后的状态")
    summary = manager.get_resource_summary()
    print(f"  可用GPU: {summary['total_available_gpus']}/{summary['total_gpus']}")
    print(f"  运行任务: {summary['total_running_tasks']}")
    
    # 释放资源
    print("\n步骤4: 释放资源")
    success = manager.release_resources("task_a")
    print(f"  释放结果: {'✓ 成功' if success else '✗ 失败'}")
    
    # 验证资源已释放
    print("\n步骤5: 验证资源已释放")
    summary = manager.get_resource_summary()
    print(f"  可用GPU: {summary['total_available_gpus']}/{summary['total_gpus']}")
    print(f"  运行任务: {summary['total_running_tasks']}")


def demo_multiple_tasks():
    """演示：多任务场景"""
    print("\n" + "=" * 70)
    print("演示2: 多任务场景")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    # 分配3个任务
    print("\n模拟3个用户同时请求资源:")
    tasks = [
        ("user_a_training", 4, 32),
        ("user_b_inference", 2, 16),
        ("user_c_experiment", 2, 16),
    ]
    
    allocated_tasks = []
    
    for task_id, gpus, cpus in tasks:
        print(f"\n  用户请求: {task_id} ({gpus} GPUs, {cpus} CPUs)")
        result = manager.allocate_resources(task_id, gpus, cpus)
        if result:
            allocated_tasks.append(task_id)
            print(f"    ✓ 分配成功: {result['server_name']}, GPU {result['gpu_ids']}")
        else:
            print(f"    ✗ 分配失败: 资源不足")
    
    # 显示当前资源使用情况
    print("\n当前资源使用情况:")
    summary = manager.get_resource_summary()
    for server in summary['servers']:
        if server['running_tasks'] > 0:
            print(f"  {server['server_name']}: "
                  f"{server['available_gpus']}/{server['total_gpus']} GPU可用, "
                  f"运行{server['running_tasks']}个任务")
    
    # 逐个释放资源
    print("\n逐个释放资源:")
    for task_id in allocated_tasks:
        print(f"  释放: {task_id}")
        manager.release_resources(task_id)
        time.sleep(0.5)  # 模拟任务完成时间
    
    print("\n所有资源已释放")


def demo_resource_insufficient():
    """演示：资源不足场景"""
    print("\n" + "=" * 70)
    print("演示3: 资源不足处理")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    # 分配大量资源
    print("\n尝试分配超过可用资源的任务:")
    
    allocated = 0
    for i in range(20):  # 尝试分配20个任务
        result = manager.allocate_resources(f"task_{i:02d}", 2, 16)
        if result:
            allocated += 1
        else:
            print(f"\n  第{i+1}次分配失败: 资源不足")
            print(f"  已成功分配: {allocated} 个任务")
            break
    
    # 显示资源使用情况
    summary = manager.get_resource_summary()
    gpu_used = summary['total_gpus'] - summary['total_available_gpus']
    gpu_util = gpu_used / summary['total_gpus'] * 100
    
    print(f"\n当前资源状态:")
    print(f"  GPU使用率: {gpu_util:.1f}% ({gpu_used}/{summary['total_gpus']})")
    print(f"  运行任务: {summary['total_running_tasks']}")
    
    # 清理
    print("\n清理所有任务...")
    for i in range(allocated):
        manager.release_resources(f"task_{i:02d}")
    
    print("✓ 清理完成")


def demo_api_usage():
    """演示：作为API使用"""
    print("\n" + "=" * 70)
    print("演示4: Python API使用")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    print("\n模拟训练任务:")
    
    # 1. 分配资源
    print("  1. 分配GPU资源...")
    allocation = manager.allocate_resources("training_job", 4, 32)
    
    if allocation is None:
        print("    ✗ 资源分配失败")
        return
    
    print(f"    ✓ 分配成功: 使用GPU {allocation['gpu_ids']}")
    
    # 2. 设置环境变量
    print("\n  2. 配置训练环境...")
    import os
    os.environ['CUDA_VISIBLE_DEVICES'] = allocation['gpu_devices']
    print(f"    CUDA_VISIBLE_DEVICES={allocation['gpu_devices']}")
    
    # 3. 模拟训练
    print("\n  3. 开始训练...")
    print("    Epoch 1/10...")
    time.sleep(0.5)
    print("    Epoch 5/10...")
    time.sleep(0.5)
    print("    Epoch 10/10...")
    print("    ✓ 训练完成")
    
    # 4. 释放资源
    print("\n  4. 释放资源...")
    success = manager.release_resources("training_job")
    print(f"    {'✓' if success else '✗'} 资源已释放")


def demo_detailed_info():
    """演示：查看详细信息"""
    print("\n" + "=" * 70)
    print("演示5: 详细信息查看")
    print("=" * 70)
    
    manager = GPUResourceManagerV01()
    
    # 分配一些任务
    print("\n创建一些测试任务...")
    manager.allocate_resources("job_1", 4, 32)
    manager.allocate_resources("job_2", 2, 16)
    
    # 查看详细状态
    print("\n查看详细状态:")
    status = manager.get_detailed_status()
    
    for server in status['servers']:
        print(f"\n服务器: {server['server_name']}")
        print(f"  可用GPU ID: {server['available_gpus']}")
        print(f"  可用CPU: {server['available_cpus']}")
        
        if server['running_tasks']:
            print(f"  运行中的任务:")
            for task in server['running_tasks']:
                print(f"    - {task['task_id']}")
                print(f"      GPU: {task['allocated_gpus']}")
                print(f"      CPU: {task['allocated_cpus']}")
                print(f"      开始: {task['start_time']}")
    
    # 清理
    print("\n清理...")
    manager.release_resources("job_1")
    manager.release_resources("job_2")


def main():
    """运行所有演示"""
    print("\n" + "=" * 70)
    print("GPU资源管理器 v0.1 - 完整演示")
    print("=" * 70)
    
    try:
        # 运行各个演示
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
        print("✓ 所有演示完成！")
        print("=" * 70)
        print("\n提示:")
        print("  - 查看 README_v01.md 了解更多用法")
        print("  - 运行 test_v01.py 进行测试")
        print("  - 使用 cli_v01.py 进行日常操作")
        print()
        
    except Exception as e:
        print(f"\n✗ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 确保清理
        print("\n清理环境...")
        manager = GPUResourceManagerV01()
        manager.reset_resources()


if __name__ == '__main__':
    main()

