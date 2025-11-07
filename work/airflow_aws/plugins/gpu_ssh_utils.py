"""
GPU服务器SSH连接工具类
"""
import paramiko
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GPUSSHClient:
    """GPU服务器SSH客户端封装类"""
    
    def __init__(
        self,
        hostname: str,
        username: str = 'ubuntu',
        port: int = 22,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化SSH客户端
        
        Args:
            hostname: 主机名或IP地址
            username: SSH用户名
            port: SSH端口
            key_path: 私钥文件路径
            password: 密码（如果不使用密钥）
            timeout: 连接超时时间（秒）
        """
        self.hostname = hostname
        self.username = username
        self.port = port
        self.key_path = key_path
        self.password = password
        self.timeout = timeout
        self.client = None
        
    def connect(self):
        """建立SSH连接"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_path:
                # 使用密钥认证
                private_key = paramiko.RSAKey.from_private_key_file(self.key_path)
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    pkey=private_key,
                    timeout=self.timeout
                )
                logger.info(f"使用密钥成功连接到 {self.hostname}")
            elif self.password:
                # 使用密码认证
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=self.timeout
                )
                logger.info(f"使用密码成功连接到 {self.hostname}")
            else:
                raise ValueError("必须提供密钥路径或密码")
                
        except Exception as e:
            logger.error(f"SSH连接失败: {str(e)}")
            raise
    
    def execute_command(self, command: str, timeout: int = 300) -> str:
        """
        执行SSH命令
        
        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            
        Returns:
            命令输出结果
        """
        if not self.client:
            raise RuntimeError("SSH客户端未连接，请先调用connect()")
        
        try:
            logger.info(f"执行命令: {command}")
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
            # 获取输出
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code != 0:
                logger.error(f"命令执行失败 (退出码: {exit_code})")
                logger.error(f"错误输出: {error}")
                raise RuntimeError(f"命令执行失败: {error}")
            
            logger.info(f"命令执行成功")
            return output
            
        except Exception as e:
            logger.error(f"执行命令时出错: {str(e)}")
            raise
    
    def execute_commands(self, commands: list, timeout: int = 300) -> list:
        """
        批量执行命令
        
        Args:
            commands: 命令列表
            timeout: 每个命令的超时时间
            
        Returns:
            每个命令的输出结果列表
        """
        results = []
        for cmd in commands:
            result = self.execute_command(cmd, timeout)
            results.append(result)
        return results
    
    def upload_file(self, local_path: str, remote_path: str):
        """
        上传文件到远程服务器
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
        """
        if not self.client:
            raise RuntimeError("SSH客户端未连接，请先调用connect()")
        
        try:
            sftp = self.client.open_sftp()
            logger.info(f"上传文件: {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)
            sftp.close()
            logger.info("文件上传成功")
        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise
    
    def download_file(self, remote_path: str, local_path: str):
        """
        从远程服务器下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径
        """
        if not self.client:
            raise RuntimeError("SSH客户端未连接，请先调用connect()")
        
        try:
            sftp = self.client.open_sftp()
            logger.info(f"下载文件: {remote_path} -> {local_path}")
            sftp.get(remote_path, local_path)
            sftp.close()
            logger.info("文件下载成功")
        except Exception as e:
            logger.error(f"文件下载失败: {str(e)}")
            raise
    
    def close(self):
        """关闭SSH连接"""
        if self.client:
            self.client.close()
            logger.info("SSH连接已关闭")
            self.client = None
    
    def __enter__(self):
        """支持上下文管理器"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时自动关闭连接"""
        self.close()

