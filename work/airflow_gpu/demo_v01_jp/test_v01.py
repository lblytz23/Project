"""
GPU リソースマネージャー v0.1 ユニットテスト
"""

import unittest
import os
import json
from gpu_resource_manager_v01 import GPUResourceManagerV01


class TestGPUResourceManagerV01(unittest.TestCase):
    """GPU リソースマネージャーテストクラス"""
    
    def setUp(self):
        """各テスト前に実行：環境をクリーンアップ"""
        # 存在する可能性のあるファイルを削除
        if os.path.exists(GPUResourceManagerV01.RESOURCE_FILE):
            os.remove(GPUResourceManagerV01.RESOURCE_FILE)
        if os.path.exists(GPUResourceManagerV01.LOCK_FILE):
            os.remove(GPUResourceManagerV01.LOCK_FILE)
        
        # 新しいマネージャーインスタンスを作成
        self.manager = GPUResourceManagerV01()
    
    def tearDown(self):
        """各テスト後に実行：環境をクリーンアップ"""
        # テストファイルをクリーンアップ
        if os.path.exists(GPUResourceManagerV01.RESOURCE_FILE):
            os.remove(GPUResourceManagerV01.RESOURCE_FILE)
        if os.path.exists(GPUResourceManagerV01.LOCK_FILE):
            os.remove(GPUResourceManagerV01.LOCK_FILE)
    
    def test_01_init(self):
        """テスト：システム初期化"""
        # ファイルが作成されたことを確認
        self.assertTrue(os.path.exists(GPUResourceManagerV01.RESOURCE_FILE))
        
        # 初期状態を確認
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_servers'], 4)
        self.assertEqual(summary['total_gpus'], 32)  # 4 * 8
        self.assertEqual(summary['total_available_gpus'], 32)
        self.assertEqual(summary['total_cpus'], 256)  # 4 * 64
        self.assertEqual(summary['total_available_cpus'], 256)
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_02_allocate_success(self):
        """テスト：リソース割り当て成功"""
        result = self.manager.allocate_resources("test_task_001", 4, 32)
        
        # 割り当て成功を確認
        self.assertIsNotNone(result)
        self.assertEqual(result['task_id'], "test_task_001")
        self.assertEqual(len(result['gpu_ids']), 4)
        self.assertEqual(result['cpu_count'], 32)
        self.assertIn(result['server_id'], range(4))
        
        # リソース状態の更新を確認
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 28)  # 32 - 4
        self.assertEqual(summary['total_available_cpus'], 224)  # 256 - 32
        self.assertEqual(summary['total_running_tasks'], 1)
    
    def test_03_allocate_invalid_gpus(self):
        """テスト：無効な GPU 数"""
        # GPU 数 < 2
        with self.assertRaises(ValueError):
            self.manager.allocate_resources("test_task_002", 1, 32)
        
        # GPU 数 > 8
        with self.assertRaises(ValueError):
            self.manager.allocate_resources("test_task_003", 9, 32)
    
    def test_04_allocate_invalid_cpus(self):
        """テスト：無効な CPU 数"""
        # CPU 数 > 64
        with self.assertRaises(ValueError):
            self.manager.allocate_resources("test_task_004", 4, 128)
    
    def test_05_allocate_multiple(self):
        """テスト：複数回の割り当て"""
        # 1回目の割り当て
        result1 = self.manager.allocate_resources("test_task_101", 4, 32)
        self.assertIsNotNone(result1)
        
        # 2回目の割り当て
        result2 = self.manager.allocate_resources("test_task_102", 4, 32)
        self.assertIsNotNone(result2)
        
        # 3回目の割り当て
        result3 = self.manager.allocate_resources("test_task_103", 2, 16)
        self.assertIsNotNone(result3)
        
        # リソース状態を確認
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 22)  # 32 - 4 - 4 - 2
        self.assertEqual(summary['total_running_tasks'], 3)
    
    def test_06_allocate_insufficient_resources(self):
        """テスト：リソース不足"""
        # まずすべての GPU を割り当て（4サーバー * 8GPU = 32GPU）
        # 毎回 2GPU を割り当て、合計16回割り当て可能
        for i in range(16):
            result = self.manager.allocate_resources(f"test_task_{i:03d}", 2, 16)
            self.assertIsNotNone(result, f"第{i+1}回の割り当ては成功するはずです")
        
        # すべての GPU が割り当てられたことを確認
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 0)
        
        # 再度割り当てを試みると失敗するはず
        result = self.manager.allocate_resources("test_task_fail", 2, 16)
        self.assertIsNone(result)
    
    def test_07_release_success(self):
        """テスト：リソース解放成功"""
        # まず割り当て
        result = self.manager.allocate_resources("test_task_201", 4, 32)
        self.assertIsNotNone(result)
        
        # 次に解放
        success = self.manager.release_resources("test_task_201")
        self.assertTrue(success)
        
        # リソースが返却されたことを確認
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_available_gpus'], 32)
        self.assertEqual(summary['total_available_cpus'], 256)
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_08_release_nonexistent(self):
        """テスト：存在しないタスクの解放"""
        success = self.manager.release_resources("nonexistent_task")
        self.assertFalse(success)
    
    def test_09_release_order(self):
        """テスト：任意の順序で解放"""
        # 3つのタスクを割り当て
        self.manager.allocate_resources("task_a", 2, 16)
        self.manager.allocate_resources("task_b", 2, 16)
        self.manager.allocate_resources("task_c", 2, 16)
        
        # 3つのタスクがあることを確認
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 3)
        
        # まず中間のタスクを解放
        self.manager.release_resources("task_b")
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 2)
        
        # 次に他のタスクを解放
        self.manager.release_resources("task_c")
        self.manager.release_resources("task_a")
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_10_resource_summary(self):
        """テスト：リソースサマリー機能"""
        # いくつかのリソースを割り当て
        self.manager.allocate_resources("task_1", 4, 32)
        self.manager.allocate_resources("task_2", 2, 16)
        
        summary = self.manager.get_resource_summary()
        
        # サマリー構造を確認
        self.assertIn('total_servers', summary)
        self.assertIn('servers', summary)
        self.assertIn('total_available_gpus', summary)
        
        # サーバー情報を確認
        self.assertEqual(len(summary['servers']), 4)
        for server in summary['servers']:
            self.assertIn('server_name', server)
            self.assertIn('gpu_utilization', server)
            self.assertIn('cpu_utilization', server)
    
    def test_11_detailed_status(self):
        """テスト：詳細状態機能"""
        # リソースを割り当て
        self.manager.allocate_resources("task_detail", 4, 32)
        
        status = self.manager.get_detailed_status()
        
        # 状態構造を確認
        self.assertIn('servers', status)
        self.assertIn('last_updated', status)
        self.assertIn('version', status)
        
        # タスク情報を確認
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
        """テスト：リセット機能"""
        # まずいくつかのリソースを割り当て
        self.manager.allocate_resources("task_before_reset", 4, 32)
        summary_before = self.manager.get_resource_summary()
        self.assertEqual(summary_before['total_running_tasks'], 1)
        
        # リセット
        success = self.manager.reset_resources()
        self.assertTrue(success)
        
        # リセット後の状態を確認
        summary_after = self.manager.get_resource_summary()
        self.assertEqual(summary_after['total_available_gpus'], 32)
        self.assertEqual(summary_after['total_running_tasks'], 0)
    
    def test_13_concurrent_simulation(self):
        """テスト：並行シナリオのシミュレーション"""
        # 10個のタスクが連続して高速にリクエストするシミュレーション
        tasks = []
        for i in range(10):
            result = self.manager.allocate_resources(f"concurrent_task_{i}", 2, 16)
            if result:
                tasks.append(result['task_id'])
        
        # 少なくともいくつかのタスクが割り当てられたことを確認
        self.assertGreater(len(tasks), 0)
        
        # すべてのタスクを解放
        for task_id in tasks:
            success = self.manager.release_resources(task_id)
            self.assertTrue(success)
        
        # リソースが完全に解放されたことを確認
        summary = self.manager.get_resource_summary()
        self.assertEqual(summary['total_running_tasks'], 0)
    
    def test_14_prefer_server(self):
        """テスト：優先サーバー機能"""
        # サーバー2での割り当てを指定
        result = self.manager.allocate_resources("task_prefer", 4, 32, prefer_server_id=2)
        
        # サーバー2に十分なリソースがある場合、サーバー2に割り当てられるはず
        if result:
            self.assertEqual(result['server_id'], 2)
    
    def test_15_gpu_devices_format(self):
        """テスト：GPU デバイス文字列形式"""
        result = self.manager.allocate_resources("task_gpu_format", 4, 32)
        
        self.assertIsNotNone(result)
        self.assertIn('gpu_devices', result)
        
        # 形式を確認（例："0,1,2,3"）
        gpu_devices = result['gpu_devices']
        self.assertIsInstance(gpu_devices, str)
        parts = gpu_devices.split(',')
        self.assertEqual(len(parts), 4)
        
        # すべて数字であることを確認
        for part in parts:
            self.assertTrue(part.isdigit())


def run_tests():
    """すべてのテストを実行"""
    # テストスイートを作成
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGPUResourceManagerV01)
    
    # テストを実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # サマリーを表示
    print("\n" + "=" * 70)
    print("テストサマリー")
    print("=" * 70)
    print(f"総テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ すべてのテストに合格！")
        return 0
    else:
        print("\n✗ テストに失敗があります")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(run_tests())
