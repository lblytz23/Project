"""
本地测试脚本 - 用于在部署前测试DAG的各个组件
"""
import sys
import os
from pathlib import Path

# 添加plugins目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'plugins'))

from gpu_ssh_utils import GPUSSHClient
from aws_secrets_utils import get_secret_from_secrets_manager


def test_secrets_manager():
    """测试Secrets Manager连接"""
    print("\n=== 测试Secrets Manager ===")
    
    secret_arn = input("请输入Secrets Manager ARN: ").strip()
    
    if not secret_arn:
        print("❌ ARN不能为空")
        return False
    
    try:
        secret_value = get_secret_from_secrets_manager(secret_arn)
        print(f"✓ 成功获取密钥 (长度: {len(secret_value)} 字符)")
        return True
    except Exception as e:
        print(f"❌ 获取密钥失败: {str(e)}")
        return False


def test_ssh_connection():
    """测试SSH连接"""
    print("\n=== 测试SSH连接 ===")
    
    hostname = input("请输入GPU服务器IP: ").strip()
    username = input("请输入SSH用户名 [ubuntu]: ").strip() or "ubuntu"
    key_path = input("请输入SSH私钥路径: ").strip()
    
    if not hostname or not key_path:
        print("❌ 主机名和密钥路径不能为空")
        return False
    
    try:
        ssh_client = GPUSSHClient(
            hostname=hostname,
            username=username,
            key_path=key_path
        )
        
        print("正在连接...")
        ssh_client.connect()
        print("✓ SSH连接成功")
        
        # 测试执行命令
        print("\n测试执行命令...")
        result = ssh_client.execute_command("whoami")
        print(f"✓ 当前用户: {result}")
        
        result = ssh_client.execute_command("pwd")
        print(f"✓ 当前目录: {result}")
        
        result = ssh_client.execute_command("uname -a")
        print(f"✓ 系统信息: {result}")
        
        ssh_client.close()
        print("\n✓ SSH测试完成")
        return True
        
    except Exception as e:
        print(f"❌ SSH连接失败: {str(e)}")
        return False


def test_git_operations():
    """测试Git操作"""
    print("\n=== 测试Git操作 ===")
    
    hostname = input("请输入GPU服务器IP: ").strip()
    username = input("请输入SSH用户名 [ubuntu]: ").strip() or "ubuntu"
    key_path = input("请输入SSH私钥路径: ").strip()
    workspace = input("请输入工作目录路径: ").strip()
    repo_url = input("请输入Git仓库URL: ").strip()
    branch = input("请输入分支名称: ").strip()
    
    if not all([hostname, key_path, workspace, repo_url, branch]):
        print("❌ 所有参数都不能为空")
        return False
    
    try:
        ssh_client = GPUSSHClient(
            hostname=hostname,
            username=username,
            key_path=key_path
        )
        
        ssh_client.connect()
        print("✓ SSH连接成功")
        
        # 创建工作目录
        print(f"\n创建工作目录: {workspace}")
        ssh_client.execute_command(f"mkdir -p {workspace}")
        print("✓ 工作目录创建成功")
        
        # 检查并清理旧仓库
        repo_path = f"{workspace}/cicd-test"
        print(f"\n检查仓库: {repo_path}")
        result = ssh_client.execute_command(
            f"[ -d {repo_path} ] && echo 'exists' || echo 'not_exists'"
        )
        
        if 'exists' in result:
            print("仓库已存在，正在清理...")
            ssh_client.execute_command(f"rm -rf {repo_path}")
            print("✓ 旧仓库清理完成")
        
        # 克隆仓库
        print(f"\n克隆仓库: {repo_url}")
        ssh_client.execute_command(
            f"cd {workspace} && git clone {repo_url}",
            timeout=300
        )
        print("✓ 仓库克隆成功")
        
        # 切换分支
        print(f"\n切换到分支: {branch}")
        ssh_client.execute_command(f"cd {repo_path} && git checkout {branch}")
        print("✓ 分支切换成功")
        
        # 验证分支
        current_branch = ssh_client.execute_command(
            f"cd {repo_path} && git branch --show-current"
        )
        print(f"✓ 当前分支: {current_branch}")
        
        ssh_client.close()
        print("\n✓ Git操作测试完成")
        return True
        
    except Exception as e:
        print(f"❌ Git操作失败: {str(e)}")
        return False


def test_yaml_reading():
    """测试读取YAML文件"""
    print("\n=== 测试读取YAML文件 ===")
    
    hostname = input("请输入GPU服务器IP: ").strip()
    username = input("请输入SSH用户名 [ubuntu]: ").strip() or "ubuntu"
    key_path = input("请输入SSH私钥路径: ").strip()
    yaml_path = input("请输入YAML文件完整路径: ").strip()
    
    if not all([hostname, key_path, yaml_path]):
        print("❌ 所有参数都不能为空")
        return False
    
    try:
        import yaml
        
        ssh_client = GPUSSHClient(
            hostname=hostname,
            username=username,
            key_path=key_path
        )
        
        ssh_client.connect()
        print("✓ SSH连接成功")
        
        # 读取YAML文件
        print(f"\n读取文件: {yaml_path}")
        yaml_content = ssh_client.execute_command(f"cat {yaml_path}")
        print(f"\n文件内容:\n{yaml_content}")
        
        # 解析YAML
        print("\n解析YAML...")
        data = yaml.safe_load(yaml_content)
        print(f"✓ YAML解析成功: {data}")
        
        ssh_client.close()
        print("\n✓ YAML读取测试完成")
        return True
        
    except Exception as e:
        print(f"❌ YAML读取失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("GPU服务器CICD - 本地测试工具")
    print("=" * 50)
    
    tests = {
        "1": ("测试Secrets Manager", test_secrets_manager),
        "2": ("测试SSH连接", test_ssh_connection),
        "3": ("测试Git操作", test_git_operations),
        "4": ("测试读取YAML", test_yaml_reading),
        "5": ("运行所有测试", None),
    }
    
    while True:
        print("\n请选择要运行的测试:")
        for key, (name, _) in tests.items():
            print(f"{key}. {name}")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-5): ").strip()
        
        if choice == "0":
            print("\n再见!")
            break
        elif choice == "5":
            # 运行所有测试
            results = []
            for key in ["1", "2", "3", "4"]:
                name, test_func = tests[key]
                print(f"\n{'=' * 50}")
                print(f"运行: {name}")
                print('=' * 50)
                result = test_func()
                results.append((name, result))
            
            # 总结
            print("\n" + "=" * 50)
            print("测试结果总结")
            print("=" * 50)
            for name, result in results:
                status = "✓ 通过" if result else "❌ 失败"
                print(f"{name}: {status}")
            
        elif choice in tests and tests[choice][1]:
            name, test_func = tests[choice]
            test_func()
        else:
            print("❌ 无效选项，请重新选择")


if __name__ == "__main__":
    main()

