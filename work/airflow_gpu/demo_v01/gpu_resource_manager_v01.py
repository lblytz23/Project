"""
GPU资源管理器 v0.1 - 最小可行版本
功能：核心资源分配和释放算法

特点：
- 使用JSON文件存储资源状态
- 简单的文件锁机制（单机版）
- 首次适应算法
- 不依赖Airflow或其他复杂组件
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
import fcntl


class GPUResourceManagerV01:
    """
    GPU资源管理器 v0.1
    
    配置：
    - 4台服务器，每台8个GPU，64个CPU
    """
    
    # 系统配置
    TOTAL_SERVERS = 4
    GPUS_PER_SERVER = 8
    CPUS_PER_SERVER = 64
    
    # 文件路径
    RESOURCE_FILE = "resource_status.json"
    LOCK_FILE = ".resource.lock"
    
    def __init__(self):
        """初始化资源管理器"""
        self._init_resource_file()
    
    def _init_resource_file(self):
        """初始化资源状态文件"""
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
            print(f"✓ 资源状态文件已创建: {self.RESOURCE_FILE}")
    
    def _acquire_lock(self, timeout: int = 60) -> Optional[object]:
        """
        获取文件锁
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            文件对象（用于释放锁），失败返回None
        """
        lock_file = open(self.LOCK_FILE, 'w')
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 尝试获取排他锁（非阻塞）
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_file
            except IOError:
                # 锁被占用，等待
                time.sleep(0.1)
        
        # 超时
        lock_file.close()
        return None
    
    def _release_lock(self, lock_file: object):
        """释放文件锁"""
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except Exception as e:
                print(f"⚠ 释放锁时出错: {e}")
    
    def _read_status(self) -> Dict:
        """读取资源状态"""
        with open(self.RESOURCE_FILE, 'r') as f:
            return json.load(f)
    
    def _write_status(self, status: Dict):
        """写入资源状态"""
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
        分配GPU和CPU资源
        
        算法：首次适应算法（First Fit）
        
        Args:
            task_id: 任务唯一标识符
            required_gpus: 需要的GPU数量（2-8）
            required_cpus: 需要的CPU数量（1-64）
            prefer_server_id: 优先选择的服务器ID（可选）
        
        Returns:
            分配成功返回字典：
            {
                'server_id': int,
                'server_name': str,
                'gpu_ids': List[int],
                'cpu_count': int,
                'gpu_devices': str,  # 用于CUDA_VISIBLE_DEVICES
                'task_id': str
            }
            分配失败返回None
        
        Raises:
            ValueError: 参数不合法
        """
        # 参数验证
        if not (2 <= required_gpus <= 8):
            raise ValueError(f"GPU数量必须在2-8之间，当前值: {required_gpus}")
        
        if not (1 <= required_cpus <= self.CPUS_PER_SERVER):
            raise ValueError(f"CPU数量必须在1-{self.CPUS_PER_SERVER}之间，当前值: {required_cpus}")
        
        if prefer_server_id is not None:
            if not (0 <= prefer_server_id < self.TOTAL_SERVERS):
                raise ValueError(f"服务器ID必须在0-{self.TOTAL_SERVERS-1}之间")
        
        # 获取锁
        lock_file = self._acquire_lock()
        if lock_file is None:
            print("✗ 获取锁超时")
            return None
        
        try:
            # 读取当前状态
            status = self._read_status()
            selected_server = None
            
            # 如果指定了优先服务器，先检查
            if prefer_server_id is not None:
                server = status['servers'][prefer_server_id]
                if (len(server['available_gpus']) >= required_gpus and
                    server['available_cpus'] >= required_cpus):
                    selected_server = server
            
            # 如果优先服务器不可用或未指定，遍历所有服务器
            if selected_server is None:
                for server in status['servers']:
                    if (len(server['available_gpus']) >= required_gpus and
                        server['available_cpus'] >= required_cpus):
                        selected_server = server
                        break
            
            # 没有找到合适的服务器
            if selected_server is None:
                print(f"✗ 资源不足: 需要 {required_gpus} GPUs 和 {required_cpus} CPUs")
                return None
            
            # 分配GPU
            allocated_gpus = selected_server['available_gpus'][:required_gpus]
            selected_server['available_gpus'] = selected_server['available_gpus'][required_gpus:]
            
            # 分配CPU
            selected_server['available_cpus'] -= required_cpus
            
            # 记录任务信息
            task_info = {
                'task_id': task_id,
                'allocated_gpus': allocated_gpus,
                'allocated_cpus': required_cpus,
                'start_time': datetime.now().isoformat()
            }
            selected_server['running_tasks'].append(task_info)
            
            # 保存状态
            self._write_status(status)
            
            # 构建返回结果
            result = {
                'server_id': selected_server['server_id'],
                'server_name': selected_server['server_name'],
                'gpu_ids': allocated_gpus,
                'cpu_count': required_cpus,
                'gpu_devices': ','.join(map(str, allocated_gpus)),
                'task_id': task_id
            }
            
            print(f"✓ 资源分配成功:")
            print(f"  服务器: {result['server_name']}")
            print(f"  GPU IDs: {result['gpu_ids']}")
            print(f"  CPU数量: {result['cpu_count']}")
            
            return result
            
        finally:
            # 确保释放锁
            self._release_lock(lock_file)
    
    def release_resources(self, task_id: str) -> bool:
        """
        释放指定任务的资源
        
        Args:
            task_id: 任务唯一标识符
        
        Returns:
            成功返回True，失败返回False
        """
        # 获取锁
        lock_file = self._acquire_lock()
        if lock_file is None:
            print("✗ 获取锁超时")
            return False
        
        try:
            # 读取当前状态
            status = self._read_status()
            
            # 查找任务
            for server in status['servers']:
                for task in server['running_tasks']:
                    if task['task_id'] == task_id:
                        # 找到任务，归还资源
                        
                        # 归还GPU
                        server['available_gpus'].extend(task['allocated_gpus'])
                        server['available_gpus'].sort()  # 保持有序
                        
                        # 归还CPU
                        server['available_cpus'] += task['allocated_cpus']
                        
                        # 移除任务记录
                        server['running_tasks'].remove(task)
                        
                        # 保存状态
                        self._write_status(status)
                        
                        print(f"✓ 资源已释放: {task_id}")
                        return True
            
            # 未找到任务
            print(f"✗ 未找到任务: {task_id}")
            return False
            
        finally:
            # 确保释放锁
            self._release_lock(lock_file)
    
    def get_resource_summary(self) -> Dict:
        """
        获取资源使用摘要
        
        Returns:
            资源摘要字典
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
            
            # 累计统计
            summary['total_available_gpus'] += available_gpus
            summary['total_gpus'] += total_gpus
            summary['total_available_cpus'] += available_cpus
            summary['total_cpus'] += total_cpus
            summary['total_running_tasks'] += running_tasks
        
        return summary
    
    def get_detailed_status(self) -> Dict:
        """
        获取详细资源状态（包含所有任务信息）
        
        Returns:
            完整的资源状态字典
        """
        return self._read_status()
    
    def reset_resources(self) -> bool:
        """
        重置所有资源状态（危险操作！）
        
        警告：这将清除所有运行中任务的记录
        
        Returns:
            成功返回True
        """
        lock_file = self._acquire_lock()
        if lock_file is None:
            print("✗ 获取锁超时")
            return False
        
        try:
            # 删除现有文件
            if os.path.exists(self.RESOURCE_FILE):
                os.remove(self.RESOURCE_FILE)
            
            # 重新初始化
            self._init_resource_file()
            
            print("✓ 资源状态已重置")
            return True
            
        finally:
            self._release_lock(lock_file)


if __name__ == "__main__":
    # 简单的测试
    print("GPU资源管理器 v0.1 - 测试")
    print("=" * 60)
    
    manager = GPUResourceManagerV01()
    
    # 测试1: 查看初始状态
    print("\n测试1: 查看初始状态")
    summary = manager.get_resource_summary()
    print(f"总GPU数: {summary['total_gpus']}")
    print(f"可用GPU数: {summary['total_available_gpus']}")
    
    # 测试2: 分配资源
    print("\n测试2: 分配资源")
    result = manager.allocate_resources("test_task_001", 4, 32)
    if result:
        print(f"分配结果: {result}")
    
    # 测试3: 查看状态
    print("\n测试3: 查看分配后状态")
    summary = manager.get_resource_summary()
    print(f"可用GPU数: {summary['total_available_gpus']}")
    print(f"运行任务数: {summary['total_running_tasks']}")
    
    # 测试4: 释放资源
    print("\n测试4: 释放资源")
    success = manager.release_resources("test_task_001")
    print(f"释放结果: {success}")
    
    # 测试5: 查看最终状态
    print("\n测试5: 查看最终状态")
    summary = manager.get_resource_summary()
    print(f"可用GPU数: {summary['total_available_gpus']}")
    print(f"运行任务数: {summary['total_running_tasks']}")
    
    print("\n" + "=" * 60)
    print("测试完成！")

