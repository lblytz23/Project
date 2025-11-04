# GPU资源管理系统 - 详细设计文档

**文档版本**: v1.0  
**编制日期**: 2025-11-04  
**项目名称**: 基于Airflow的GPU资源管理系统  
**文档状态**: 正式发布

---

## 文档修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|----------|
| v1.0 | 2025-11-04 | 系统设计师 | 初始版本 |

---

## 目录

1. [引言](#1-引言)
2. [类设计](#2-类设计)
3. [算法设计](#3-算法设计)
4. [时序设计](#4-时序设计)
5. [状态机设计](#5-状态机设计)
6. [数据结构设计](#6-数据结构设计)
7. [接口详细设计](#7-接口详细设计)
8. [异常处理设计](#8-异常处理设计)
9. [并发控制设计](#9-并发控制设计)
10. [性能优化设计](#10-性能优化设计)

---

## 1. 引言

### 1.1 文档目的

本文档是GPU资源管理系统的详细设计文档，在基础设计的基础上，提供更加具体的实现细节，包括类的详细设计、算法实现、时序交互、异常处理等，为开发人员提供明确的实现指导。

### 1.2 适用范围

本文档适用于：
- 系统开发人员
- 代码审查人员
- 测试人员
- 技术文档维护人员

### 1.3 参考文档

- 《GPU资源管理系统 - 基础设计文档》
- 《GPU资源管理系统 - 需求规格说明书》
- Apache Airflow API文档

---

## 2. 类设计

### 2.1 核心类：GPUResourceManager

#### 2.1.1 类图

```
┌────────────────────────────────────────────────────────────┐
│                  GPUResourceManager                        │
├────────────────────────────────────────────────────────────┤
│ 类属性 (Class Attributes)                                  │
│ - TOTAL_SERVERS: int = 4                                   │
│ - GPUS_PER_SERVER: int = 8                                 │
│ - CPUS_PER_SERVER: int = 64                                │
│ - RESOURCE_VAR_NAME: str = "gpu_resource_status"           │
│ - LOCK_VAR_NAME: str = "gpu_resource_lock"                 │
├────────────────────────────────────────────────────────────┤
│ 实例方法 (Instance Methods)                                │
│ + __init__()                                               │
│ + allocate_resources(task_id, required_gpus,               │
│                      required_cpus, prefer_server_id)      │
│ + release_resources(task_id)                               │
│ + get_resource_summary()                                   │
│ + reset_resources()                                        │
├────────────────────────────────────────────────────────────┤
│ 私有方法 (Private Methods)                                 │
│ - _initialize_resources()                                  │
│ - _acquire_lock(timeout)                                   │
│ - _release_lock()                                          │
│ - _get_resource_status()                                   │
│ - _update_resource_status(status)                          │
└────────────────────────────────────────────────────────────┘
```

#### 2.1.2 类详细说明

**类名**: `GPUResourceManager`

**职责**:
1. 管理GPU和CPU资源的分配和释放
2. 维护资源状态的一致性
3. 提供资源查询接口
4. 实现分布式锁机制

**类属性**:

| 属性名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| TOTAL_SERVERS | int | 服务器总数 | 4 |
| GPUS_PER_SERVER | int | 每台服务器GPU数量 | 8 |
| CPUS_PER_SERVER | int | 每台服务器CPU数量 | 64 |
| RESOURCE_VAR_NAME | str | 资源状态变量名 | "gpu_resource_status" |
| LOCK_VAR_NAME | str | 锁变量名 | "gpu_resource_lock" |

**实例方法**:

##### 1. `__init__(self)`

**功能**: 构造函数，初始化资源管理器

**参数**: 无

**返回**: 无

**处理流程**:
```
1. 调用 _initialize_resources()
2. 如果 gpu_resource_status 不存在
   2.1 创建初始资源状态数据结构
   2.2 保存到 Airflow Variables
3. 记录初始化日志
```

**伪代码**:
```python
def __init__(self):
    try:
        status = Variable.get(RESOURCE_VAR_NAME)
        log("资源状态已存在")
    except KeyError:
        # 创建初始状态
        initial_status = {
            "servers": [
                {
                    "server_id": i,
                    "server_name": f"gpu-server-{i}",
                    "total_gpus": GPUS_PER_SERVER,
                    "available_gpus": list(range(GPUS_PER_SERVER)),
                    "total_cpus": CPUS_PER_SERVER,
                    "available_cpus": CPUS_PER_SERVER,
                    "running_tasks": []
                }
                for i in range(TOTAL_SERVERS)
            ],
            "last_updated": now()
        }
        Variable.set(RESOURCE_VAR_NAME, json.dumps(initial_status))
        log("资源状态已初始化")
```

##### 2. `allocate_resources(task_id, required_gpus, required_cpus, prefer_server_id=None)`

**功能**: 分配GPU和CPU资源

**参数**:
- `task_id` (str): 任务唯一标识符
- `required_gpus` (int): 需要的GPU数量，范围[2, 8]
- `required_cpus` (int): 需要的CPU数量，范围[1, 64]
- `prefer_server_id` (int, optional): 优先选择的服务器ID

**返回**: 
- `dict`: 分配成功，返回分配结果
- `None`: 分配失败

**异常**:
- `ValueError`: 参数不合法（GPU数量不在2-8范围，CPU数量超过64）

**处理流程**:
```
1. 参数验证
   1.1 检查 required_gpus 是否在 [2, 8] 范围
   1.2 检查 required_cpus 是否 <= CPUS_PER_SERVER
   
2. 获取分布式锁（超时60秒）
   2.1 如果获取失败，返回 None
   
3. 读取当前资源状态
   
4. 资源查找算法
   4.1 如果指定了 prefer_server_id
       4.1.1 检查该服务器是否满足需求
       4.1.2 如果满足，选择该服务器
   4.2 如果未指定或优先服务器不满足
       4.2.1 遍历所有服务器
       4.2.2 找到第一个满足条件的服务器
   4.3 如果没有找到，释放锁并返回 None
   
5. 资源分配
   5.1 从 available_gpus 列表中取出前 N 个
   5.2 从 available_cpus 中减去需要的数量
   5.3 创建任务记录
   5.4 添加到 running_tasks 列表
   
6. 更新资源状态
   6.1 设置 last_updated 时间戳
   6.2 保存到 Variables
   
7. 释放锁
   
8. 返回分配结果
```

**详细算法** (见 3.1 节)

##### 3. `release_resources(task_id)`

**功能**: 释放指定任务的资源

**参数**:
- `task_id` (str): 任务唯一标识符

**返回**: 
- `bool`: True表示成功，False表示失败

**处理流程**:
```
1. 获取分布式锁（超时60秒）
   1.1 如果获取失败，返回 False
   
2. 读取当前资源状态
   
3. 查找任务
   3.1 遍历所有服务器的 running_tasks
   3.2 找到 task_id 匹配的任务
   3.3 如果未找到，释放锁并返回 False
   
4. 资源归还
   4.1 将 allocated_gpus 加回 available_gpus
   4.2 将 allocated_cpus 加回 available_cpus
   4.3 对 available_gpus 进行排序
   4.4 从 running_tasks 中移除该任务
   
5. 更新资源状态
   5.1 设置 last_updated 时间戳
   5.2 保存到 Variables
   
6. 释放锁
   
7. 返回 True
```

**详细算法** (见 3.2 节)

##### 4. `get_resource_summary()`

**功能**: 获取资源使用摘要

**参数**: 无

**返回**: `dict` - 资源摘要信息

**处理流程**:
```
1. 读取当前资源状态（不需要锁）
   
2. 计算每个服务器的统计信息
   2.1 GPU利用率 = (total - available) / total * 100
   2.2 CPU利用率 = (total - available) / total * 100
   2.3 运行任务数 = len(running_tasks)
   
3. 构建摘要数据结构
   
4. 返回摘要
```

**返回数据结构**:
```json
{
  "total_servers": 4,
  "servers": [
    {
      "server_id": 0,
      "server_name": "gpu-server-0",
      "available_gpus": 4,
      "total_gpus": 8,
      "available_cpus": 32,
      "total_cpus": 64,
      "running_tasks": 2,
      "gpu_utilization": "50.0%",
      "cpu_utilization": "50.0%"
    }
  ]
}
```

##### 5. `reset_resources()`

**功能**: 重置所有资源状态（危险操作）

**参数**: 无

**返回**: `bool` - True表示成功

**处理流程**:
```
1. 获取分布式锁
2. 删除现有的 gpu_resource_status
3. 调用 _initialize_resources() 重新初始化
4. 释放锁
5. 返回 True
```

**私有方法**:

##### 6. `_acquire_lock(timeout=60)`

**功能**: 获取分布式锁

**实现原理**:
```
1. 记录开始时间
2. 循环（最多 timeout 秒）
   2.1 读取 gpu_resource_lock 的值
   2.2 如果值为 "0"（未锁定）
       2.2.1 设置值为 "1"（锁定）
       2.2.2 返回 True
   2.3 否则，等待 0.1 秒
3. 超时后返回 False
```

**改进方案**（生产环境）:
```python
# 使用 Redis 实现真正的分布式锁
import redis
from redis.lock import Lock

self.redis_client = redis.Redis(host='localhost', port=6379)
self.lock = Lock(self.redis_client, "gpu_resource_lock", timeout=60)
return self.lock.acquire(blocking=True, timeout=60)
```

---

## 3. 算法设计

### 3.1 资源分配算法

#### 3.1.1 算法名称
首次适应算法（First Fit Algorithm）

#### 3.1.2 算法描述
遍历所有服务器，找到第一个满足GPU和CPU需求的服务器进行分配。

#### 3.1.3 算法流程图

```
开始
  ↓
参数验证
  ├→ GPU ∈ [2,8]? ──N→ 抛出 ValueError
  └→ Y
  ↓
CPU ≤ 64? ──N→ 抛出 ValueError
  └→ Y
  ↓
获取锁(超时60s)
  ├→ 成功? ──N→ 返回 None
  └→ Y
  ↓
读取资源状态
  ↓
指定了 prefer_server_id? ──Y→ 检查优先服务器
  ├→ N                         ├→ 满足? ──Y→ 选择该服务器
  │                            └→ N ↓
  ↓                                 ↓
遍历所有服务器 ←──────────────────┘
  ↓
当前服务器 i
  ↓
available_gpus ≥ required_gpus?
  ├→ N → i++, 继续遍历
  └→ Y
  ↓
available_cpus ≥ required_cpus?
  ├→ N → i++, 继续遍历
  └→ Y
  ↓
选择服务器 i
  ↓
从 available_gpus 取出前 N 个
  ↓
从 available_cpus 减去 M
  ↓
创建任务记录
  ↓
添加到 running_tasks
  ↓
更新资源状态
  ↓
释放锁
  ↓
返回分配结果
  ↓
结束
```

#### 3.1.4 算法伪代码

```python
Algorithm: allocate_resources
Input: task_id, required_gpus, required_cpus, prefer_server_id
Output: allocation_result | None

1. # 参数验证
2. if required_gpus < 2 or required_gpus > 8:
3.     raise ValueError("GPU数量必须在2-8之间")
4. if required_cpus > CPUS_PER_SERVER:
5.     raise ValueError("CPU数量超过服务器容量")

6. # 获取锁
7. if not _acquire_lock(timeout=60):
8.     log_error("获取锁超时")
9.     return None

10. try:
11.     # 读取资源状态
12.     status = _get_resource_status()
13.     selected_server = None
14.     
15.     # 优先服务器检查
16.     if prefer_server_id is not None:
17.         server = status["servers"][prefer_server_id]
18.         if len(server["available_gpus"]) >= required_gpus and \
19.            server["available_cpus"] >= required_cpus:
20.             selected_server = server
21.     
22.     # 遍历所有服务器
23.     if selected_server is None:
24.         for server in status["servers"]:
25.             if len(server["available_gpus"]) >= required_gpus and \
26.                server["available_cpus"] >= required_cpus:
27.                 selected_server = server
28.                 break
29.     
30.     # 没有找到合适的服务器
31.     if selected_server is None:
32.         log_warning("没有足够的资源")
33.         return None
34.     
35.     # 分配GPU
36.     allocated_gpus = selected_server["available_gpus"][:required_gpus]
37.     selected_server["available_gpus"] = \
38.         selected_server["available_gpus"][required_gpus:]
39.     
40.     # 分配CPU
41.     selected_server["available_cpus"] -= required_cpus
42.     
43.     # 创建任务记录
44.     task_info = {
45.         "task_id": task_id,
46.         "allocated_gpus": allocated_gpus,
47.         "allocated_cpus": required_cpus,
48.         "start_time": current_timestamp()
49.     }
50.     selected_server["running_tasks"].append(task_info)
51.     
52.     # 更新状态
53.     _update_resource_status(status)
54.     
55.     # 构建返回结果
56.     result = {
57.         "server_id": selected_server["server_id"],
58.         "server_name": selected_server["server_name"],
59.         "gpu_ids": allocated_gpus,
60.         "cpu_count": required_cpus,
61.         "gpu_devices": ",".join(map(str, allocated_gpus)),
62.         "task_id": task_id
63.     }
64.     
65.     log_info(f"资源分配成功: {result}")
66.     return result
67.     
68. finally:
69.     # 释放锁
70.     _release_lock()
```

#### 3.1.5 算法复杂度分析

**时间复杂度**:
- 最好情况: O(1) - 第一个服务器即满足需求
- 最坏情况: O(N) - 遍历所有N个服务器
- 平均情况: O(N/2)

其中 N = TOTAL_SERVERS = 4，因此实际性能非常好。

**空间复杂度**: O(1) - 只使用固定大小的临时变量

### 3.2 资源释放算法

#### 3.2.1 算法描述
根据task_id查找对应的资源分配记录，归还GPU和CPU资源。

#### 3.2.2 算法伪代码

```python
Algorithm: release_resources
Input: task_id
Output: success (bool)

1. # 获取锁
2. if not _acquire_lock(timeout=60):
3.     log_error("获取锁超时")
4.     return False

5. try:
6.     # 读取资源状态
7.     status = _get_resource_status()
8.     
9.     # 查找任务
10.     for server in status["servers"]:
11.         for task in server["running_tasks"]:
12.             if task["task_id"] == task_id:
13.                 # 找到任务，归还资源
14.                 
15.                 # 归还GPU
16.                 server["available_gpus"].extend(task["allocated_gpus"])
17.                 server["available_gpus"].sort()  # 保持有序
18.                 
19.                 # 归还CPU
20.                 server["available_cpus"] += task["allocated_cpus"]
21.                 
22.                 # 移除任务记录
23.                 server["running_tasks"].remove(task)
24.                 
25.                 # 更新状态
26.                 _update_resource_status(status)
27.                 
28.                 log_info(f"资源已释放: {task_id}")
29.                 return True
30.     
31.     # 未找到任务
32.     log_warning(f"未找到任务: {task_id}")
33.     return False
34.     
35. finally:
36.     # 释放锁
37.     _release_lock()
```

#### 3.2.3 算法复杂度分析

**时间复杂度**:
- 最好情况: O(1) - 任务在第一个服务器的第一个位置
- 最坏情况: O(N×M) - 需要遍历所有服务器和所有任务
  - N = 服务器数量 (4)
  - M = 平均每服务器运行任务数

**空间复杂度**: O(1)

### 3.3 服务器选择策略

#### 3.3.1 当前策略：首次适应（First Fit）

**优点**:
- ✅ 实现简单
- ✅ 性能好（早期匹配）
- ✅ 适合大多数场景

**缺点**:
- ❌ 可能导致资源碎片
- ❌ 后面的服务器可能一直空闲

#### 3.3.2 可选策略

**1. 最佳适应（Best Fit）**
```python
# 选择剩余资源最少但能满足需求的服务器
best_server = None
min_remaining = float('inf')

for server in servers:
    if can_allocate(server, required):
        remaining = server.available_gpus - required_gpus
        if remaining < min_remaining:
            min_remaining = remaining
            best_server = server
```

**优点**: 减少资源浪费  
**缺点**: 可能增加碎片

**2. 轮询（Round Robin）**
```python
# 轮流选择服务器
last_used_server = get_last_used()
start_from = (last_used_server + 1) % TOTAL_SERVERS

for i in range(TOTAL_SERVERS):
    server_id = (start_from + i) % TOTAL_SERVERS
    if can_allocate(servers[server_id], required):
        return servers[server_id]
```

**优点**: 负载均衡  
**缺点**: 可能跳过更优选择

**3. 负载最低优先（Least Loaded First）**
```python
# 选择当前负载最低的服务器
servers_sorted = sorted(servers, 
                       key=lambda s: len(s.running_tasks))

for server in servers_sorted:
    if can_allocate(server, required):
        return server
```

**优点**: 均匀分配负载  
**缺点**: 排序开销

---

## 4. 时序设计

### 4.1 资源分配时序图

```
用户  Airflow  DAG      GPUResourceManager  Variables  Server
 │      │      │              │               │         │
 │提交配置│      │              │               │         │
 ├────→│      │              │               │         │
 │      │触发DAG│              │               │         │
 │      ├────→│              │               │         │
 │      │      │ allocate()   │               │         │
 │      │      ├────────────→│               │         │
 │      │      │              │ acquire_lock()│         │
 │      │      │              ├─────────────→│         │
 │      │      │              │     "1"       │         │
 │      │      │              │←─────────────┤         │
 │      │      │              │ get_status()  │         │
 │      │      │              ├─────────────→│         │
 │      │      │              │   JSON data   │         │
 │      │      │              │←─────────────┤         │
 │      │      │              │               │         │
 │      │      │              │ [查找合适服务器]          │
 │      │      │              │ [分配GPU和CPU]           │
 │      │      │              │               │         │
 │      │      │              │ update_status()│        │
 │      │      │              ├─────────────→│         │
 │      │      │              │     OK        │         │
 │      │      │              │←─────────────┤         │
 │      │      │              │ release_lock()│         │
 │      │      │              ├─────────────→│         │
 │      │      │              │     "0"       │         │
 │      │      │              │←─────────────┤         │
 │      │      │  allocation  │               │         │
 │      │      │←────────────┤               │         │
 │      │      │              │               │         │
 │      │      │ build_docker_cmd()            │         │
 │      │      ├──────────────────────────────┼───────→│
 │      │      │                               │   docker run
 │      │      │                               │         │
 │      │      │              [训练执行中...]          │
 │      │      │                               │         │
 │      │      │ release()    │               │         │
 │      │      ├────────────→│               │         │
 │      │      │              │ acquire_lock()│         │
 │      │      │              ├─────────────→│         │
 │      │      │              │ [归还资源]    │         │
 │      │      │              │ update_status()│        │
 │      │      │              ├─────────────→│         │
 │      │      │              │ release_lock()│         │
 │      │      │              ├─────────────→│         │
 │      │      │     True     │               │         │
 │      │      │←────────────┤               │         │
```

### 4.2 并发分配时序图

```
用户A  用户B  GPUResourceManager  Variables
 │      │           │               │
 │ req1 │           │               │
 ├──────┼─────────→│               │
 │      │           │ acquire_lock()│
 │      │           ├─────────────→│
 │      │ req2      │   成功(用户A) │
 │      ├─────────→│←─────────────┤
 │      │           │ [处理请求A]   │
 │      │           │ acquire_lock()│  (被阻塞)
 │      │           │←─────────────┤
 │      │           │ [等待...]     │
 │      │           │               │
 │      │           │ [A完成分配]   │
 │      │           │ update()      │
 │      │           ├─────────────→│
 │      │           │ release_lock()│
 │      │           ├─────────────→│
 │      │           │   "0"         │
 │      │           │←─────────────┤
 │←─────┤           │               │  (A获得结果)
 │      │           │               │
 │      │           │ acquire_lock()│  (B获得锁)
 │      │           ├─────────────→│
 │      │           │   成功(用户B) │
 │      │           │←─────────────┤
 │      │           │ [处理请求B]   │
 │      │           │ update()      │
 │      │           ├─────────────→│
 │      │           │ release_lock()│
 │      │           ├─────────────→│
 │      │←─────────┤               │  (B获得结果)
```

### 4.3 资源释放时序图

```
DAG    GPUResourceManager  Variables  Server
 │           │               │         │
 │ release() │               │         │
 ├─────────→│               │         │
 │           │ acquire_lock()│         │
 │           ├─────────────→│         │
 │           │     "1"       │         │
 │           │←─────────────┤         │
 │           │ get_status()  │         │
 │           ├─────────────→│         │
 │           │   JSON data   │         │
 │           │←─────────────┤         │
 │           │               │         │
 │           │ [查找task_id] │         │
 │           │ [归还GPU]     │         │
 │           │ [归还CPU]     │         │
 │           │ [移除任务记录]│         │
 │           │               │         │
 │           │ update_status()│        │
 │           ├─────────────→│         │
 │           │     OK        │         │
 │           │←─────────────┤         │
 │           │ release_lock()│         │
 │           ├─────────────→│         │
 │           │     "0"       │         │
 │           │←─────────────┤         │
 │    True   │               │         │
 │←─────────┤               │         │
```

---

## 5. 状态机设计

### 5.1 任务状态机

```
                    ┌──────────┐
                    │  待提交   │
                    │ PENDING  │
                    └────┬─────┘
                         │ 用户提交配置
                         ↓
                    ┌──────────┐
                    │  排队中   │
                    │ QUEUED   │
                    └────┬─────┘
                         │ Airflow调度
                         ↓
                    ┌──────────┐
                    │ 分配资源中 │
                    │ALLOCATING│
                    └────┬─────┘
                         │
           ┌─────────────┼─────────────┐
           │ 成功         │             │ 失败
           ↓             ↓             ↓
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │ 运行中   │  │资源不足   │  │  错误    │
     │ RUNNING  │  │ WAITING  │  │  ERROR   │
     └────┬─────┘  └────┬─────┘  └────┬─────┘
          │             │ 重试         │
          │             └──────────────┤
          │                           │
          ↓                           ↓
     ┌──────────┐              ┌──────────┐
     │  完成    │              │  失败    │
     │ SUCCESS  │              │  FAILED  │
     └────┬─────┘              └────┬─────┘
          │                         │
          └──────────┬──────────────┘
                     │ 释放资源
                     ↓
                ┌──────────┐
                │ 已清理   │
                │ CLEANED  │
                └──────────┘
```

### 5.2 服务器状态

```
服务器状态 = {
    "IDLE":     所有GPU和CPU都可用,
    "PARTIAL":  部分GPU或CPU被占用,
    "FULL":     所有GPU被占用,
    "ERROR":    服务器异常
}

状态转换：

IDLE ──[分配资源]──→ PARTIAL
                       ↓
PARTIAL ──[继续分配]──→ FULL
  ↑                     │
  │                     │
  └────[释放资源]←──────┘
  
  
任何状态 ──[检测异常]──→ ERROR
```

### 5.3 锁状态机

```
        ┌──────────┐
  ┌────→│  未锁定   │←────┐
  │     │ UNLOCKED │     │
  │     │   ("0")  │     │
  │     └────┬─────┘     │
  │          │           │
  │   acquire_lock()     │
  │          │      release_lock()
  │          ↓           │
  │     ┌──────────┐     │
  └─────│   已锁定  ├─────┘
  超时   │  LOCKED  │  完成操作
        │   ("1")  │
        └──────────┘
```

---

## 6. 数据结构设计

### 6.1 核心数据结构

#### 6.1.1 ResourceStatus（资源状态）

```python
ResourceStatus = {
    "servers": List[ServerInfo],
    "last_updated": str  # ISO 8601格式
}

ServerInfo = {
    "server_id": int,           # 0-3
    "server_name": str,         # "gpu-server-{id}"
    "total_gpus": int,          # 8
    "available_gpus": List[int], # [0,1,2,3,4,5,6,7]
    "total_cpus": int,          # 64
    "available_cpus": int,      # 0-64
    "running_tasks": List[TaskInfo]
}

TaskInfo = {
    "task_id": str,
    "allocated_gpus": List[int],
    "allocated_cpus": int,
    "start_time": str  # ISO 8601格式
}
```

#### 6.1.2 AllocationResult（分配结果）

```python
AllocationResult = {
    "server_id": int,
    "server_name": str,
    "gpu_ids": List[int],
    "cpu_count": int,
    "gpu_devices": str,  # "0,1,2,3" 用于CUDA_VISIBLE_DEVICES
    "task_id": str
}
```

#### 6.1.3 ResourceSummary（资源摘要）

```python
ResourceSummary = {
    "total_servers": int,
    "servers": List[ServerSummary]
}

ServerSummary = {
    "server_id": int,
    "server_name": str,
    "available_gpus": int,
    "total_gpus": int,
    "available_cpus": int,
    "total_cpus": int,
    "running_tasks": int,
    "gpu_utilization": str,  # "50.0%"
    "cpu_utilization": str   # "50.0%"
}
```

### 6.2 数据结构设计原则

#### 6.2.1 原子性
- ✅ 资源状态更新必须原子进行
- ✅ 使用分布式锁保证一致性

#### 6.2.2 可序列化
- ✅ 所有数据结构可序列化为JSON
- ✅ 便于存储和传输

#### 6.2.3 可扩展性
- ✅ 预留扩展字段空间
- ✅ 支持增加新的服务器类型

---

## 7. 接口详细设计

### 7.1 Python接口规范

#### 7.1.1 接口：allocate_resources

```python
def allocate_resources(
    self,
    task_id: str,
    required_gpus: int,
    required_cpus: int,
    prefer_server_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    分配GPU和CPU资源
    
    Args:
        task_id: 任务唯一标识符，建议格式：{dag_run_id}_{task_id}
        required_gpus: 需要的GPU数量，范围[2, 8]
        required_cpus: 需要的CPU数量，范围[1, 64]
        prefer_server_id: 可选，优先选择的服务器ID [0, 3]
    
    Returns:
        成功时返回 AllocationResult 字典：
        {
            "server_id": int,
            "server_name": str,
            "gpu_ids": List[int],
            "cpu_count": int,
            "gpu_devices": str,
            "task_id": str
        }
        
        失败时返回 None
    
    Raises:
        ValueError: 参数不合法
            - required_gpus 不在 [2, 8] 范围
            - required_cpus > 64
            - prefer_server_id 不在 [0, 3] 范围
    
    Side Effects:
        - 修改 Airflow Variables 中的 gpu_resource_status
        - 记录INFO级别日志
    
    Thread Safety:
        线程安全，使用分布式锁保护
    
    Example:
        >>> manager = GPUResourceManager()
        >>> result = manager.allocate_resources(
        ...     task_id="run_001",
        ...     required_gpus=4,
        ...     required_cpus=32
        ... )
        >>> if result:
        ...     print(f"分配到服务器: {result['server_name']}")
        ...     print(f"GPU: {result['gpu_ids']}")
        ... else:
        ...     print("资源不足")
    """
```

### 7.2 REST API接口规范

#### 7.2.1 接口：POST /api/allocate

**基本信息**:
- URL: `/api/allocate`
- 方法: `POST`
- 内容类型: `application/json`

**请求体**:
```json
{
  "task_id": "string",      // 必填，任务ID
  "required_gpus": integer,  // 必填，范围[2, 8]
  "required_cpus": integer   // 必填，范围[1, 64]
}
```

**响应**:

成功（200 OK）:
```json
{
  "server_id": 0,
  "server_name": "gpu-server-0",
  "gpu_ids": [0, 1, 2, 3],
  "cpu_count": 32,
  "gpu_devices": "0,1,2,3",
  "task_id": "test_001"
}
```

失败（400 Bad Request）:
```json
{
  "error": "Missing required parameters"
}
```

失败（503 Service Unavailable）:
```json
{
  "error": "Resource allocation failed"
}
```

**示例**:
```bash
curl -X POST http://localhost:5000/api/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test_001",
    "required_gpus": 4,
    "required_cpus": 32
  }'
```

---

## 8. 异常处理设计

### 8.1 异常分类

#### 8.1.1 参数异常
```python
class: ValueError

触发条件:
- required_gpus < 2 or required_gpus > 8
- required_cpus > 64
- prefer_server_id < 0 or prefer_server_id >= TOTAL_SERVERS

处理策略:
- 立即抛出异常
- 记录ERROR日志
- 不进行任何资源操作
```

#### 8.1.2 资源不足异常
```python
情况: 所有服务器都无法满足需求

处理策略:
- 返回 None（不抛出异常）
- 记录WARNING日志
- 上层调用者决定重试或失败
```

#### 8.1.3 锁获取超时异常
```python
情况: 60秒内无法获取分布式锁

处理策略:
- 返回 None
- 记录ERROR日志
- 建议检查是否有死锁或长时间占用锁的任务
```

#### 8.1.4 Variables访问异常
```python
class: AirflowException

触发条件:
- Airflow Variables 服务不可用
- 网络问题
- 数据库问题

处理策略:
- 捕获异常
- 记录ERROR日志
- 向上层抛出异常
- 触发Airflow重试机制
```

### 8.2 异常处理流程

```python
try:
    # 1. 参数验证
    if not validate_parameters(required_gpus, required_cpus):
        raise ValueError("参数不合法")
    
    # 2. 获取锁
    if not _acquire_lock(timeout=60):
        log.error("获取锁超时")
        return None
    
    try:
        # 3. 读取资源状态
        status = _get_resource_status()
        
        # 4. 执行分配逻辑
        result = perform_allocation(status, required_gpus, required_cpus)
        
        if result is None:
            log.warning("资源不足")
            return None
        
        # 5. 更新状态
        _update_resource_status(status)
        
        # 6. 返回结果
        return result
        
    except AirflowException as e:
        log.error(f"Airflow异常: {e}")
        raise  # 重新抛出，触发重试
        
    except Exception as e:
        log.error(f"未知异常: {e}")
        raise
        
    finally:
        # 7. 确保释放锁
        _release_lock()
        
except ValueError as e:
    log.error(f"参数错误: {e}")
    raise

except Exception as e:
    log.error(f"系统错误: {e}")
    raise
```

### 8.3 重试策略

#### Airflow任务重试配置
```python
default_args = {
    'retries': 2,              # 重试2次
    'retry_delay': timedelta(minutes=5),  # 间隔5分钟
    'retry_exponential_backoff': True,    # 指数退避
    'max_retry_delay': timedelta(minutes=30)
}
```

#### 资源分配重试逻辑
```
第1次尝试 ──失败→ 等待5分钟 ──→ 第2次尝试
                                      │
                              失败 ↓
                          等待10分钟
                              │
                              ↓
                          第3次尝试
                              │
                      失败 ↓   ↓ 成功
                    任务失败   返回结果
```

---

## 9. 并发控制设计

### 9.1 分布式锁机制

#### 9.1.1 锁的粒度
- **全局锁**: 保护整个资源状态
- **粒度**: 粗粒度（覆盖所有服务器）
- **原因**: 资源分配需要考虑所有服务器，细粒度锁会增加复杂度

#### 9.1.2 锁的实现

**简单实现（适用于小规模）**:
```python
def _acquire_lock(self, timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            lock_status = Variable.get(self.LOCK_VAR_NAME, default_var="0")
            if lock_status == "0":
                Variable.set(self.LOCK_VAR_NAME, "1")
                return True
        except Exception as e:
            logger.warning(f"获取锁时出错: {e}")
        time.sleep(0.1)
    return False

def _release_lock(self):
    try:
        Variable.set(self.LOCK_VAR_NAME, "0")
    except Exception as e:
        logger.error(f"释放锁时出错: {e}")
```

**生产环境实现（使用Redis）**:
```python
import redis
from redis.lock import Lock

class GPUResourceManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        self._initialize_resources()
    
    def _acquire_lock(self, timeout=60):
        self.lock = Lock(
            self.redis_client,
            name="gpu_resource_lock",
            timeout=timeout,
            blocking_timeout=timeout,
            thread_local=False
        )
        try:
            acquired = self.lock.acquire(blocking=True)
            if acquired:
                logger.info("获取锁成功")
            return acquired
        except redis.exceptions.LockError as e:
            logger.error(f"获取锁失败: {e}")
            return False
    
    def _release_lock(self):
        try:
            if hasattr(self, 'lock'):
                self.lock.release()
                logger.info("释放锁成功")
        except redis.exceptions.LockError as e:
            logger.warning(f"释放锁失败（可能已超时）: {e}")
```

### 9.2 并发场景分析

#### 场景1：两个任务同时请求资源

```
时间线：
T0: 任务A请求4 GPUs
T0: 任务B请求4 GPUs  (几乎同时)

流程：
T0:   A尝试获取锁  ────→ 成功
T0:   B尝试获取锁  ────→ 等待（被阻塞）

T1:   A读取资源状态
T2:   A执行分配算法
T3:   A更新资源状态
T4:   A释放锁

T5:   B获取锁  ────→ 成功（A已释放）
T6:   B读取资源状态（已包含A的分配）
T7:   B执行分配算法
T8:   B更新资源状态
T9:   B释放锁

结果：A和B都成功分配，不会冲突
```

#### 场景2：100个任务同时请求

```
锁队列：
[Task1] → [Task2] → [Task3] → ... → [Task100]
  ↑获取
  执行
  释放 ↓
       [Task2] → [Task3] → ... → [Task100]
         ↑获取
         
流程：
1. 任务按到达顺序排队
2. 依次获取锁、执行、释放
3. 平均每个任务耗时：100-500ms
4. 100个任务总耗时：10-50秒
```

### 9.3 死锁预防

#### 死锁条件分析

**死锁的四个必要条件**:
1. 互斥：锁是互斥资源 ✓
2. 持有并等待：持有锁并等待其他资源 ✗
3. 不可抢占：锁不能被抢占 ✓
4. 循环等待：多个任务循环等待 ✗

**结论**: 系统中只有一个全局锁，不存在循环等待，不会发生死锁。

#### 锁超时机制

```python
# 设置锁超时
LOCK_TIMEOUT = 60  # 60秒

# 超时后自动释放
if time.time() - lock_acquire_time > LOCK_TIMEOUT:
    _force_release_lock()
    log.error("锁超时，强制释放")
```

---

## 10. 性能优化设计

### 10.1 优化目标

| 性能指标 | 当前值 | 目标值 | 优化空间 |
|----------|--------|--------|----------|
| 资源分配延迟 | ~200ms | <100ms | 50% |
| 并发吞吐量 | 50 req/min | 200 req/min | 4x |
| 锁等待时间 | ~5s (高并发) | <1s | 80% |
| API响应时间 | ~50ms | <30ms | 40% |

### 10.2 优化策略

#### 10.2.1 减少锁持有时间

**当前实现**:
```python
acquire_lock()
  ↓
read_status()      # 10ms
  ↓
find_server()      # 5ms
  ↓
allocate()         # 5ms
  ↓
update_status()    # 10ms
  ↓
release_lock()

总锁持有时间：30ms
```

**优化后**:
```python
# 预读取（不加锁）
status = read_status_cached()  # 从缓存读取
find_server()                   # 在锁外完成

acquire_lock()
  ↓
read_status()      # 验证状态
  ↓
allocate()         # 仅分配操作
  ↓
update_status()
  ↓
release_lock()

总锁持有时间：15ms（减少50%）
```

#### 10.2.2 使用缓存

```python
from functools import lru_cache
from datetime import datetime, timedelta

class GPUResourceManager:
    def __init__(self):
        self._cache = {}
        self._cache_ttl = timedelta(seconds=1)
    
    def _get_resource_status_cached(self):
        """带缓存的资源状态读取"""
        now = datetime.now()
        
        if 'status' in self._cache:
            cache_time = self._cache['time']
            if now - cache_time < self._cache_ttl:
                return self._cache['status']
        
        # 缓存过期，重新读取
        status = self._get_resource_status()
        self._cache = {
            'status': status,
            'time': now
        }
        return status
```

#### 10.2.3 批量操作

```python
def allocate_batch(self, requests: List[AllocationRequest]) -> List[AllocationResult]:
    """批量分配资源（减少锁获取次数）"""
    
    if not self._acquire_lock(timeout=60):
        return [None] * len(requests)
    
    try:
        status = self._get_resource_status()
        results = []
        
        for req in requests:
            result = self._allocate_single(status, req)
            results.append(result)
        
        self._update_resource_status(status)
        return results
        
    finally:
        self._release_lock()
```

#### 10.2.4 异步化

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncGPUResourceManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.manager = GPUResourceManager()
    
    async def allocate_resources_async(self, task_id, required_gpus, required_cpus):
        """异步资源分配"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self.manager.allocate_resources,
            task_id, required_gpus, required_cpus
        )
        return result
```

### 10.3 性能监控

#### 10.3.1 关键指标

```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # 记录性能指标
            logger.info(f"{func.__name__} 耗时: {duration*1000:.2f}ms")
            
            # 发送到监控系统
            send_metric(f"{func.__name__}.duration", duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} 失败, 耗时: {duration*1000:.2f}ms")
            send_metric(f"{func.__name__}.error", 1)
            raise
    
    return wrapper

class GPUResourceManager:
    @monitor_performance
    def allocate_resources(self, ...):
        # 实现...
        pass
```

#### 10.3.2 性能告警

```python
# 设置告警阈值
ALERT_THRESHOLDS = {
    'allocation_duration': 500,  # ms
    'lock_wait_time': 5000,      # ms
    'concurrent_requests': 50     # 并发数
}

def check_and_alert(metric_name, value):
    threshold = ALERT_THRESHOLDS.get(metric_name)
    if threshold and value > threshold:
        send_alert(f"{metric_name} 超过阈值: {value} > {threshold}")
```

---

## 附录

### A. 数据库表设计（扩展方案）

如果未来需要将资源状态从Variables迁移到数据库：

```sql
-- 服务器表
CREATE TABLE gpu_servers (
    server_id INT PRIMARY KEY,
    server_name VARCHAR(50) NOT NULL,
    total_gpus INT NOT NULL DEFAULT 8,
    total_cpus INT NOT NULL DEFAULT 64,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- GPU资源表
CREATE TABLE gpu_resources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    server_id INT NOT NULL,
    gpu_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'AVAILABLE',  -- AVAILABLE, ALLOCATED
    allocated_to VARCHAR(100),  -- task_id
    allocated_at TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES gpu_servers(server_id),
    UNIQUE KEY (server_id, gpu_id)
);

-- CPU资源表
CREATE TABLE cpu_resources (
    server_id INT PRIMARY KEY,
    available_cpus INT NOT NULL DEFAULT 64,
    allocated_cpus INT NOT NULL DEFAULT 0,
    FOREIGN KEY (server_id) REFERENCES gpu_servers(server_id)
);

-- 任务分配记录表
CREATE TABLE task_allocations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL UNIQUE,
    server_id INT NOT NULL,
    allocated_gpus JSON,  -- [0,1,2,3]
    allocated_cpus INT,
    status VARCHAR(20) DEFAULT 'RUNNING',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES gpu_servers(server_id),
    INDEX idx_task_id (task_id),
    INDEX idx_status (status)
);
```

### B. API完整文档

详见接口设计部分（第7节）

### C. 测试用例设计

```python
class TestGPUResourceManager(unittest.TestCase):
    def setUp(self):
        self.manager = GPUResourceManager()
        self.manager.reset_resources()
    
    def test_allocate_success(self):
        """测试：成功分配资源"""
        result = self.manager.allocate_resources(
            task_id="test_001",
            required_gpus=4,
            required_cpus=32
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result['gpu_ids']), 4)
        self.assertEqual(result['cpu_count'], 32)
    
    def test_allocate_invalid_params(self):
        """测试：无效参数"""
        with self.assertRaises(ValueError):
            self.manager.allocate_resources(
                task_id="test_002",
                required_gpus=1,  # 无效：小于2
                required_cpus=32
            )
    
    def test_allocate_insufficient_resources(self):
        """测试：资源不足"""
        # 先分配满所有服务器
        for i in range(16):  # 4服务器 x 4次
            result = self.manager.allocate_resources(
                task_id=f"test_{i:03d}",
                required_gpus=2,
                required_cpus=16
            )
            self.assertIsNotNone(result)
        
        # 此时应该无法再分配
        result = self.manager.allocate_resources(
            task_id="test_fail",
            required_gpus=2,
            required_cpus=16
        )
        self.assertIsNone(result)
    
    def test_release_success(self):
        """测试：成功释放资源"""
        # 分配
        result = self.manager.allocate_resources(
            task_id="test_release",
            required_gpus=4,
            required_cpus=32
        )
        self.assertIsNotNone(result)
        
        # 释放
        success = self.manager.release_resources("test_release")
        self.assertTrue(success)
    
    def test_concurrent_allocation(self):
        """测试：并发分配"""
        import threading
        
        results = []
        
        def allocate():
            result = self.manager.allocate_resources(
                task_id=f"concurrent_{threading.get_ident()}",
                required_gpus=2,
                required_cpus=16
            )
            results.append(result)
        
        threads = [threading.Thread(target=allocate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # 所有分配都应该成功（足够的资源）
        self.assertEqual(sum(1 for r in results if r is not None), 10)
```

---

**文档结束**

*本文档为GPU资源管理系统的详细设计文档，包含了类设计、算法、时序、状态机、数据结构、接口、异常处理、并发控制和性能优化等方面的详细说明。*

