# VertexAI Pipeline 监控脚本

这个 Airflow DAG 用于监控 GCP VertexAI Pipeline 的运行状态，并在发现长时间运行的 Pipeline 时通过 Microsoft Teams 发送通知。

## 功能特点

- ✅ 自动监控所有状态为 `running` 的 VertexAI Pipeline
- ✅ 检测运行时长超过 2 天的 Pipeline
- ✅ 通过 Teams Webhook 发送详细的通知
- ✅ 每天下午 4 点自动执行
- ✅ 包含 Pipeline 名称、URL、运行时长等详细信息

## 安装步骤

### 1. 安装依赖包

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install apache-airflow>=2.5.0
pip install google-cloud-aiplatform>=1.34.0
pip install requests>=2.28.0
```

### 2. 配置 GCP 认证

确保 Airflow 运行环境有访问 GCP VertexAI 的权限。可以通过以下方式之一：

**选项 A: 使用服务账号密钥文件**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

**选项 B: 使用 GCP Composer**  
如果在 GCP Composer 上运行，会自动使用默认服务账号。

**选项 C: 使用 Airflow Connection**  
在 Airflow Web UI 中配置 Google Cloud 连接。

### 3. 设置 Airflow Variables

通过 Airflow Web UI 或命令行设置以下变量：

```bash
# GCP 项目 ID
airflow variables set gcp_project_id "your-project-id"

# VertexAI 区域
airflow variables set gcp_region "us-central1"

# Teams Webhook URL
airflow variables set teams_webhook_url "https://outlook.office.com/webhook/your-webhook-url"
```

### 4. 配置 Teams Webhook

1. 在 Microsoft Teams 中打开目标频道
2. 点击频道名称旁的 `...` 按钮
3. 选择 "连接器" (Connectors)
4. 搜索并添加 "传入 Webhook" (Incoming Webhook)
5. 配置 Webhook 名称和图标
6. 复制生成的 Webhook URL
7. 将 URL 保存到 Airflow Variables 中

### 5. 部署 DAG

将 `test.py` 文件复制到 Airflow 的 DAGs 目录：

```bash
cp test.py $AIRFLOW_HOME/dags/
```

## 使用说明

### 手动触发 DAG

```bash
airflow dags trigger vertexai_pipeline_monitor
```

### 测试 DAG

```bash
airflow dags test vertexai_pipeline_monitor 2025-10-29
```

### 查看 DAG 运行日志

```bash
airflow tasks logs vertexai_pipeline_monitor monitor_pipelines 2025-10-29
```

## 配置参数

### 调度时间

当前设置为每天下午 4 点（16:00）执行。如需修改，在 `test.py` 中更改：

```python
schedule_interval='0 16 * * *',  # cron 格式: 分 时 日 月 周
```

常用 cron 示例：
- `0 16 * * *` - 每天下午 4 点
- `0 */6 * * *` - 每 6 小时
- `0 9,17 * * *` - 每天上午 9 点和下午 5 点
- `0 16 * * 1-5` - 工作日下午 4 点

### 监控阈值

当前设置为 2 天。如需修改，在 `test.py` 中更改：

```python
DURATION_THRESHOLD_DAYS = 2
```

## DAG 结构

```
monitor_pipelines (Task 1)
    │
    ├── 连接 VertexAI
    ├── 获取所有 running 状态的 Pipeline
    ├── 检查运行时长
    ├── 筛选超过 2 天的 Pipeline
    └── 通过 XCom 传递数据
         │
         ▼
send_teams_notification (Task 2)
    │
    ├── 从 XCom 获取超时 Pipeline 列表
    ├── 构建 Teams 消息卡片
    └── 发送到 Teams Webhook
```

## 输出示例

### Teams 通知消息

通知包含以下信息：
- ⚠️ 标题：VertexAI Pipeline 运行超时警告
- 📊 超时 Pipeline 数量
- 📋 每个 Pipeline 的详细信息：
  - Pipeline 名称
  - 运行时长（天数和小时数）
  - 创建时间
  - 状态
  - 直接访问链接
- 🔗 快速访问 Vertex AI Console 的按钮

## 故障排查

### 问题 1: 认证失败

**错误信息**: `DefaultCredentialsError: Could not automatically determine credentials`

**解决方案**:
- 确保设置了 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量
- 检查服务账号是否有 `Vertex AI User` 权限

### 问题 2: Teams 通知发送失败

**错误信息**: `Teams webhook failed with status 400`

**解决方案**:
- 检查 Webhook URL 是否正确
- 确认 Webhook 在 Teams 中是否还处于激活状态
- 检查消息格式是否符合 Teams 要求

### 问题 3: 找不到 Pipeline

**可能原因**:
- GCP 项目 ID 或区域配置错误
- 服务账号权限不足
- 确实没有处于 running 状态的 Pipeline

## 权限要求

运行此脚本的服务账号需要以下 GCP IAM 权限：

- `aiplatform.pipelineJobs.list`
- `aiplatform.pipelineJobs.get`

推荐角色：
- `roles/aiplatform.user` (Vertex AI User)

## 监控和告警

建议配置：
- 在 Airflow 中设置 DAG 失败告警
- 定期检查 DAG 运行历史
- 监控 Teams 通知接收情况

## 自定义扩展

### 添加更多监控指标

在 `monitor_vertex_ai_pipelines` 函数中添加：

```python
pipeline_info = {
    'name': job.display_name,
    'url': job.url,
    'cpu_usage': job.metrics.get('cpu_usage'),  # 添加自定义指标
    'memory_usage': job.metrics.get('memory_usage'),
}
```

### 添加邮件通知

安装 `sendgrid` 并添加邮件发送任务：

```python
from airflow.providers.sendgrid.operators.sendgrid import SendGridOperator

notify_email_task = SendGridOperator(
    task_id='send_email_notification',
    # ... 配置参数
)
```

## 许可证

本项目仅供学习和参考使用。

## 联系方式

如有问题或建议，请联系相关团队。

