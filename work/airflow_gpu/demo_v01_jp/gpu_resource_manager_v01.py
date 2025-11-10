"""
GPU リソースマネージャー v0.1 - 最小実行可能版
機能：コアリソース割り当ておよび解放アルゴリズム

特徴：
- JSON ファイルでリソース状態を保存
- シンプルなファイルロックメカニズム（シングルマシン版）
- First Fit アルゴリズム
- Airflow やその他の複雑なコンポーネントに依存しない
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
import fcntl


class GPUResourceManagerV01:
    """
    GPU リソースマネージャー v0.1
    
    設定：
    - 4台のサーバー、各8GPU、64CPU
    """
    
    # システム設定
    TOTAL_SERVERS = 4
    GPUS_PER_SERVER = 8
    CPUS_PER_SERVER = 64
    
    # ファイルパス
    RESOURCE_FILE = "resource_status.json"
    LOCK_FILE = ".resource.lock"
    
    def __init__(self):
        """リソースマネージャーを初期化"""
        self._init_resource_file()
    
    def _init_resource_file(self):
        """リソース状態ファイルを初期化"""
        if not os.path.exists(self.RESOURCE_FILE):
            initial_status = {
                "servers": [
                    {
                        "server_id": i,
                        "server_name": f"gpu-server-{i}",
                        "total_gpus": self.GPUS_PER_SERVER,
                        "available_gpus": list(range(self.GPUS_PER_SERVER)),
                        "total_cpus": self.CPUS_PER_SERVER,
                        "available_cpus": self.CPUS_PER_SERVER,
                        "running_tasks": []
                    }
                    for i in range(self.TOTAL_SERVERS)
                ],
                "last_updated": datetime.now().isoformat(),
                "version": "0.1"
            }
            self._write_status(initial_status)
            print(f"✓ リソース状態ファイルが作成されました: {self.RESOURCE_FILE}")
    
    def _acquire_lock(self, timeout: int = 60) -> Optional[object]:
        """
        ファイルロックを取得
        
        Args:
            timeout: タイムアウト時間（秒）
        
        Returns:
            ファイルオブジェクト（ロック解放用）、失敗時は None
        """
        lock_file = open(self.LOCK_FILE, 'w')
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 排他ロックを取得（ノンブロッキング）
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_file
            except IOError:
                # ロックが占有されている、待機
                time.sleep(0.1)
        
        # タイムアウト
        lock_file.close()
        return None
    
    def _release_lock(self, lock_file: object):
        """ファイルロックを解放"""
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except Exception as e:
                print(f"⚠ ロック解放時にエラー: {e}")
    
    def _read_status(self) -> Dict:
        """リソース状態を読み取り"""
        with open(self.RESOURCE_FILE, 'r') as f:
            return json.load(f)
    
    def _write_status(self, status: Dict):
        """リソース状態を書き込み"""
        status['last_updated'] = datetime.now().isoformat()
        with open(self.RESOURCE_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    
    def allocate_resources(
        self,
        task_id: str,
        required_gpus: int,
        required_cpus: int,
        prefer_server_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        GPU および CPU リソースを割り当て
        
        アルゴリズム：First Fit アルゴリズム
        
        Args:
            task_id: タスク一意識別子
            required_gpus: 必要な GPU 数（2-8）
            required_cpus: 必要な CPU 数（1-64）
            prefer_server_id: 優先するサーバー ID（オプション）
        
        Returns:
            割り当て成功時は辞書を返す：
            {
                'server_id': int,
                'server_name': str,
                'gpu_ids': List[int],
                'cpu_count': int,
                'gpu_devices': str,  # CUDA_VISIBLE_DEVICES 用
                'task_id': str
            }
            割り当て失敗時は None
        
        Raises:
            ValueError: パラメータが不正
        """
        # パラメータ検証
        if not (2 <= required_gpus <= 8):
            raise ValueError(f"GPU 数は 2-8 の間である必要があります、現在値: {required_gpus}")
        
        if not (1 <= required_cpus <= self.CPUS_PER_SERVER):
            raise ValueError(f"CPU 数は 1-{self.CPUS_PER_SERVER} の間である必要があります、現在値: {required_cpus}")
        
        if prefer_server_id is not None:
            if not (0 <= prefer_server_id < self.TOTAL_SERVERS):
                raise ValueError(f"サーバー ID は 0-{self.TOTAL_SERVERS-1} の間である必要があります")
        
        # ロックを取得
        lock_file = self._acquire_lock()
        if lock_file is None:
            print("✗ ロック取得タイムアウト")
            return None
        
        try:
            # 現在の状態を読み取り
            status = self._read_status()
            selected_server = None
            
            # 優先サーバーが指定されている場合、まず確認
            if prefer_server_id is not None:
                server = status['servers'][prefer_server_id]
                if (len(server['available_gpus']) >= required_gpus and
                    server['available_cpus'] >= required_cpus):
                    selected_server = server
            
            # 優先サーバーが利用不可または未指定の場合、すべてのサーバーを走査
            if selected_server is None:
                for server in status['servers']:
                    if (len(server['available_gpus']) >= required_gpus and
                        server['available_cpus'] >= required_cpus):
                        selected_server = server
                        break
            
            # 適切なサーバーが見つからない
            if selected_server is None:
                print(f"✗ リソース不足: {required_gpus} GPU と {required_cpus} CPU が必要です")
                return None
            
            # GPU を割り当て
            allocated_gpus = selected_server['available_gpus'][:required_gpus]
            selected_server['available_gpus'] = selected_server['available_gpus'][required_gpus:]
            
            # CPU を割り当て
            selected_server['available_cpus'] -= required_cpus
            
            # タスク情報を記録
            task_info = {
                'task_id': task_id,
                'allocated_gpus': allocated_gpus,
                'allocated_cpus': required_cpus,
                'start_time': datetime.now().isoformat()
            }
            selected_server['running_tasks'].append(task_info)
            
            # 状態を保存
            self._write_status(status)
            
            # 返却結果を構築
            result = {
                'server_id': selected_server['server_id'],
                'server_name': selected_server['server_name'],
                'gpu_ids': allocated_gpus,
                'cpu_count': required_cpus,
                'gpu_devices': ','.join(map(str, allocated_gpus)),
                'task_id': task_id
            }
            
            print(f"✓ リソース割り当て成功:")
            print(f"  サーバー: {result['server_name']}")
            print(f"  GPU ID: {result['gpu_ids']}")
            print(f"  CPU 数: {result['cpu_count']}")
            
            return result
            
        finally:
            # ロックを確実に解放
            self._release_lock(lock_file)
    
    def release_resources(self, task_id: str) -> bool:
        """
        指定されたタスクのリソースを解放
        
        Args:
            task_id: タスク一意識別子
        
        Returns:
            成功時 True、失敗時 False
        """
        # ロックを取得
        lock_file = self._acquire_lock()
        if lock_file is None:
            print("✗ ロック取得タイムアウト")
            return False
        
        try:
            # 現在の状態を読み取り
            status = self._read_status()
            
            # タスクを検索
            for server in status['servers']:
                for task in server['running_tasks']:
                    if task['task_id'] == task_id:
                        # タスクを見つけた、リソースを返却
                        
                        # GPU を返却
                        server['available_gpus'].extend(task['allocated_gpus'])
                        server['available_gpus'].sort()  # ソート維持
                        
                        # CPU を返却
                        server['available_cpus'] += task['allocated_cpus']
                        
                        # タスク記録を削除
                        server['running_tasks'].remove(task)
                        
                        # 状態を保存
                        self._write_status(status)
                        
                        print(f"✓ リソース解放完了: {task_id}")
                        return True
            
            # タスクが見つからない
            print(f"✗ タスクが見つかりません: {task_id}")
            return False
            
        finally:
            # ロックを確実に解放
            self._release_lock(lock_file)
    
    def get_resource_summary(self) -> Dict:
        """
        リソース使用状況のサマリーを取得
        
        Returns:
            リソースサマリー辞書
        """
        status = self._read_status()
        
        summary = {
            'total_servers': len(status['servers']),
            'servers': [],
            'total_available_gpus': 0,
            'total_gpus': 0,
            'total_available_cpus': 0,
            'total_cpus': 0,
            'total_running_tasks': 0
        }
        
        for server in status['servers']:
            available_gpus = len(server['available_gpus'])
            total_gpus = server['total_gpus']
            available_cpus = server['available_cpus']
            total_cpus = server['total_cpus']
            running_tasks = len(server['running_tasks'])
            
            gpu_utilization = (total_gpus - available_gpus) / total_gpus * 100
            cpu_utilization = (total_cpus - available_cpus) / total_cpus * 100
            
            server_summary = {
                'server_id': server['server_id'],
                'server_name': server['server_name'],
                'available_gpus': available_gpus,
                'total_gpus': total_gpus,
                'available_cpus': available_cpus,
                'total_cpus': total_cpus,
                'running_tasks': running_tasks,
                'gpu_utilization': f"{gpu_utilization:.1f}%",
                'cpu_utilization': f"{cpu_utilization:.1f}%"
            }
            summary['servers'].append(server_summary)
            
            # 累計統計
            summary['total_available_gpus'] += available_gpus
            summary['total_gpus'] += total_gpus
            summary['total_available_cpus'] += available_cpus
            summary['total_cpus'] += total_cpus
            summary['total_running_tasks'] += running_tasks
        
        return summary
    
    def get_detailed_status(self) -> Dict:
        """
        詳細なリソース状態を取得（すべてのタスク情報を含む）
        
        Returns:
            完全なリソース状態辞書
        """
        return self._read_status()
    
    def reset_resources(self) -> bool:
        """
        すべてのリソース状態をリセット（危険な操作！）
        
        警告：実行中のすべてのタスク記録がクリアされます
        
        Returns:
            成功時 True
        """
        lock_file = self._acquire_lock()
        if lock_file is None:
            print("✗ ロック取得タイムアウト")
            return False
        
        try:
            # 既存ファイルを削除
            if os.path.exists(self.RESOURCE_FILE):
                os.remove(self.RESOURCE_FILE)
            
            # 再初期化
            self._init_resource_file()
            
            print("✓ リソース状態がリセットされました")
            return True
            
        finally:
            self._release_lock(lock_file)


if __name__ == "__main__":
    # 簡単なテスト
    print("GPU リソースマネージャー v0.1 - テスト")
    print("=" * 60)
    
    manager = GPUResourceManagerV01()
    
    # テスト1: 初期状態を確認
    print("\nテスト1: 初期状態を確認")
    summary = manager.get_resource_summary()
    print(f"総 GPU 数: {summary['total_gpus']}")
    print(f"利用可能 GPU 数: {summary['total_available_gpus']}")
    
    # テスト2: リソースを割り当て
    print("\nテスト2: リソースを割り当て")
    result = manager.allocate_resources("test_task_001", 4, 32)
    if result:
        print(f"割り当て結果: {result}")
    
    # テスト3: 状態を確認
    print("\nテスト3: 割り当て後の状態を確認")
    summary = manager.get_resource_summary()
    print(f"利用可能 GPU 数: {summary['total_available_gpus']}")
    print(f"実行中タスク数: {summary['total_running_tasks']}")
    
    # テスト4: リソースを解放
    print("\nテスト4: リソースを解放")
    success = manager.release_resources("test_task_001")
    print(f"解放結果: {success}")
    
    # テスト5: 最終状態を確認
    print("\nテスト5: 最終状態を確認")
    summary = manager.get_resource_summary()
    print(f"利用可能 GPU 数: {summary['total_available_gpus']}")
    print(f"実行中タスク数: {summary['total_running_tasks']}")
    
    print("\n" + "=" * 60)
    print("テスト完了！")
