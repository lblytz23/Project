# 🚀 5分钟快速开始

## 第1步：安装依赖 (30秒)

```bash
cd demo_v01
pip install -r requirements_v01.txt
```

## 第2步：初始化 (10秒)

```bash
python cli_v01.py --init
```

## 第3步：查看状态 (5秒)

```bash
python cli_v01.py --status
```

## 第4步：分配资源 (5秒)

```bash
python cli_v01.py --allocate my_first_task 4 32
```

## 第5步：查看变化 (5秒)

```bash
python cli_v01.py --status
```

## 第6步：释放资源 (5秒)

```bash
python cli_v01.py --release my_first_task
```

## 🎉 完成！

你已经掌握了基本用法！

---

## 下一步

### 运行完整演示
```bash
python demo_example.py
```

### 运行测试
```bash
python test_v01.py
```

### 阅读文档
```bash
cat README_v01.md
```

---

## 常用命令速查

```bash
# 查看状态
python cli_v01.py --status

# 查看详情
python cli_v01.py --detail

# 分配资源 (任务ID GPU数量 CPU数量)
python cli_v01.py --allocate <task_id> <gpus> <cpus>

# 释放资源
python cli_v01.py --release <task_id>

# 重置系统
python cli_v01.py --reset
```

---

**准备好进入v0.2了吗？** 🎯

查看 `迭代开发计划.md` 了解下一步！

