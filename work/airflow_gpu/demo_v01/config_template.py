"""
GPU资源管理器配置模板
复制此文件为 config.py 并根据实际情况修改
"""

# ============================================================
# 基础配置 - 必须修改
# ============================================================

# 服务器配置
TOTAL_SERVERS = 4        # 你有几台GPU服务器？
GPUS_PER_SERVER = 8      # 每台服务器有几个GPU？
CPUS_PER_SERVER = 64     # 每台服务器有几个CPU？

# 示例：
# - 2台服务器，每台4GPU，32CPU：TOTAL_SERVERS=2, GPUS_PER_SERVER=4, CPUS_PER_SERVER=32
# - 8台服务器，每台8GPU，128CPU：TOTAL_SERVERS=8, GPUS_PER_SERVER=8, CPUS_PER_SERVER=128


# ============================================================
# 文件路径配置 - 可选修改
# ============================================================

import os

# 方案1：使用当前目录（默认，适合测试）
DATA_DIR = "."
RESOURCE_FILE = "resource_status.json"
LOCK_FILE = ".resource.lock"

# 方案2：使用固定目录（推荐生产环境）
# DATA_DIR = "/var/lib/gpu_manager"           # Linux
# DATA_DIR = "C:\\ProgramData\\GPUManager"    # Windows
# RESOURCE_FILE = os.path.join(DATA_DIR, "resource_status.json")
# LOCK_FILE = os.path.join(DATA_DIR, ".resource.lock")

# 方案3：使用用户主目录
# from pathlib import Path
# DATA_DIR = str(Path.home() / ".gpu_manager")
# RESOURCE_FILE = os.path.join(DATA_DIR, "resource_status.json")
# LOCK_FILE = os.path.join(DATA_DIR, ".resource.lock")


# ============================================================
# 服务器配置 - 可选修改
# ============================================================

# 服务器命名方案
# 方案1：默认命名（gpu-server-0, gpu-server-1, ...）
def get_server_name(server_id):
    return f"gpu-server-{server_id}"

# 方案2：使用实际主机名
# def get_server_name(server_id):
#     server_names = ["node01", "node02", "node03", "node04"]
#     return server_names[server_id]

# 方案3：使用IP地址
# def get_server_name(server_id):
#     server_ips = ["192.168.1.11", "192.168.1.12", "192.168.1.13", "192.168.1.14"]
#     return server_ips[server_id]

# 方案4：混合配置（不同服务器不同配置）
# 如果你的服务器配置不一样，定义每台服务器的具体配置
CUSTOM_SERVERS = None  # 设置为None使用统一配置

# 取消注释并修改以使用自定义配置
# CUSTOM_SERVERS = [
#     {"id": 0, "name": "high-gpu-01", "gpus": 8, "cpus": 128},
#     {"id": 1, "name": "high-gpu-02", "gpus": 8, "cpus": 128},
#     {"id": 2, "name": "low-gpu-01",  "gpus": 4, "cpus": 64},
#     {"id": 3, "name": "low-gpu-02",  "gpus": 4, "cpus": 64},
# ]


# ============================================================
# 资源限制配置 - 可选修改
# ============================================================

# GPU数量限制
MIN_GPUS = 2             # 最少需要几个GPU？（设为1允许单GPU任务）
MAX_GPUS = GPUS_PER_SERVER  # 最多允许几个GPU？

# CPU数量限制
MIN_CPUS = 1             # 最少需要几个CPU？
MAX_CPUS = CPUS_PER_SERVER  # 最多允许几个CPU？


# ============================================================
# 锁配置 - Windows用户必须修改
# ============================================================

import sys

# 锁机制选择
# 选项1: 'fcntl' - Linux/Unix（默认）
# 选项2: 'filelock' - 跨平台（需要 pip install filelock）
# 选项3: 'simple' - 简单标志文件锁

if sys.platform == 'win32':
    LOCK_TYPE = 'filelock'  # Windows推荐使用filelock
else:
    LOCK_TYPE = 'fcntl'     # Linux推荐使用fcntl

# 锁超时时间（秒）
LOCK_TIMEOUT = 60        # 获取锁的最长等待时间


# ============================================================
# 显示配置 - 可选修改
# ============================================================

# CLI表格显示语言
USE_CHINESE = True       # True=中文，False=英文

# 表格显示格式
TABLE_FORMAT = 'grid'    # 可选：'grid', 'simple', 'plain', 'fancy_grid'


# ============================================================
# 高级配置 - 通常不需要修改
# ============================================================

# 版本号
VERSION = "0.1"

# 日志级别
LOG_LEVEL = "INFO"       # DEBUG, INFO, WARNING, ERROR

# 状态文件编码
FILE_ENCODING = "utf-8"

# JSON缩进
JSON_INDENT = 2


# ============================================================
# 配置验证
# ============================================================

def validate_config():
    """验证配置是否合理"""
    errors = []
    
    if TOTAL_SERVERS < 1:
        errors.append(f"服务器数量必须 >= 1，当前: {TOTAL_SERVERS}")
    
    if GPUS_PER_SERVER < 1:
        errors.append(f"每台服务器GPU数量必须 >= 1，当前: {GPUS_PER_SERVER}")
    
    if CPUS_PER_SERVER < 1:
        errors.append(f"每台服务器CPU数量必须 >= 1，当前: {CPUS_PER_SERVER}")
    
    if MIN_GPUS < 1 or MIN_GPUS > MAX_GPUS:
        errors.append(f"GPU最小值必须在 1-{MAX_GPUS} 之间，当前: {MIN_GPUS}")
    
    if CUSTOM_SERVERS:
        if len(CUSTOM_SERVERS) != TOTAL_SERVERS:
            errors.append(f"自定义服务器数量({len(CUSTOM_SERVERS)})与TOTAL_SERVERS({TOTAL_SERVERS})不一致")
    
    if LOCK_TYPE not in ['fcntl', 'filelock', 'simple']:
        errors.append(f"无效的锁类型: {LOCK_TYPE}")
    
    if errors:
        print("❌ 配置错误:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


# ============================================================
# 配置信息显示
# ============================================================

def show_config():
    """显示当前配置"""
    print("\n" + "=" * 60)
    print("GPU资源管理器配置")
    print("=" * 60)
    print(f"\n服务器配置:")
    print(f"  服务器数量: {TOTAL_SERVERS}")
    print(f"  每台GPU数: {GPUS_PER_SERVER}")
    print(f"  每台CPU数: {CPUS_PER_SERVER}")
    print(f"  总GPU数: {TOTAL_SERVERS * GPUS_PER_SERVER}")
    print(f"  总CPU数: {TOTAL_SERVERS * CPUS_PER_SERVER}")
    
    print(f"\n文件路径:")
    print(f"  数据目录: {DATA_DIR if DATA_DIR != '.' else '当前目录'}")
    print(f"  状态文件: {RESOURCE_FILE}")
    print(f"  锁文件: {LOCK_FILE}")
    
    print(f"\n资源限制:")
    print(f"  GPU范围: {MIN_GPUS}-{MAX_GPUS}")
    print(f"  CPU范围: {MIN_CPUS}-{MAX_CPUS}")
    
    print(f"\n锁配置:")
    print(f"  锁类型: {LOCK_TYPE}")
    print(f"  锁超时: {LOCK_TIMEOUT}秒")
    
    if CUSTOM_SERVERS:
        print(f"\n自定义服务器配置:")
        for srv in CUSTOM_SERVERS:
            print(f"  {srv['name']}: {srv['gpus']} GPUs, {srv['cpus']} CPUs")
    
    print("\n" + "=" * 60 + "\n")


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    print("\n配置模板使用说明：")
    print("1. 复制此文件为 config.py")
    print("2. 根据实际情况修改配置")
    print("3. 在主程序中导入: from config import *")
    print("4. 运行验证: python config.py")
    
    print("\n当前配置:")
    show_config()
    
    print("配置验证:")
    if validate_config():
        print("✅ 配置有效！")
    else:
        print("❌ 配置有错误，请修正后再使用")

