# 脚本分析文档

> **使用说明**: 请在本文档中标注你的修改需求，我会根据你的标注来修改代码。
> 
> 标注格式建议：
> - `[修改]` - 需要修改的功能
> - `[新增]` - 需要新增的功能  
> - `[删除]` - 需要删除的功能
> - `[问题]` - 发现的问题或疑问

---

## 一、脚本总览

| 脚本名称 | 功能定位 | 依赖关系 |
|---------|---------|---------|
| `file_related.py` | 数据采集 - 扫描目录并存入数据库 | 独立运行，输出 SQLite 数据库 |
| `file_related_process.py` | 数据检查 - 从数据库读取并检查问题 | 依赖 `file_related.py` 生成的数据库 |
| `image_related_process_for_anoti.py` | 图片相似度检测 | 独立运行 |
| `image_load_check.py` | 图片完整性检测 | 独立运行 |

### 数据流图
```
[目录扫描]                    [图片处理]
    │                            │
    ▼                            ▼
file_related.py          image_related_process_for_anoti.py
    │                            │
    ▼                            ▼
camera_file_summary.db    similar_images.csv/html
    │                            
    ▼                        image_load_check.py
file_related_process.py          │
    │                            ▼
    ▼                    corruption_detection_results.csv
ng_list.csv
```

---

## 二、各脚本详细分析

---

### 2.1 file_related.py（数据采集脚本）

#### 功能描述
扫描指定目录下的相机数据文件（.json, .png, _label.png），提取元数据并存入 SQLite 数据库。

#### 核心函数
| 函数名 | 功能 | 参数 |
|-------|------|------|
| `scan_camera_directory_to_db()` | 主函数，扫描目录并写入数据库 | `base_path`, `db_path`, `batch_size=10` |

#### 数据库表结构 (camera_files)
| 字段名 | 类型 | 说明 |
|-------|------|------|
| filename | TEXT | 文件基础名（不含扩展名） |
| file_path | TEXT | 文件所在目录路径 |
| set_content | TEXT | JSON数组，包含的文件类型 ["json", "png", "label"] |
| Manufacturer | TEXT | 制造商 |
| MakeDate | TEXT | 制作日期 |
| imgType | TEXT | 图像类型 |
| CameraType | TEXT | 相机类型 |
| AssessmentData | BOOLEAN | 评估数据标志 |
| TestCourseData | BOOLEAN | 测试数据标志 |
| ColorFilter | TEXT | 颜色滤镜 |
| CarType | TEXT | 车辆类型 |
| Pattern | TEXT | 标注模式 |
| SemsegType | TEXT | 语义分割类型 |
| SingleAnotation | TEXT | 单一标注 |
| ng_list | TEXT | JSON数组，问题列表 |

#### 当前配置
```python
directory_list = [
    "//172.22.193.201/share/learning_data/frame/main/full/camera/Ver4/2019/A",
    "//172.22.193.201/share/learning_data/frame/main/full/camera/Ver4/2019/B",
    "//172.22.193.201/share/learning_data/frame/main/full/camera/Ver4/2020_1st/A",
    "//172.22.193.201/share/learning_data/frame/main/full/camera/Ver4/2020_2nd/A",
    "//172.22.193.201/share/learning_data/frame/main/full/camera/Ver5/2024_2nd/C",
]
db_path = "camera_file_summary.db"
batch_size = 10
```

#### 已识别的问题/可优化点
| 编号 | 问题描述 | 优先级 | 你的意见 |
|-----|---------|-------|---------|
| F1-1 | 每次运行会追加数据，不会清理旧数据，可能导致重复 | 高 | |
| F1-2 | 缺少命令行参数支持，目录写死在代码中 | 中 | |
| F1-3 | batch_size=10 偏小，大量数据时效率低 | 低 | |
| F1-4 | 缺少错误统计和汇总报告 | 中 | |
| F1-5 | 没有支持增量扫描（跳过已处理的文件） | 中 | |
| F1-6 | 只支持 .json/.png 文件，不支持其他格式 | 低 | |

#### 建议新增功能
| 编号 | 功能描述 | 你的意见 |
|-----|---------|---------|
| F1-N1 | 添加 `--clear` 参数，运行前清空表 | |
| F1-N2 | 添加命令行参数 `--dir` 和 `--db` | |
| F1-N3 | 添加扫描完成后的统计报告 | |
| F1-N4 | 支持配置文件 (YAML/JSON) 读取目录列表 | |

---

### 2.2 file_related_process.py（数据检查脚本）

#### 功能描述
从数据库读取文件记录，执行多项检查规则，将有问题的记录输出到 CSV。

#### 核心类
**CameraFileChecker**
| 方法名 | 功能 |
|-------|------|
| `__init__()` | 初始化，解析数据库行 |
| `check_set_content_length()` | 检查 set_content 是否少于3项 |
| `check_filename_cut()` | 检查文件名是否包含下划线 |
| `check_illegal_keywords()` | 检查文件名是否包含非法关键词 |
| `print_entry()` | 打印详细信息（调试用） |

#### 当前检查规则
| 规则 | 检查内容 | 错误标记 |
|-----|---------|---------|
| 规则1 | set_content 数量 < 3（缺少文件） | `set_content < 3` |
| 规则2 | 文件名包含下划线 `_` | `filename_cut` |
| 规则3 | 文件名包含非法关键词 | `illegal_filename` |

#### 当前配置
```python
illegal_keywords = ["luanbo", "miyano", "sample"]
db_path = "camera_file_summary.db"  # 硬编码
output_csv = "ng_list.csv"  # 硬编码
```

#### 已识别的问题/可优化点
| 编号 | 问题描述 | 优先级 | 你的意见 |
|-----|---------|-------|---------|
| F2-1 | 数据库路径和输出路径硬编码 | 高 | |
| F2-2 | 非法关键词列表硬编码，不易维护 | 中 | |
| F2-3 | 检查规则固定，无法动态配置 | 中 | |
| F2-4 | 缺少统计信息（总数、问题数、各类型数量） | 中 | |
| F2-5 | CSV输出的ng_item列数不固定，不便后续处理 | 低 | |
| F2-6 | 主程序代码没有封装到函数中 | 低 | |

#### 建议新增功能
| 编号 | 功能描述 | 你的意见 |
|-----|---------|---------|
| F2-N1 | 支持命令行参数配置 | |
| F2-N2 | 支持从配置文件读取非法关键词 | |
| F2-N3 | 添加更多检查规则（可扩展） | |
| F2-N4 | 输出统计报告 | |
| F2-N5 | 支持按问题类型分类输出 | |

---

### 2.3 image_related_process_for_anoti.py（相似图片检测）

#### 功能描述
使用 pHash + ORB 双重算法检测相似图片，输出 CSV 和 HTML 报告。

#### 算法流程
```
1. 收集所有图片路径
       │
       ▼
2. 计算每张图片的 pHash
       │
       ▼
3. 两两比较 pHash，筛选候选对（distance <= threshold）
       │
       ▼
4. 对候选对进行 ORB 特征匹配验证
       │
       ▼
5. 输出结果（CSV + HTML）
```

#### 核心函数
| 函数名 | 功能 |
|-------|------|
| `compute_phash()` | 计算感知哈希 |
| `compute_orb_similarity()` | ORB 特征匹配计算相似度 |
| `generate_phash_pairs()` | 生成 pHash 候选对 |
| `filter_orb_matches()` | ORB 过滤验证 |
| `save_results_as_csv()` | 保存 CSV 结果 |
| `save_results_as_html_paginated()` | 保存分页 HTML 报告 |
| `run_pipeline()` | 主流程函数 |

#### 当前配置
```python
CONFIG = {
    "phash_threshold": 5,        # pHash 距离阈值
    "orb_min_matches": 30,       # ORB 最小匹配点数
    "orb_min_ratio": 0.15,       # 最小匹配比率
    "orb_max_avg_distance": 50,  # 最大平均距离
    "num_workers": 4,            # 工作线程数（未使用）
    "save_image_max": 10,        # 每个HTML页面最大图片数
    "check_image": "*.*"         # 图片匹配模式
}
CHUNK_SIZE = 1000
PHASH_SIZE = 200  # 进度日志间隔
```

#### 已识别的问题/可优化点
| 编号 | 问题描述 | 优先级 | 你的意见 |
|-----|---------|-------|---------|
| I1-1 | `apache_beam` 导入但未使用 | 低 | |
| I1-2 | `num_workers` 配置未实现多线程 | 高 | |
| I1-3 | 大量图片时，pHash两两比较是O(n²)复杂度 | 高 | |
| I1-4 | 缺少进度条显示 | 中 | |
| I1-5 | HTML报告分页文件命名不直观（001, 002...） | 低 | |
| I1-6 | `encode_image_base64` 函数定义了两次（全局+局部） | 低 | |
| I1-7 | 没有缓存机制，重复运行需要重新计算所有pHash | 中 | |

#### 建议新增功能
| 编号 | 功能描述 | 你的意见 |
|-----|---------|---------|
| I1-N1 | 实现多线程/多进程处理 | |
| I1-N2 | 添加 pHash 缓存（存入数据库或文件） | |
| I1-N3 | 添加 tqdm 进度条 | |
| I1-N4 | 支持命令行参数 | |
| I1-N5 | 优化算法，使用 VP-tree 或 BK-tree 加速相似查找 | |
| I1-N6 | 支持更多图片格式（jpg, bmp等） | |

---

### 2.4 image_load_check.py（图片完整性检测）

#### 功能描述
检测图片文件是否损坏/可加载，并可生成各种类型的损坏测试图片。

#### 核心函数
| 函数名 | 功能 |
|-------|------|
| `corruption_image_generator()` | 生成各种类型的损坏图片（用于测试） |
| `detect_corrupted_image_type()` | 检测单张图片是否可正常加载 |
| `main()` | 主函数，批量检测目录下的图片 |

#### 损坏类型生成器（用于测试）
| 函数名 | 损坏类型 | 描述 |
|-------|---------|------|
| `corrupt_header()` | 头部损坏 | PNG签名（前8字节）置零 |
| `corrupt_chunk()` | 块损坏 | 文件中央10字节覆写为0xFF |
| `corrupt_bit_level()` | 位级损坏 | 100-109字节位反转 |
| `corrupt_compression()` | 压缩数据损坏 | IDAT块数据覆写为0x00 |
| `corrupt_truncation()` | 截断损坏 | 删除末尾100字节 |
| `corrupt_random_bytes()` | 随机字节插入 | 在1/3处插入20个随机字节 |

#### 当前配置
```python
image_dir_list = [
    "D:/workspac_luan/Tasks/20250520_Data",
    r"Z://AI_dataset_image/Ver4_rev2/2023_1st/C",
]
output_csv = "{image_dir}/corruption_detection_results.csv"
```

#### 已识别的问题/可优化点
| 编号 | 问题描述 | 优先级 | 你的意见 |
|-----|---------|-------|---------|
| I2-1 | `corruption_image_generator` 函数未在主程序中调用 | 中 | |
| I2-2 | 只支持 PNG 格式检测 | 中 | |
| I2-3 | 使用 `verify()` 检测可能漏检某些损坏类型 | 中 | |
| I2-4 | 缺少更详细的错误分类 | 低 | |
| I2-5 | 目录路径硬编码 | 中 | |
| I2-6 | 没有递归扫描子目录 | 低 | |
| I2-7 | `math` 和 `random` 导入但主程序未使用 | 低 | |

#### 建议新增功能
| 编号 | 功能描述 | 你的意见 |
|-----|---------|---------|
| I2-N1 | 支持命令行参数 | |
| I2-N2 | 支持更多图片格式 (jpg, bmp, tiff) | |
| I2-N3 | 添加 `load()` 检测（比 verify 更彻底） | |
| I2-N4 | 支持递归扫描子目录 | |
| I2-N5 | 添加错误类型分类统计 | |
| I2-N6 | 支持将损坏图片移动/复制到指定目录 | |

---

## 三、跨脚本问题与建议

### 3.1 共性问题
| 编号 | 问题描述 | 涉及脚本 | 你的意见 |
|-----|---------|---------|---------|
| G-1 | 路径配置均为硬编码 | 全部 | |
| G-2 | 缺少统一的配置管理 | 全部 | |
| G-3 | 缺少统一的日志框架 | 部分 | |
| G-4 | 没有错误处理的统一标准 | 全部 | |
| G-5 | 缺少单元测试 | 全部 | |

### 3.2 架构优化建议
| 编号 | 建议 | 你的意见 |
|-----|------|---------|
| A-1 | 创建统一的配置文件 (config.yaml) | |
| A-2 | 创建共用的工具模块 (utils.py) | |
| A-3 | 添加主入口脚本，整合所有功能 | |
| A-4 | 使用 argparse 统一命令行接口 | |
| A-5 | 添加日志配置模块 | |

---

## 四、你的修改需求

> 请在下面添加你的具体修改需求，我会根据你的需求来修改代码。

### 4.1 需要修改的功能
```
（请在这里描述需要修改的功能）

例如：
- [修改] F1-1: 添加 --clear 参数，在插入前清空表
- [修改] I1-2: 实现多线程处理

```

### 4.2 需要新增的功能
```
（请在这里描述需要新增的功能）

例如：
- [新增] 统一配置文件
- [新增] 添加 tqdm 进度条

```

### 4.3 需要删除的功能
```
（请在这里描述需要删除的功能）

例如：
- [删除] apache_beam 相关导入

```

### 4.4 其他备注
```
（请在这里添加其他说明或问题）

```

---

## 五、版本记录

| 版本 | 日期 | 修改内容 |
|-----|------|---------|
| v1.0 | 2025-12-08 | 初始分析文档 |

