# 🚀 快速开始指南

10分钟内让你的GPU服务器CICD DAG运行起来！

## ⚡ 5步快速部署

### 步骤1: 准备SSH密钥（2分钟）

```bash
# 将SSH私钥上传到AWS Secrets Manager
aws secretsmanager create-secret \
    --name gpu-server-ssh-key \
    --secret-string file://~/.ssh/id_rsa \
    --region us-east-1

# 记录返回的ARN
# 示例: arn:aws:secretsmanager:us-east-1:123456789012:secret:gpu-server-ssh-key-AbCdEf
```

### 步骤2: 配置部署脚本（1分钟）

编辑 `deploy.ps1` 或 `deploy.sh`：

```powershell
# Windows (PowerShell)
$MwaaBucket = "your-actual-mwaa-bucket-name"
$AwsRegion = "us-east-1"
```

```bash
# Linux/Mac (Bash)
MWAA_BUCKET="your-actual-mwaa-bucket-name"
AWS_REGION="us-east-1"
```

### 步骤3: 部署到MWAA（2分钟）

```powershell
# Windows
.\deploy.ps1
```

```bash
# Linux/Mac
chmod +x deploy.sh
./deploy.sh
```

### 步骤4: 配置IAM权限（3分钟）

将以下策略附加到MWAA执行角色：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:*:*:secret:gpu-server-ssh-key-*"
        }
    ]
}
```

### 步骤5: 触发DAG（2分钟）

1. 打开Airflow UI（从MWAA控制台获取URL）
2. 找到 `gpu_server_cicd_workflow`
3. 点击"Trigger DAG"
4. 填入参数：

```json
{
  "gpu_server_ip": "10.0.1.100",
  "workspace_path": "/home/ubuntu/workspace",
  "secrets_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:gpu-server-ssh-key-AbCdEf"
}
```

5. 点击"Trigger"

## ✅ 验证部署

### 检查DAG是否加载

```bash
aws mwaa create-cli-token --name your-mwaa-environment \
    | jq -r '.CliToken' \
    | xargs -I {} curl -X GET \
    "https://your-webserver-url/api/v1/dags/gpu_server_cicd_workflow" \
    -H "Authorization: Bearer {}"
```

### 查看DAG运行状态

在Airflow UI中：
- 绿色 ✓ = 成功
- 红色 ✗ = 失败
- 黄色 ⟳ = 运行中

## 🔧 本地测试（可选）

在部署到MWAA之前，可以本地测试：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试脚本
python test_local.py

# 选择测试项：
# 1. 测试Secrets Manager
# 2. 测试SSH连接
# 3. 测试Git操作
# 4. 测试读取YAML
```

## 📊 预期结果

成功运行后，你会看到：

1. **validate_inputs** ✓ - 参数验证通过
2. **retrieve_ssh_key** ✓ - SSH密钥已获取
3. **test_ssh_connection** ✓ - SSH连接成功
4. **clone_and_checkout_repo** ✓ - Git仓库已克隆
5. **read_version_yaml** ✓ - 版本文件已读取
6. **update_airflow_variables** ✓ - Variables已更新
7. **cleanup_temp_files** ✓ - 临时文件已清理

在Airflow Variables中会看到更新的值：
- `a`: 10.0
- `b`: 10.0
- `c`: 10.0
- `d`: 10.0

## 🐛 常见问题

### Q1: DAG没有出现在UI中

**解决方法：**
- 等待3-5分钟让MWAA加载DAG
- 检查dag-processing日志是否有语法错误
- 确认S3路径正确: `s3://bucket/dags/gpu_server_cicd_dag.py`

### Q2: SSH连接失败

**解决方法：**
- 检查VPC网络配置和路由
- 确认安全组允许SSH（端口22）
- 测试网络连通性：`telnet gpu-ip 22`

### Q3: Secrets Manager权限被拒绝

**解决方法：**
- 检查IAM角色是否附加了正确的策略
- 确认Secret ARN正确
- 测试：`aws secretsmanager get-secret-value --secret-id <arn>`

## 📚 下一步

- 📖 阅读完整文档：[README.md](README.md)
- 🏗️ MWAA环境配置：[MWAA_SETUP.md](MWAA_SETUP.md)
- 💡 查看示例：[examples/](examples/)
- 🔒 安全最佳实践：[README.md#安全最佳实践](README.md#安全最佳实践)

## 💬 需要帮助？

- 检查CloudWatch日志
- 查看Airflow任务日志
- 参考故障排查部分
- 运行本地测试脚本定位问题

---

**祝你部署顺利！** 🎉

