# 示例文件说明

## example_trigger.json

这是一个示例的DAG触发配置文件，展示了如何通过API或CLI触发DAG。

### 使用方法

**1. 通过Airflow CLI触发：**

```bash
airflow dags trigger gpu_server_cicd_workflow \
    --conf "$(cat examples/example_trigger.json | jq '.conf')"
```

**2. 通过AWS MWAA CLI触发：**

```bash
aws mwaa create-cli-token --name your-mwaa-environment-name \
    --region us-east-1 \
    | jq -r '.CliToken' \
    | xargs -I {} curl -X POST \
    "https://your-mwaa-webserver-url/api/v1/dags/gpu_server_cicd_workflow/dagRuns" \
    -H "Authorization: Bearer {}" \
    -H "Content-Type: application/json" \
    -d @examples/example_trigger.json
```

**3. 使用Python SDK：**

```python
import boto3
import json

# 加载配置
with open('examples/example_trigger.json', 'r') as f:
    config = json.load(f)

# 触发DAG（需要使用MWAA的REST API）
# 详见AWS文档
```

### 配置参数说明

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| gpu_server_ip | 是 | GPU服务器IP地址 | 10.0.1.100 |
| workspace_path | 是 | GPU服务器上的工作目录 | /home/ubuntu/workspace |
| secrets_arn | 是 | SSH密钥的Secrets Manager ARN | arn:aws:secretsmanager:... |
| git_repo_url | 否 | Git仓库URL（有默认值） | https://github.com/... |
| git_branch | 否 | Git分支名（有默认值） | cicd_01_etl |
| version_file_path | 否 | 版本文件相对路径（有默认值） | www/version.yaml |

## version.yaml

这是一个示例的版本文件，展示了DAG期望读取的文件格式。

### 文件位置

该文件应该存在于Git仓库中的指定路径（默认是 `www/version.yaml`）。

### 格式要求

- 必须是有效的YAML格式
- 包含键值对，值可以是数字或字符串
- 所有的键都会被更新到Airflow Variables中

### 示例

```yaml
a: 10.0
b: 10.0
c: 10.0
d: 10.0
```

### 访问更新后的变量

在其他DAG中访问这些变量：

```python
from airflow.models import Variable

# 读取变量
version_a = Variable.get("a")
version_b = Variable.get("b", default_var="1.0")

# 在模板中使用
"{{ var.value.a }}"
"{{ var.json.my_dict_var.key }}"
```

## 其他示例

### 通过Airflow UI手动触发

1. 登录Airflow Web界面
2. 找到 `gpu_server_cicd_workflow` DAG
3. 点击"Trigger DAG"
4. 在弹出的表单中输入参数（参考example_trigger.json中的值）
5. 点击"Trigger"

### 定时触发

如果需要定时执行，可以在DAG定义中修改 `schedule_interval`：

```python
# 每天凌晨2点执行
schedule_interval="0 2 * * *"

# 每周一执行
schedule_interval="0 0 * * 1"

# 使用cron表达式
schedule_interval="*/30 * * * *"  # 每30分钟
```

### 条件触发

可以使用 `TriggerDagRunOperator` 从其他DAG触发：

```python
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

trigger = TriggerDagRunOperator(
    task_id='trigger_gpu_cicd',
    trigger_dag_id='gpu_server_cicd_workflow',
    conf={
        'gpu_server_ip': '10.0.1.100',
        'workspace_path': '/home/ubuntu/workspace',
        'secrets_arn': 'arn:aws:...'
    }
)
```

