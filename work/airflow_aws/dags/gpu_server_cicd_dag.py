"""
GPU服务器CICD DAG
通过私有链接SSH连接本地GPU服务器，执行git操作并更新Airflow变量
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.python import PythonOperator
import logging
import yaml
import os
import tempfile
from pathlib import Path

# 导入自定义工具
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins'))
from gpu_ssh_utils import GPUSSHClient
from aws_secrets_utils import get_secret_from_secrets_manager

logger = logging.getLogger(__name__)

# 默认参数
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG定义
with DAG(
    dag_id='gpu_server_cicd_workflow',
    default_args=default_args,
    description='通过SSH连接GPU服务器执行CICD操作',
    schedule_interval=None,  # 手动触发
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['gpu', 'cicd', 'ssh'],
    # 用户输入参数
    params={
        "gpu_server_ip": "",
        "workspace_path": "",
        "secrets_arn": "arn:aws:secretsmanager:region:account-id:secret:your-secret-name",
        "git_repo_url": "https://github.com/your-org/cicd-test.git",
        "git_branch": "cicd_01_etl",
        "version_file_path": "www/version.yaml"
    },
    render_template_as_native_obj=True,
) as dag:
    
    @task
    def validate_inputs(**context):
        """验证用户输入参数"""
        params = context['params']
        
        gpu_ip = params.get('gpu_server_ip', '').strip()
        workspace = params.get('workspace_path', '').strip()
        secrets_arn = params.get('secrets_arn', '').strip()
        
        if not gpu_ip:
            raise ValueError("GPU服务器IP地址不能为空")
        
        if not workspace:
            raise ValueError("Workspace路径不能为空")
            
        if not secrets_arn or 'your-secret' in secrets_arn:
            raise ValueError("请提供有效的Secrets Manager ARN")
        
        logger.info(f"输入验证通过 - GPU IP: {gpu_ip}, Workspace: {workspace}")
        
        return {
            'gpu_ip': gpu_ip,
            'workspace': workspace,
            'secrets_arn': secrets_arn,
            'git_repo_url': params.get('git_repo_url'),
            'git_branch': params.get('git_branch'),
            'version_file_path': params.get('version_file_path')
        }
    
    @task
    def retrieve_ssh_key(**context):
        """从AWS Secrets Manager获取SSH密钥"""
        validated_params = context['ti'].xcom_pull(task_ids='validate_inputs')
        secrets_arn = validated_params['secrets_arn']
        
        logger.info(f"正在从Secrets Manager获取密钥: {secrets_arn}")
        
        # 从Secrets Manager获取密钥
        secret_data = get_secret_from_secrets_manager(secrets_arn)
        
        # 创建临时目录存储密钥
        temp_dir = tempfile.mkdtemp(prefix='airflow_ssh_')
        key_path = os.path.join(temp_dir, 'ssh_private_key.pem')
        
        # 写入密钥文件
        with open(key_path, 'w') as f:
            f.write(secret_data)
        
        # 设置正确的权限
        os.chmod(key_path, 0o600)
        
        logger.info(f"SSH密钥已保存到: {key_path}")
        
        return {
            'key_path': key_path,
            'temp_dir': temp_dir
        }
    
    @task
    def test_ssh_connection(**context):
        """测试SSH连接"""
        validated_params = context['ti'].xcom_pull(task_ids='validate_inputs')
        key_info = context['ti'].xcom_pull(task_ids='retrieve_ssh_key')
        
        gpu_ip = validated_params['gpu_ip']
        key_path = key_info['key_path']
        
        logger.info(f"测试SSH连接到: {gpu_ip}")
        
        ssh_client = GPUSSHClient(
            hostname=gpu_ip,
            username='ubuntu',  # 根据实际情况修改
            key_path=key_path
        )
        
        try:
            ssh_client.connect()
            result = ssh_client.execute_command('whoami')
            logger.info(f"SSH连接成功! 用户: {result}")
            ssh_client.close()
            return True
        except Exception as e:
            logger.error(f"SSH连接失败: {str(e)}")
            raise
    
    @task
    def clone_and_checkout_repo(**context):
        """在GPU服务器上克隆仓库并切换分支"""
        validated_params = context['ti'].xcom_pull(task_ids='validate_inputs')
        key_info = context['ti'].xcom_pull(task_ids='retrieve_ssh_key')
        
        gpu_ip = validated_params['gpu_ip']
        workspace = validated_params['workspace']
        git_repo_url = validated_params['git_repo_url']
        git_branch = validated_params['git_branch']
        key_path = key_info['key_path']
        
        ssh_client = GPUSSHClient(
            hostname=gpu_ip,
            username='ubuntu',
            key_path=key_path
        )
        
        try:
            ssh_client.connect()
            
            # 创建workspace目录（如果不存在）
            ssh_client.execute_command(f'mkdir -p {workspace}')
            
            # 检查cicd-test目录是否存在
            repo_path = f"{workspace}/cicd-test"
            check_cmd = f"[ -d {repo_path} ] && echo 'exists' || echo 'not_exists'"
            result = ssh_client.execute_command(check_cmd)
            
            if 'exists' in result:
                logger.info(f"仓库已存在，更新代码...")
                # 如果存在，先删除再克隆（或者使用git pull）
                ssh_client.execute_command(f'rm -rf {repo_path}')
            
            # 克隆仓库
            logger.info(f"克隆仓库: {git_repo_url}")
            clone_cmd = f'cd {workspace} && git clone {git_repo_url}'
            ssh_client.execute_command(clone_cmd)
            
            # 切换到指定分支
            logger.info(f"切换到分支: {git_branch}")
            checkout_cmd = f'cd {repo_path} && git checkout {git_branch}'
            ssh_client.execute_command(checkout_cmd)
            
            # 验证当前分支
            verify_cmd = f'cd {repo_path} && git branch --show-current'
            current_branch = ssh_client.execute_command(verify_cmd)
            logger.info(f"当前分支: {current_branch}")
            
            ssh_client.close()
            
            return {
                'repo_path': repo_path,
                'current_branch': current_branch.strip()
            }
            
        except Exception as e:
            ssh_client.close()
            logger.error(f"Git操作失败: {str(e)}")
            raise
    
    @task
    def read_version_yaml(**context):
        """读取version.yaml文件内容"""
        validated_params = context['ti'].xcom_pull(task_ids='validate_inputs')
        key_info = context['ti'].xcom_pull(task_ids='retrieve_ssh_key')
        repo_info = context['ti'].xcom_pull(task_ids='clone_and_checkout_repo')
        
        gpu_ip = validated_params['gpu_ip']
        version_file_path = validated_params['version_file_path']
        repo_path = repo_info['repo_path']
        key_path = key_info['key_path']
        
        full_version_path = f"{repo_path}/{version_file_path}"
        
        ssh_client = GPUSSHClient(
            hostname=gpu_ip,
            username='ubuntu',
            key_path=key_path
        )
        
        try:
            ssh_client.connect()
            
            # 读取version.yaml文件
            logger.info(f"读取文件: {full_version_path}")
            cat_cmd = f'cat {full_version_path}'
            yaml_content = ssh_client.execute_command(cat_cmd)
            
            logger.info(f"YAML内容:\n{yaml_content}")
            
            ssh_client.close()
            
            # 解析YAML
            version_data = yaml.safe_load(yaml_content)
            logger.info(f"解析的版本数据: {version_data}")
            
            return version_data
            
        except Exception as e:
            ssh_client.close()
            logger.error(f"读取version.yaml失败: {str(e)}")
            raise
    
    @task
    def update_airflow_variables(**context):
        """更新Airflow Variables"""
        version_data = context['ti'].xcom_pull(task_ids='read_version_yaml')
        
        if not version_data:
            raise ValueError("版本数据为空")
        
        logger.info("开始更新Airflow Variables...")
        
        updated_vars = {}
        for key, value in version_data.items():
            try:
                # 设置或更新Variable
                Variable.set(key, value)
                updated_vars[key] = value
                logger.info(f"已更新Variable: {key} = {value}")
            except Exception as e:
                logger.error(f"更新Variable {key} 失败: {str(e)}")
                raise
        
        logger.info(f"成功更新 {len(updated_vars)} 个Variables: {updated_vars}")
        
        return updated_vars
    
    @task
    def cleanup_temp_files(**context):
        """清理临时文件"""
        key_info = context['ti'].xcom_pull(task_ids='retrieve_ssh_key')
        temp_dir = key_info.get('temp_dir')
        
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"已清理临时目录: {temp_dir}")
        
        return True
    
    # 定义任务流程
    validated_params = validate_inputs()
    key_info = retrieve_ssh_key()
    ssh_test = test_ssh_connection()
    repo_info = clone_and_checkout_repo()
    version_data = read_version_yaml()
    updated_vars = update_airflow_variables()
    cleanup = cleanup_temp_files()
    
    # 设置任务依赖
    validated_params >> key_info >> ssh_test >> repo_info >> version_data >> updated_vars >> cleanup

