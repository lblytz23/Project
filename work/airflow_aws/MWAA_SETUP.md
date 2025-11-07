# MWAA环境配置指南

本文档详细说明如何设置AWS MWAA环境以支持GPU服务器CICD DAG。

## 📋 前置条件

- AWS账户并具有必要权限
- AWS CLI已安装和配置
- 了解VPC和网络配置
- 了解IAM权限管理

## 🔧 步骤1: 创建VPC和网络配置

### 1.1 创建VPC（如果还没有）

```bash
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=mwaa-vpc}]' \
    --region us-east-1
```

### 1.2 创建私有子网

MWAA需要至少2个私有子网在不同的可用区：

```bash
# 子网1
aws ec2 create-subnet \
    --vpc-id vpc-xxxxxx \
    --cidr-block 10.0.1.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=mwaa-private-subnet-1}]'

# 子网2
aws ec2 create-subnet \
    --vpc-id vpc-xxxxxx \
    --cidr-block 10.0.2.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=mwaa-private-subnet-2}]'
```

### 1.3 配置VPN或私有链接连接到GPU服务器

**方案A: Site-to-Site VPN**

```bash
# 创建Customer Gateway
aws ec2 create-customer-gateway \
    --type ipsec.1 \
    --public-ip <your-gpu-server-public-ip> \
    --bgp-asn 65000 \
    --tag-specifications 'ResourceType=customer-gateway,Tags=[{Key=Name,Value=gpu-server-gateway}]'

# 创建Virtual Private Gateway
aws ec2 create-vpn-gateway \
    --type ipsec.1 \
    --tag-specifications 'ResourceType=vpn-gateway,Tags=[{Key=Name,Value=mwaa-vpn-gateway}]'

# 附加到VPC
aws ec2 attach-vpn-gateway \
    --vpn-gateway-id vgw-xxxxxx \
    --vpc-id vpc-xxxxxx
```

**方案B: AWS Direct Connect**

适用于高带宽、低延迟需求。

**方案C: VPC Peering（如果GPU服务器在另一个VPC）**

```bash
aws ec2 create-vpc-peering-connection \
    --vpc-id vpc-xxxxxx \
    --peer-vpc-id vpc-yyyyyy \
    --peer-region us-east-1
```

## 🗄️ 步骤2: 创建S3存储桶

### 2.1 创建MWAA存储桶

```bash
aws s3 mb s3://my-mwaa-bucket --region us-east-1

# 启用版本控制
aws s3api put-bucket-versioning \
    --bucket my-mwaa-bucket \
    --versioning-configuration Status=Enabled
```

### 2.2 创建必要的文件夹

```bash
aws s3api put-object --bucket my-mwaa-bucket --key dags/
aws s3api put-object --bucket my-mwaa-bucket --key plugins/
aws s3api put-object --bucket my-mwaa-bucket --key config/
```

### 2.3 配置存储桶策略

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "airflow.amazonaws.com"
            },
            "Action": [
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::my-mwaa-bucket",
                "arn:aws:s3:::my-mwaa-bucket/*"
            ]
        }
    ]
}
```

## 🔐 步骤3: 配置Secrets Manager

### 3.1 存储SSH私钥

**方法1: 使用AWS CLI**

```bash
# 从文件读取
aws secretsmanager create-secret \
    --name gpu-server-ssh-key \
    --description "GPU服务器SSH私钥" \
    --secret-string file://path/to/private_key.pem \
    --region us-east-1
```

**方法2: 使用JSON格式**

```bash
aws secretsmanager create-secret \
    --name gpu-server-ssh-key \
    --description "GPU服务器SSH私钥" \
    --secret-string '{"private_key":"-----BEGIN RSA PRIVATE KEY-----\nMII...\n-----END RSA PRIVATE KEY-----"}' \
    --region us-east-1
```

### 3.2 记录Secret ARN

执行后会返回ARN，格式如：
```
arn:aws:secretsmanager:us-east-1:123456789012:secret:gpu-server-ssh-key-AbCdEf
```

保存此ARN，在触发DAG时需要使用。

## 👤 步骤4: 配置IAM角色和权限

### 4.1 创建MWAA执行角色

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "airflow.amazonaws.com",
                    "airflow-env.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

### 4.2 附加权限策略

**基础MWAA权限（AWS托管策略）：**
- `AmazonMWAAFullAccess`

**自定义策略 - S3访问：**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject*",
                "s3:GetBucket*",
                "s3:List*"
            ],
            "Resource": [
                "arn:aws:s3:::my-mwaa-bucket",
                "arn:aws:s3:::my-mwaa-bucket/*"
            ]
        }
    ]
}
```

**自定义策略 - Secrets Manager访问：**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:gpu-server-ssh-key-*"
        }
    ]
}
```

**自定义策略 - CloudWatch日志：**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:log-group:/aws/mwaa/*"
        }
    ]
}
```

### 4.3 创建完整的IAM角色

```bash
# 创建角色
aws iam create-role \
    --role-name mwaa-execution-role \
    --assume-role-policy-document file://trust-policy.json

# 附加策略
aws iam attach-role-policy \
    --role-name mwaa-execution-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonMWAAFullAccess

aws iam put-role-policy \
    --role-name mwaa-execution-role \
    --policy-name s3-access \
    --policy-document file://s3-policy.json

aws iam put-role-policy \
    --role-name mwaa-execution-role \
    --policy-name secrets-manager-access \
    --policy-document file://secrets-policy.json
```

## 🚀 步骤5: 创建MWAA环境

### 5.1 准备配置文件

创建 `mwaa-config.json`：

```json
{
    "Name": "my-mwaa-environment",
    "ExecutionRoleArn": "arn:aws:iam::123456789012:role/mwaa-execution-role",
    "SourceBucketArn": "arn:aws:s3:::my-mwaa-bucket",
    "DagS3Path": "dags",
    "NetworkConfiguration": {
        "SubnetIds": [
            "subnet-xxxxxx",
            "subnet-yyyyyy"
        ],
        "SecurityGroupIds": []
    },
    "PluginsS3Path": "plugins/plugins.zip",
    "RequirementsS3Path": "requirements.txt",
    "AirflowVersion": "2.7.2",
    "EnvironmentClass": "mw1.small",
    "MaxWorkers": 5,
    "MinWorkers": 1,
    "Schedulers": 2,
    "WebserverAccessMode": "PUBLIC_ONLY",
    "LoggingConfiguration": {
        "DagProcessingLogs": {
            "Enabled": true,
            "LogLevel": "INFO"
        },
        "SchedulerLogs": {
            "Enabled": true,
            "LogLevel": "INFO"
        },
        "TaskLogs": {
            "Enabled": true,
            "LogLevel": "INFO"
        },
        "WorkerLogs": {
            "Enabled": true,
            "LogLevel": "INFO"
        },
        "WebserverLogs": {
            "Enabled": true,
            "LogLevel": "INFO"
        }
    }
}
```

### 5.2 创建环境

```bash
aws mwaa create-environment --cli-input-json file://mwaa-config.json
```

创建过程需要20-30分钟。

### 5.3 检查创建状态

```bash
aws mwaa get-environment --name my-mwaa-environment
```

## 🔒 步骤6: 配置安全组

### 6.1 为MWAA创建安全组

```bash
aws ec2 create-security-group \
    --group-name mwaa-security-group \
    --description "Security group for MWAA environment" \
    --vpc-id vpc-xxxxxx
```

### 6.2 配置出站规则（允许SSH到GPU服务器）

```bash
aws ec2 authorize-security-group-egress \
    --group-id sg-xxxxxx \
    --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges='[{CidrIp=10.x.x.x/32,Description="GPU Server SSH"}]'
```

### 6.3 配置GPU服务器安全组

在GPU服务器的安全组中添加入站规则，允许来自MWAA的SSH连接。

## ✅ 步骤7: 验证配置

### 7.1 检查VPC连通性

创建一个测试DAG验证网络连接：

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def test_connectivity():
    import socket
    gpu_ip = "10.x.x.x"
    port = 22
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((gpu_ip, port))
    sock.close()
    if result == 0:
        print(f"✓ 可以连接到 {gpu_ip}:{port}")
    else:
        print(f"✗ 无法连接到 {gpu_ip}:{port}")

with DAG('test_connectivity', start_date=datetime(2025, 1, 1), schedule_interval=None) as dag:
    PythonOperator(task_id='test', python_callable=test_connectivity)
```

### 7.2 检查Secrets Manager访问

```python
def test_secrets():
    import boto3
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='gpu-server-ssh-key')
    print("✓ 成功访问Secrets Manager")
```

## 📊 步骤8: 监控和日志

### 8.1 配置CloudWatch告警

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name mwaa-worker-cpu-high \
    --alarm-description "Alert when MWAA worker CPU is high" \
    --metric-name CPUUtilization \
    --namespace AWS/MWAA \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

### 8.2 查看日志

```bash
# 查看DAG处理日志
aws logs tail /aws/mwaa/my-mwaa-environment/dag-processing

# 查看调度器日志
aws logs tail /aws/mwaa/my-mwaa-environment/scheduler

# 查看任务日志
aws logs tail /aws/mwaa/my-mwaa-environment/task
```

## 💰 成本优化建议

1. **选择合适的环境大小**
   - 开发: `mw1.small`
   - 生产: `mw1.medium` 或 `mw1.large`

2. **配置自动缩放**
   - 设置 `MinWorkers` 和 `MaxWorkers`

3. **使用S3生命周期策略**
   - 自动删除旧的日志和临时文件

4. **定期审查未使用的资源**

## 🔍 故障排查

### 问题1: 无法连接到GPU服务器

- 检查VPN/Peering连接状态
- 检查路由表配置
- 检查安全组规则
- 使用VPC Flow Logs排查

### 问题2: Secrets Manager访问被拒绝

- 检查IAM角色权限
- 检查Secret的资源策略
- 确认区域匹配

### 问题3: DAG不显示

- 检查S3路径配置
- 检查DAG语法错误
- 查看dag-processing日志

## 📚 参考资源

- [MWAA官方文档](https://docs.aws.amazon.com/mwaa/)
- [VPC配置最佳实践](https://docs.aws.amazon.com/vpc/)
- [Secrets Manager最佳实践](https://docs.aws.amazon.com/secretsmanager/)

