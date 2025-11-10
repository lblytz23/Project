"""
GPU资源管理器 v0.1 单元测试
"""

import unittest
import os
import json
from gpu_resource_manager_v01 import GPUResourceManagerV01


class TestGPUResourceManagerV01(unittest.TestCase):
    """GPU资源管理器测试类"""
    
    def setUp(self):
        """每个测试前执行：清理环境"""
        # 删除可能存在的文件
        if os.path.exists(GPUResourceManagerV01.RESOURCE_FILE):
            os.remove(GPUResourceManagerV01.RESOURCE_FILE)
        if os.path.exists(GPUResourceManagerV01.LOCK_FILE):
            os.remove(GPUResourceManagerV01.LOCK_FILE)
        
        # 创建新的管理器实例
        self.manager = GPUResourceManagerV01()
    
    def tearDown(self):
        """每个测试后执行：清理环境"""
        # 清理测试文件
        if os.path.exists(GPUResourceManagerV01.RESOURCE_FILE):
            os.remove(GPUResourceManagerV01.RESOURCE_FILE)
        if os.path.exists(GPUResourceManagerV01.LOCK_FILE):
            os.remove(GPUResourceManagerV01.LOCK_FILE)
    
    def test_01_init(self):
        """测试：系统初始化"""
        # 验证文件已创建
        self.assertTrue(os.path.exists(GPUResourceManagerV01.RESOURCE_FILE))
        
        # 验证初始状态
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_servers'], 4)
        self.assertEqual(summary['total_gpus'], 32)  # 4 * 8
        self.assertEqual(summary['total_available_gpus'], 32)
        self.assertEqual(summary['total_cpus'], 256)  # 4 * 64
        self.assertEqual(summary['total_available_cpus'], 256)
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_02_allocate_success(self):
        """测试：成功分配资源"""
        result = self.manager.allocate_resources("test_task_001", 4, 32)
        
        # 验证分配成功
        self.assertIsNotNone(result)
        self.assertEqual(result['task_id'], "test_task_001")
        self.assertEqual(len(result['gpu_ids']), 4)
        self.assertEqual(result['cpu_count'], 32)
        self.assertIn(result['server_id'], range(4))
        
        # 验证资源状态更新
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 28)  # 32 - 4
        self.assertEqual(summary['total_available_cpus'], 224)  # 256 - 32
        self.assertEqual(summary['total_running_tasks'], 1)
    
    def test_03_allocate_invalid_gpus(self):
        """测试：无效的GPU数量"""
        # GPU数量 < 2
        with self.assertRaises(ValueError):
            self.manager.allocate_resources("test_task_002", 1, 32)
        
        # GPU数量 > 8
        with self.assertRaises(ValueError):
            self.manager.allocate_resources("test_task_003", 9, 32)
    
    def test_04_allocate_invalid_cpus(self):
        """测试：无效的CPU数量"""
        # CPU数量 > 64
        with self.assertRaises(ValueError):
            self.manager.allocate_resources("test_task_004", 4, 128)
    
    def test_05_allocate_multiple(self):
        """测试：多次分配"""
        # 第1次分配
        result1 = self.manager.allocate_resources("test_task_101", 4, 32)
        self.assertIsNotNone(result1)
        
        # 第2次分配
        result2 = self.manager.allocate_resources("test_task_102", 4, 32)
        self.assertIsNotNone(result2)
        
        # 第3次分配
        result3 = self.manager.allocate_resources("test_task_103", 2, 16)
        self.assertIsNotNone(result3)
        
        # 验证资源状态
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 22)  # 32 - 4 - 4 - 2
        self.assertEqual(summary['total_running_tasks'], 3)
    
    def test_06_allocate_insufficient_resources(self):
        """测试：资源不足"""
        # 先分配满所有GPU（4个服务器 * 8个GPU = 32个GPU）
        # 每次分配2个GPU，总共可以分配16次
        for i in range(16):
            result = self.manager.allocate_resources(f"test_task_{i:03d}", 2, 16)
            self.assertIsNotNone(result, f"第{i+1}次分配应该成功")
        
        # 验证所有GPU都已分配
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 0)
        
        # 再次尝试分配应该失败
        result = self.manager.allocate_resources("test_task_fail", 2, 16)
        self.assertIsNone(result)
    
    def test_07_release_success(self):
        """测试：成功释放资源"""
        # 先分配
        result = self.manager.allocate_resources("test_task_201", 4, 32)
        self.assertIsNotNone(result)
        
        # 再释放
        success = self.manager.release_resources("test_task_201")
        self.assertTrue(success)
        
        # 验证资源已归还
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 32)
        self.assertEqual(summary['total_available_cpus'], 256)
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_08_release_nonexistent(self):
        """测试：释放不存在的任务"""
        success = self.manager.release_resources("nonexistent_task")
        self.assertFalse(success)
    
    def test_09_release_order(self):
        """测试：按任意顺序释放"""
        # 分配3个任务
        self.manager.allocate_resources("task_a", 2, 16)
        self.manager.allocate_resources("task_b", 2, 16)
        self.manager.allocate_resources("task_c", 2, 16)
        
        # 验证有3个任务
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 3)
        
        # 先释放中间的任务
        self.manager.release_resources("task_b")
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 2)
        
        # 再释放其他任务
        self.manager.release_resources("task_c")
        self.manager.release_resources("task_a")
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_10_resource_summary(self):
        """测试：资源摘要功能"""
        # 分配一些资源
        self.manager.allocate_resources("task_1", 4, 32)
        self.manager.allocate_resources("task_2", 2, 16)
        
        summary = self.manager.get_resource_summary()
        
        # 验证摘要结构
        self.assertIn('total_servers', summary)
        self.assertIn('servers', summary)
        self.assertIn('total_available_gpus', summary)
        
        # 验证服务器信息
        self.assertEqual(len(summary['servers']), 4)
        for server in summary['servers']:
            self.assertIn('server_name', server)
            self.assertIn('gpu_utilization', server)
            self.assertIn('cpu_utilization', server)
    
    def test_11_detailed_status(self):
        """测试：详细状态功能"""
        # 分配资源
        self.manager.allocate_resources("task_detail", 4, 32)
        
        status = self.manager.get_detailed_status()
        
        # 验证状态结构
        self.assertIn('servers', status)
        self.assertIn('last_updated', status)
        self.assertIn('version', status)
        
        # 验证任务信息
        found_task = False
        for server in status['servers']:
            for task in server['running_tasks']:
                if task['task_id'] == "task_detail":
                    found_task = True
                    self.assertIn('allocated_gpus', task)
                    self.assertIn('allocated_cpus', task)
                    self.assertIn('start_time', task)
        
        self.assertTrue(found_task)
    
    def test_12_reset(self):
        """测试：重置功能"""
        # 先分配一些资源
        self.manager.allocate_resources("task_before_reset", 4, 32)
        summary_before = self.manager.get_resource_summary()
        self.assertEqual(summary_before['total_running_tasks'], 1)
        
        # 重置
        success = self.manager.reset_resources()
        self.assertTrue(success)
        
        # 验证重置后状态
        summary_after = self.manager.get_resource_summary()
        self.assertEqual(summary_after['total_available_gpus'], 32)
        self.assertEqual(summary_after['total_running_tasks'], 0)
    
    def test_13_concurrent_simulation(self):
        """测试：模拟并发场景"""
        # 模拟10个任务快速连续请求
        tasks = []
        for i in range(10):
            result = self.manager.allocate_resources(f"concurrent_task_{i}", 2, 16)
            if result:
                tasks.append(result['task_id'])
        
        # 验证至少分配了一些任务
        self.assertGreater(len(tasks), 0)
        
        # 释放所有任务
        for task_id in tasks:
            success = self.manager.release_resources(task_id)
            self.assertTrue(success)
        
        # 验证资源完全释放
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_14_prefer_server(self):
        """测试：优先服务器功能"""
        # 指定在服务器2上分配
        result = self.manager.allocate_resources("task_prefer", 4, 32, prefer_server_id=2)
        
        # 如果服务器2有足够资源，应该分配在服务器2上
        if result:
            self.assertEqual(result['server_id'], 2)
    
    def test_15_gpu_devices_format(self):
        """测试：GPU设备字符串格式"""
        result = self.manager.allocate_resources("task_gpu_format", 4, 32)
        
        self.assertIsNotNone(result)
        self.assertIn('gpu_devices', result)
        
        # 验证格式（例如："0,1,2,3"）
        gpu_devices = result['gpu_devices']
        self.assertIsInstance(gpu_devices, str)
        parts = gpu_devices.split(',')
        self.assertEqual(len(parts), 4)
        
        # 验证都是数字
        for part in parts:
            self.assertTrue(part.isdigit())


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGPUResourceManagerV01)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印摘要
    print("\n" + "=" * 70)
    print("测试摘要")
    print("=" * 70)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 有测试失败")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(run_tests())

