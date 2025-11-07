# GPU服务器CICD - Airflow DAG

通过AWS MWAA（Managed Workflows for Apache Airflow）使用私有链接SSH连接本地GPU服务器，执行Git操作并更新Airflow变量。

## 📋 功能特性

1. **用户输入界面** - 在触发DAG时提供交互式输入界面
2. **AWS Secrets Manager集成** - 安全地获取和管理SSH密钥
3. **SSH连接** - 通过私有链接连接本地GPU服务器
4. **Git操作** - 自动克隆仓库并切换到指定分支
5. **版本管理** - 读取version.yaml并更新Airflow变量
6. **自动清理** - 任务完成后自动清理临时文件

## 🏗️ 项目结构

```
airflow_aws/
├── dags/
│   └── gpu_server_cicd_dag.py          # 主DAG文件
├── plugins/
│   ├── __init__.py                     # 插件包初始化
│   ├── gpu_ssh_utils.py                # SSH工具类
│   └── aws_secrets_utils.py            # AWS Secrets Manager工具
├── config/
│   └── config.yaml                     # 配置文件
├── requirements.txt                    # Python依赖
├── .env.example                        # 环境变量示例
└── README.md                           # 本文件
```

## 🚀 快速开始

### 1. 环境准备

#### 1.1 安装依赖

```bash
pip install -r requirements.txt
```

#### 1.2 配置AWS凭证

确保您的AWS凭证已正确配置，可以通过以下方式之一：

- AWS CLI配置：`aws configure`
- 环境变量：设置 `AWS_ACCESS_KEY_ID` 和 `AWS_SECRET_ACCESS_KEY`
- IAM角色（推荐在MWAA中使用）

#### 1.3 准备SSH密钥

将您的SSH私钥存储到AWS Secrets Manager：

```bash
aws secretsmanager create-secret \
    --name gpu-server-ssh-key \
    --description "GPU服务器SSH私钥" \
    --secret-string file://path/to/your/private_key.pem \
    --region us-east-1
```

或者，如果密钥是JSON格式：

```bash
aws secretsmanager create-secret \
    --name gpu-server-ssh-key \
    --description "GPU服务器SSH私钥" \
    --secret-string '{"private_key":"-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"}' \
    --region us-east-1
```

记录返回的ARN，格式类似：
```
arn:aws:secretsmanager:us-east-1:123456789012:secret:gpu-server-ssh-key-AbCdEf
```

### 2. 部署到MWAA

#### 2.1 上传DAG和插件

将文件上传到MWAA的S3存储桶：

```bash
# 上传DAG文件
aws s3 cp dags/gpu_server_cicd_dag.py s3://your-mwaa-bucket/dags/

# 上传插件（需要打包为zip）
cd plugins
zip -r plugins.zip .
aws s3 cp plugins.zip s3://your-mwaa-bucket/plugins/
cd ..
```

#### 2.2 配置MWAA环境

1. 在MWAA环境中添加Python依赖：
   - 在AWS控制台进入MWAA环境
   - 编辑环境
   - 在"Requirements file"中上传 `requirements.txt`

2. 配置IAM权限：
   确保MWAA执行角色具有以下权限：
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
               "Resource": "arn:aws:secretsmanager:*:*:secret:gpu-server-ssh-key-*"
           }
       ]
   }
   ```

#### 2.3 配置VPC和私有链接

确保您的MWAA环境配置了VPC私有链接，能够访问本地GPU服务器：

1. 配置VPC Peering或VPN连接
2. 配置安全组，允许SSH端口（22）访问
3. 确保路由表正确配置

### 3. 使用DAG

#### 3.1 在Airflow UI触发DAG

1. 登录到MWAA的Airflow Web界面
2. 找到DAG：`gpu_server_cicd_workflow`
3. 点击"Trigger DAG"按钮
4. 在弹出的参数表单中填入：

   | 参数名 | 说明 | 示例 |
   |--------|------|------|
   | gpu_server_ip | GPU服务器IP地址 | 10.0.1.100 |
   | workspace_path | 工作目录路径 | /home/ubuntu/workspace |
   | secrets_arn | Secrets Manager ARN | arn:aws:secretsmanager:us-east-1:123456789012:secret:gpu-server-ssh-key-AbCdEf |
   | git_repo_url | Git仓库URL | https://github.com/your-org/cicd-test.git |
   | git_branch | Git分支名 | cicd_01_etl |
   | version_file_path | 版本文件路径 | www/version.yaml |

5. 点击"Trigger"开始执行

#### 3.2 使用Airflow CLI触发

```bash
airflow dags trigger gpu_server_cicd_workflow \
    --conf '{
        "gpu_server_ip": "10.0.1.100",
        "workspace_path": "/home/ubuntu/workspace",
        "secrets_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:gpu-server-ssh-key-AbCdEf",
        "git_repo_url": "https://github.com/your-org/cicd-test.git",
        "git_branch": "cicd_01_etl",
        "version_file_path": "www/version.yaml"
    }'
```

#### 3.3 使用AWS CLI通过MWAA API触发

```bash
aws mwaa create-cli-token --name your-mwaa-environment-name \
    | jq -r '.CliToken' \
    | xargs -I {} curl -X POST \
    "https://your-mwaa-webserver-url/api/v1/dags/gpu_server_cicd_workflow/dagRuns" \
    -H "Authorization: Bearer {}" \
    -H "Content-Type: application/json" \
    -d '{
        "conf": {
            "gpu_server_ip": "10.0.1.100",
            "workspace_path": "/home/ubuntu/workspace",
            "secrets_arn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:gpu-server-ssh-key-AbCdEf"
        }
    }'
```

## 📊 DAG工作流程

DAG包含以下任务：

```
validate_inputs → retrieve_ssh_key → test_ssh_connection → 
clone_and_checkout_repo → read_version_yaml → 
update_airflow_variables → cleanup_temp_files
```

### 任务说明

1. **validate_inputs** - 验证用户输入的参数
2. **retrieve_ssh_key** - 从AWS Secrets Manager获取SSH密钥
3. **test_ssh_connection** - 测试SSH连接是否正常
4. **clone_and_checkout_repo** - 克隆Git仓库并切换分支
5. **read_version_yaml** - 读取version.yaml文件内容
6. **update_airflow_variables** - 更新Airflow变量
7. **cleanup_temp_files** - 清理临时文件

## 🔧 配置说明

### version.yaml格式

DAG期望的`version.yaml`文件格式：

```yaml
a: 10.0
b: 10.0
c: 10.0
d: 10.0
```

这些值将被读取并更新为Airflow Variables，可以在其他DAG中使用。

### SSH连接配置

默认SSH配置：
- 用户名: `ubuntu`
- 端口: `22`
- 超时: `30秒`

可以在 `config/config.yaml` 中修改这些默认值。

### AWS区域配置

默认使用 `us-east-1` 区域，可以通过以下方式修改：
1. 修改 `config/config.yaml` 中的 `aws.default_region`
2. 在Secrets ARN中自动识别区域

## 🔒 安全最佳实践

1. **密钥管理**
   - ✅ 使用AWS Secrets Manager存储SSH密钥
   - ✅ 定期轮换密钥
   - ❌ 不要在代码中硬编码密钥

2. **网络安全**
   - ✅ 使用VPC私有链接连接GPU服务器
   - ✅ 配置安全组限制访问
   - ✅ 使用最小权限原则

3. **访问控制**
   - ✅ 使用IAM角色而不是访问密钥
   - ✅ 限制Secrets Manager访问权限
   - ✅ 启用CloudTrail审计

## 🐛 故障排查

### SSH连接失败

1. **检查网络连通性**
   ```bash
   # 在MWAA环境中测试
   ping <gpu_server_ip>
   telnet <gpu_server_ip> 22
   ```

2. **检查SSH密钥**
   - 确认Secrets Manager中的密钥格式正确
   - 确认密钥权限为600

3. **检查安全组规则**
   - 确认MWAA安全组允许出站SSH流量
   - 确认GPU服务器安全组允许入站SSH流量

### Git操作失败

1. **检查仓库URL**
   - 确认仓库URL可访问
   - 如果是私有仓库，确认SSH密钥有访问权限

2. **检查分支名称**
   - 确认分支存在
   - 检查分支名称拼写

### Secrets Manager访问失败

1. **检查IAM权限**
   ```bash
   aws secretsmanager get-secret-value --secret-id <your-secret-arn>
   ```

2. **检查ARN格式**
   - 确认ARN格式正确
   - 确认区域匹配

## 📝 日志查看

在Airflow UI中查看任务日志：
1. 进入DAG运行详情页
2. 点击任务节点
3. 查看"Log"选项卡

关键日志位置：
- SSH连接日志：`test_ssh_connection` 任务
- Git操作日志：`clone_and_checkout_repo` 任务
- 变量更新日志：`update_airflow_variables` 任务

## 🔄 版本历史

- **v1.0.0** (2025-11-06)
  - 初始版本
  - 支持SSH连接和Git操作
  - 支持version.yaml解析
  - 支持Airflow变量更新

## 📚 相关文档

- [AWS MWAA官方文档](https://docs.aws.amazon.com/mwaa/)
- [Apache Airflow文档](https://airflow.apache.org/docs/)
- [AWS Secrets Manager文档](https://docs.aws.amazon.com/secretsmanager/)
- [Paramiko SSH库文档](https://docs.paramiko.org/)

## 💡 常见问题

**Q: 如何处理Git仓库需要认证的情况？**

A: 有两种方式：
1. 使用HTTPS + Personal Access Token
2. 配置SSH密钥用于Git访问（需要在GPU服务器上配置）

**Q: 可以同时连接多个GPU服务器吗？**

A: 可以，通过并行任务或动态任务映射实现。

**Q: 如何监控DAG执行状态？**

A: 使用Airflow的邮件通知、Slack集成或CloudWatch告警。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

