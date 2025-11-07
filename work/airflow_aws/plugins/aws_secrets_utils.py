"""
AWS Secrets Manager工具函数
"""
import boto3
import json
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_secret_from_secrets_manager(secret_arn: str, region_name: str = None) -> str:
    """
    从AWS Secrets Manager获取密钥
    
    Args:
        secret_arn: Secrets Manager的ARN
        region_name: AWS区域名称，如果为None则从ARN中提取
        
    Returns:
        密钥内容（字符串）
    """
    try:
        # 如果未指定区域，从ARN中提取
        if not region_name:
            # ARN格式: arn:aws:secretsmanager:region:account-id:secret:name
            arn_parts = secret_arn.split(':')
            if len(arn_parts) >= 4:
                region_name = arn_parts[3]
            else:
                region_name = 'us-east-1'  # 默认区域
        
        logger.info(f"从Secrets Manager获取密钥: {secret_arn}")
        logger.info(f"使用区域: {region_name}")
        
        # 创建Secrets Manager客户端
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        # 获取密钥值
        get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
        
        # 根据密钥类型获取内容
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            logger.info("成功获取密钥（SecretString格式）")
            
            # 尝试解析JSON格式的密钥
            try:
                secret_dict = json.loads(secret)
                # 如果密钥是JSON格式，通常SSH密钥会存储在特定字段中
                if 'private_key' in secret_dict:
                    return secret_dict['private_key']
                elif 'ssh_key' in secret_dict:
                    return secret_dict['ssh_key']
                elif 'key' in secret_dict:
                    return secret_dict['key']
                else:
                    # 返回第一个值
                    return list(secret_dict.values())[0]
            except json.JSONDecodeError:
                # 如果不是JSON格式，直接返回字符串
                return secret
        else:
            # 二进制密钥
            secret = get_secret_value_response['SecretBinary']
            logger.info("成功获取密钥（Binary格式）")
            return secret.decode('utf-8')
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"获取密钥失败: {error_code}")
        
        if error_code == 'ResourceNotFoundException':
            logger.error(f"密钥未找到: {secret_arn}")
        elif error_code == 'InvalidRequestException':
            logger.error("请求无效")
        elif error_code == 'InvalidParameterException':
            logger.error("参数无效")
        elif error_code == 'DecryptionFailure':
            logger.error("密钥解密失败")
        elif error_code == 'InternalServiceError':
            logger.error("服务内部错误")
        
        raise
    except Exception as e:
        logger.error(f"获取密钥时发生未知错误: {str(e)}")
        raise


def create_or_update_secret(
    secret_name: str,
    secret_value: str,
    description: str = None,
    region_name: str = 'us-east-1'
) -> dict:
    """
    创建或更新Secrets Manager中的密钥
    
    Args:
        secret_name: 密钥名称
        secret_value: 密钥值
        description: 密钥描述
        region_name: AWS区域
        
    Returns:
        操作结果字典
    """
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        # 尝试更新现有密钥
        try:
            response = client.update_secret(
                SecretId=secret_name,
                SecretString=secret_value
            )
            logger.info(f"密钥更新成功: {secret_name}")
            return {
                'action': 'updated',
                'arn': response['ARN'],
                'name': response['Name']
            }
        except client.exceptions.ResourceNotFoundException:
            # 如果密钥不存在，创建新密钥
            response = client.create_secret(
                Name=secret_name,
                Description=description or f"Created by Airflow DAG",
                SecretString=secret_value
            )
            logger.info(f"密钥创建成功: {secret_name}")
            return {
                'action': 'created',
                'arn': response['ARN'],
                'name': response['Name']
            }
            
    except Exception as e:
        logger.error(f"创建/更新密钥失败: {str(e)}")
        raise


def delete_secret(secret_name: str, region_name: str = 'us-east-1', force: bool = False):
    """
    删除Secrets Manager中的密钥
    
    Args:
        secret_name: 密钥名称
        region_name: AWS区域
        force: 是否强制删除（不等待恢复期）
    """
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        if force:
            client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True
            )
            logger.info(f"密钥已强制删除: {secret_name}")
        else:
            client.delete_secret(SecretId=secret_name)
            logger.info(f"密钥已标记删除（30天恢复期）: {secret_name}")
            
    except Exception as e:
        logger.error(f"删除密钥失败: {str(e)}")
        raise

