# 屏幕录制软件 - 自动安装脚本
# 使用方法：右键"以管理员身份运行 PowerShell"，然后执行此脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  屏幕录制软件 - 自动安装脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/4] 检查 Python..." -ForegroundColor Yellow
python --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Write-Host "下载地址：https://www.python.org/downloads/" -ForegroundColor Yellow
    pause
    exit 1
}
$pythonVersion = python --version
Write-Host "✅ 找到 $pythonVersion" -ForegroundColor Green
Write-Host ""

# 安装 Python 依赖
Write-Host "[2/4] 安装 Python 依赖包..." -ForegroundColor Yellow
Write-Host "正在安装：pyautogui, Pillow, opencv-python, numpy..." -ForegroundColor Gray

$packages = @("pyautogui==0.9.54", "Pillow==10.1.0", "opencv-python==4.8.1.78", "numpy==1.24.3")
foreach ($package in $packages) {
    Write-Host "  安装 $package" -ForegroundColor Gray
    pip install $package --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $package 安装成功" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ $package 安装失败" -ForegroundColor Yellow
    }
}
Write-Host ""

# 尝试安装 PyAudio
Write-Host "[3/4] 安装 PyAudio..." -ForegroundColor Yellow
pip install PyAudio --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PyAudio 安装成功" -ForegroundColor Green
} else {
    Write-Host "⚠️ PyAudio 自动安装失败" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "PyAudio 需要手动安装，请按照以下步骤操作：" -ForegroundColor Cyan
    Write-Host "1. 访问：https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio" -ForegroundColor White
    Write-Host "2. 下载对应您 Python 版本的 .whl 文件" -ForegroundColor White
    Write-Host "3. 运行：pip install PyAudio-0.2.14-cpXXX-cpXXX-win_amd64.whl" -ForegroundColor White
    Write-Host ""
    Write-Host "提示：查看您的 Python 版本：$pythonVersion" -ForegroundColor Gray
}
Write-Host ""

# 检查 ffmpeg
Write-Host "[4/4] 检查 ffmpeg..." -ForegroundColor Yellow
ffmpeg -version 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ ffmpeg 已安装" -ForegroundColor Green
} else {
    Write-Host "❌ 未找到 ffmpeg" -ForegroundColor Red
    Write-Host ""
    Write-Host "ffmpeg 是必需的组件，用于合成视频" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "请选择安装方式：" -ForegroundColor Yellow
    Write-Host "1. 使用 Chocolatey 自动安装（推荐）" -ForegroundColor White
    Write-Host "2. 手动下载安装" -ForegroundColor White
    Write-Host "3. 跳过（稍后手动安装）" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "请输入选项 (1/2/3)"
    
    if ($choice -eq '1') {
        # 检查 Chocolatey
        choco --version 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "安装 Chocolatey..." -ForegroundColor Cyan
            try {
                Set-ExecutionPolicy Bypass -Scope Process -Force
                [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
                Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
                Write-Host "✅ Chocolatey 安装成功" -ForegroundColor Green
            } catch {
                Write-Host "❌ Chocolatey 安装失败：$_" -ForegroundColor Red
                Write-Host "请手动安装 ffmpeg" -ForegroundColor Yellow
                $choice = '2'
            }
        }
        
        if ($choice -eq '1') {
            Write-Host ""
            Write-Host "安装 ffmpeg..." -ForegroundColor Cyan
            choco install ffmpeg -y
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ ffmpeg 安装成功" -ForegroundColor Green
                Write-Host "⚠️ 请重启命令提示符以使 PATH 生效" -ForegroundColor Yellow
            } else {
                Write-Host "❌ ffmpeg 安装失败" -ForegroundColor Red
                $choice = '2'
            }
        }
    }
    
    if ($choice -eq '2') {
        Write-Host ""
        Write-Host "手动安装 ffmpeg 步骤：" -ForegroundColor Cyan
        Write-Host "1. 访问：https://ffmpeg.org/download.html" -ForegroundColor White
        Write-Host "2. 下载 Windows 版本（推荐 gyan.dev 构建）" -ForegroundColor White
        Write-Host "3. 解压到 C:\ffmpeg" -ForegroundColor White
        Write-Host "4. 添加到 PATH：" -ForegroundColor White
        Write-Host "   - 右键'此电脑' → '属性' → '高级系统设置' → '环境变量'" -ForegroundColor Gray
        Write-Host "   - 在'系统变量'中找到'Path'，添加 C:\ffmpeg\bin" -ForegroundColor Gray
        Write-Host "5. 重启命令提示符" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 验证安装
Write-Host "验证安装..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Python 包检查：" -ForegroundColor Cyan
$testScript = @"
try:
    import cv2
    import pyautogui
    import PIL
    print("✅ 核心包已安装")
    
    try:
        import pyaudio
        print("✅ PyAudio 已安装")
    except:
        print("⚠️ PyAudio 未安装（需要手动安装）")
except Exception as e:
    print(f"❌ 某些包缺失：{e}")
"@

python -c $testScript

Write-Host ""
Write-Host "ffmpeg 检查：" -ForegroundColor Cyan
ffmpeg -version 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ ffmpeg 可用" -ForegroundColor Green
} else {
    Write-Host "⚠️ ffmpeg 不可用（需要手动安装）" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. 如果 PyAudio 未安装，请按照提示手动安装" -ForegroundColor White
Write-Host "2. 如果 ffmpeg 未安装，请按照提示手动安装" -ForegroundColor White
Write-Host "3. 运行程序：python screen_recorder.py" -ForegroundColor White
Write-Host ""
Write-Host "详细文档：查看 README.md 和 install_guide.md" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

pause

