# 📑 项目文档索引

欢迎使用GPU服务器CICD - AWS MWAA解决方案！

## 🎯 我该从哪里开始？

### 👋 新用户
1. **快速了解** → [README.md](README.md) - 项目概述和功能特性
2. **快速部署** → [QUICKSTART.md](QUICKSTART.md) - 10分钟快速开始
3. **查看示例** → [examples/](examples/) - 实际使用示例

### 🔧 部署人员
1. **环境配置** → [MWAA_SETUP.md](MWAA_SETUP.md) - 完整的MWAA环境设置
2. **部署脚本** → [deploy.ps1](deploy.ps1) / [deploy.sh](deploy.sh) - 自动化部署
3. **本地测试** → [test_local.py](test_local.py) - 部署前测试工具

### 🏗️ 架构师
1. **系统架构** → [ARCHITECTURE.md](ARCHITECTURE.md) - 完整架构说明
2. **安全设计** → [README.md#安全最佳实践](README.md#安全最佳实践)
3. **组件说明** → [ARCHITECTURE.md#组件说明](ARCHITECTURE.md#组件说明)

### 💻 开发人员
1. **DAG源码** → [dags/gpu_server_cicd_dag.py](dags/gpu_server_cicd_dag.py)
2. **工具模块** → [plugins/](plugins/) - SSH和AWS工具
3. **配置文件** → [config/config.yaml](config/config.yaml)

## 📚 完整文档列表

### 核心文档

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [README.md](README.md) | 项目概述、功能特性、使用指南 | 所有人 |
| [QUICKSTART.md](QUICKSTART.md) | 10分钟快速开始指南 | 新用户 |
| [MWAA_SETUP.md](MWAA_SETUP.md) | AWS MWAA环境完整配置指南 | 部署人员 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构设计文档 | 架构师、开发者 |

### 代码文件

| 文件 | 说明 | 类型 |
|------|------|------|
| `dags/gpu_server_cicd_dag.py` | 主DAG定义 | Python |
| `plugins/gpu_ssh_utils.py` | SSH连接工具类 | Python |
| `plugins/aws_secrets_utils.py` | AWS Secrets Manager工具 | Python |
| `plugins/__init__.py` | 插件包初始化 | Python |

### 配置文件

| 文件 | 说明 | 格式 |
|------|------|------|
| `requirements.txt` | Python依赖 | Text |
| `config/config.yaml` | 应用配置 | YAML |
| `.gitignore` | Git忽略规则 | Text |

### 部署工具

| 文件 | 说明 | 平台 |
|------|------|------|
| `deploy.ps1` | PowerShell部署脚本 | Windows |
| `deploy.sh` | Bash部署脚本 | Linux/Mac |
| `test_local.py` | 本地测试工具 | 跨平台 |

### 示例文件

| 文件 | 说明 |
|------|------|
| `examples/example_trigger.json` | DAG触发配置示例 |
| `examples/version.yaml` | 版本文件格式示例 |
| `examples/README.md` | 示例说明文档 |

## 🗂️ 项目目录结构

```
airflow_aws/
│
├── 📄 README.md                    # 项目主文档
├── 📄 QUICKSTART.md                # 快速开始指南
├── 📄 MWAA_SETUP.md                # MWAA配置指南
├── 📄 ARCHITECTURE.md              # 架构设计文档
├── 📄 INDEX.md                     # 本文件
│
├── 📄 requirements.txt             # Python依赖
├── 📄 .gitignore                   # Git忽略规则
│
├── 🔧 deploy.ps1                   # Windows部署脚本
├── 🔧 deploy.sh                    # Linux/Mac部署脚本
├── 🔧 test_local.py                # 本地测试工具
│
├── 📁 dags/                        # Airflow DAG目录
│   └── 📄 gpu_server_cicd_dag.py  # 主DAG文件
│
├── 📁 plugins/                     # Airflow插件目录
│   ├── 📄 __init__.py              # 插件初始化
│   ├── 📄 gpu_ssh_utils.py         # SSH工具模块
│   └── 📄 aws_secrets_utils.py     # AWS Secrets工具
│
├── 📁 config/                      # 配置文件目录
│   └── 📄 config.yaml              # 应用配置
│
└── 📁 examples/                    # 示例文件目录
    ├── 📄 README.md                # 示例说明
    ├── 📄 example_trigger.json     # 触发配置示例
    └── 📄 version.yaml             # 版本文件示例
```

## 🔍 按场景查找文档

### 场景1: 我想快速部署并运行
```
1. QUICKSTART.md - 了解快速部署步骤
2. deploy.ps1/deploy.sh - 运行部署脚本
3. examples/example_trigger.json - 查看触发示例
```

### 场景2: 我需要从零配置MWAA环境
```
1. MWAA_SETUP.md - 完整配置指南
2. ARCHITECTURE.md - 理解架构设计
3. README.md#安全最佳实践 - 安全配置
```

### 场景3: 我想了解代码实现
```
1. dags/gpu_server_cicd_dag.py - DAG主逻辑
2. plugins/gpu_ssh_utils.py - SSH连接实现
3. plugins/aws_secrets_utils.py - Secrets Manager集成
4. ARCHITECTURE.md - 架构设计思路
```

### 场景4: 我遇到了问题
```
1. README.md#故障排查 - 常见问题解决
2. MWAA_SETUP.md#故障排查 - 环境配置问题
3. test_local.py - 本地调试工具
4. examples/README.md - 示例参考
```

### 场景5: 我想扩展功能
```
1. ARCHITECTURE.md#扩展架构 - 扩展方案
2. dags/gpu_server_cicd_dag.py - 参考现有实现
3. config/config.yaml - 配置扩展
```

## 📖 阅读顺序建议

### 快速路径（30分钟）
```
README.md (概览) 
    ↓
QUICKSTART.md (快速开始)
    ↓
examples/README.md (示例)
    ↓
开始使用！
```

### 完整路径（2小时）
```
README.md (项目概述)
    ↓
ARCHITECTURE.md (理解架构)
    ↓
MWAA_SETUP.md (环境配置)
    ↓
QUICKSTART.md (快速部署)
    ↓
代码文件 (深入实现)
    ↓
examples/ (实践示例)
```

### 运维路径
```
MWAA_SETUP.md (环境搭建)
    ↓
deploy.ps1/sh (部署脚本)
    ↓
README.md#监控和日志 (运维管理)
    ↓
README.md#故障排查 (问题解决)
```

## 🔗 快速链接

### 文档
- [项目概述](README.md)
- [快速开始](QUICKSTART.md)
- [环境配置](MWAA_SETUP.md)
- [架构设计](ARCHITECTURE.md)

### 代码
- [主DAG](dags/gpu_server_cicd_dag.py)
- [SSH工具](plugins/gpu_ssh_utils.py)
- [AWS工具](plugins/aws_secrets_utils.py)
- [配置文件](config/config.yaml)

### 工具
- [部署脚本(Win)](deploy.ps1)
- [部署脚本(Unix)](deploy.sh)
- [测试工具](test_local.py)

### 示例
- [触发配置](examples/example_trigger.json)
- [版本文件](examples/version.yaml)
- [示例说明](examples/README.md)

## 💡 提示

- 📌 使用 Ctrl+F 在本页面快速查找
- 🔖 建议收藏常用文档
- 📝 遇到问题先查看故障排查章节
- 🧪 部署前使用 test_local.py 测试
- 📊 部署后检查CloudWatch日志

## 🆘 需要帮助？

1. **查看文档** - 95%的问题都能在文档中找到答案
2. **运行测试** - 使用 test_local.py 定位问题
3. **查看日志** - CloudWatch日志提供详细信息
4. **检查配置** - 验证IAM权限和网络配置

---

**开始探索吧！** 🚀

