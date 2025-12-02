# 快速安装指南

## 🚀 一键安装脚本（推荐）

### Windows PowerShell 脚本

将以下内容保存为 `install.ps1`，然后右键"以管理员身份运行 PowerShell"执行：

```powershell
# 检查 Python
Write-Host "检查 Python..." -ForegroundColor Cyan
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 安装 Python 依赖
Write-Host "`n安装 Python 依赖包..." -ForegroundColor Cyan
pip install pyautogui Pillow opencv-python numpy

# 尝试安装 PyAudio
Write-Host "`n安装 PyAudio..." -ForegroundColor Cyan
pip install PyAudio
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ PyAudio 安装失败，请手动从以下地址下载 wheel 文件：" -ForegroundColor Yellow
    Write-Host "https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio" -ForegroundColor Yellow
}

# 检查 ffmpeg
Write-Host "`n检查 ffmpeg..." -ForegroundColor Cyan
ffmpeg -version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未找到 ffmpeg" -ForegroundColor Red
    Write-Host "请选择安装方式：" -ForegroundColor Yellow
    Write-Host "1. 使用 Chocolatey 安装（推荐）：choco install ffmpeg" -ForegroundColor Yellow
    Write-Host "2. 手动下载安装：https://ffmpeg.org/download.html" -ForegroundColor Yellow
    
    $choice = Read-Host "`n是否使用 Chocolatey 安装 ffmpeg? (y/n)"
    if ($choice -eq 'y') {
        # 检查 Chocolatey
        choco --version 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "安装 Chocolatey..." -ForegroundColor Cyan
            Set-ExecutionPolicy Bypass -Scope Process -Force
            [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
            iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        }
        
        Write-Host "安装 ffmpeg..." -ForegroundColor Cyan
        choco install ffmpeg -y
    }
} else {
    Write-Host "✅ ffmpeg 已安装" -ForegroundColor Green
}

Write-Host "`n✅ 安装完成！" -ForegroundColor Green
Write-Host "运行程序：python screen_recorder.py" -ForegroundColor Cyan
```

## 📝 手动安装步骤

### 步骤 1：Python 依赖

```bash
pip install pyautogui Pillow opencv-python numpy
```

### 步骤 2：PyAudio（重要）

#### Windows 用户

**选项 A：直接安装（推荐先尝试）**
```bash
pip install PyAudio
```

**选项 B：从 wheel 文件安装**

如果选项 A 失败：

1. 访问：https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
2. 下载对应版本的 `.whl` 文件
   
   **如何选择版本？**
   - 查看你的 Python 版本：`python --version`
   - 查看系统架构：在命令提示符输入 `echo %PROCESSOR_ARCHITECTURE%`
   
   **文件名示例：**
   - `PyAudio-0.2.14-cp311-cp311-win_amd64.whl`
     - `cp311` = Python 3.11
     - `win_amd64` = Windows 64位
   
   - `PyAudio-0.2.14-cp310-cp310-win_amd64.whl`
     - `cp310` = Python 3.10
     - `win_amd64` = Windows 64位

3. 安装下载的文件：
   ```bash
   cd 下载文件夹路径
   pip install PyAudio-0.2.14-cpXXX-cpXXX-win_amd64.whl
   ```

### 步骤 3：ffmpeg

#### 方法一：Chocolatey（最简单）

```bash
# 1. 以管理员身份打开 PowerShell
# 2. 如果没有 Chocolatey，先安装它：
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 3. 安装 ffmpeg
choco install ffmpeg -y
```

#### 方法二：手动安装

1. **下载 ffmpeg**
   - 访问：https://ffmpeg.org/download.html
   - 点击 Windows 图标
   - 选择 "Windows builds from gyan.dev"
   - 下载 "ffmpeg-release-essentials.zip"

2. **解压文件**
   - 解压到 `C:\ffmpeg`（或任意位置）

3. **添加到 PATH**
   
   **图形界面方式：**
   - 右键"此电脑" → "属性"
   - 点击"高级系统设置"
   - 点击"环境变量"
   - 在"系统变量"区域找到"Path"，双击
   - 点击"新建"
   - 输入：`C:\ffmpeg\bin`（或你的实际路径）
   - 一路点击"确定"保存
   
   **命令行方式（管理员 PowerShell）：**
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\ffmpeg\bin", "Machine")
   ```

4. **验证安装**
   - 关闭并重新打开命令提示符
   - 输入：`ffmpeg -version`
   - 应该看到版本信息

## ✅ 验证安装

运行以下命令验证所有组件：

```bash
# 验证 Python 包
python -c "import cv2, pyaudio, pyautogui, PIL; print('✅ 所有 Python 包安装成功')"

# 验证 ffmpeg
ffmpeg -version
```

如果都没有错误，说明安装成功！

## 🎯 快速测试

```bash
# 运行程序
python screen_recorder.py

# 点击"开始录制"，录制几秒后点击"停止录制"
# 检查是否生成 MP4 文件
```

## ❓ 常见问题

### Q1：pip 命令不可用
**A**：确保 Python 已添加到 PATH，或使用：
```bash
python -m pip install <package_name>
```

### Q2：PyAudio 一直安装失败
**A**：必须使用 wheel 文件安装（见步骤 2 选项 B）

### Q3：ffmpeg 命令找不到
**A**：
1. 确认 ffmpeg 已解压到正确位置
2. 确认 bin 目录已添加到 PATH
3. **重启命令提示符**（重要！）

### Q4：提示缺少某个 DLL
**A**：安装 Microsoft Visual C++ Redistributable
- 下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe

## 📞 需要帮助？

如果遇到问题：

1. 查看完整的 README.md 文档
2. 确保所有依赖都正确安装
3. 检查 Python 版本（需要 3.8+）
4. 检查系统是否为 64 位

---

**准备就绪后，运行 `python screen_recorder.py` 开始使用！** 🎬

