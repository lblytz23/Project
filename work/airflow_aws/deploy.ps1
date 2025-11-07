# MWAA部署脚本 (PowerShell版本)

param(
    [string]$MwaaBucket = "your-mwaa-bucket",
    [string]$AwsRegion = "us-east-1",
    [string]$MwaaEnvName = "your-mwaa-environment"
)

Write-Host "=== MWAA DAG部署脚本 ===" -ForegroundColor Yellow

# 检查AWS CLI
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 需要安装AWS CLI" -ForegroundColor Red
    exit 1
}

# 获取用户输入
$InputBucket = Read-Host "请输入MWAA S3桶名称 [$MwaaBucket]"
if ($InputBucket) { $MwaaBucket = $InputBucket }

$InputRegion = Read-Host "请输入AWS区域 [$AwsRegion]"
if ($InputRegion) { $AwsRegion = $InputRegion }

Write-Host "开始部署..." -ForegroundColor Green

# 1. 上传DAG文件
Write-Host "[1/4] 上传DAG文件..." -ForegroundColor Yellow
aws s3 cp dags/gpu_server_cicd_dag.py "s3://$MwaaBucket/dags/" --region $AwsRegion
Write-Host "✓ DAG文件上传完成" -ForegroundColor Green

# 2. 打包并上传插件
Write-Host "[2/4] 打包插件..." -ForegroundColor Yellow
Push-Location plugins
Compress-Archive -Path * -DestinationPath ../plugins.zip -Force
Pop-Location
Write-Host "✓ 插件打包完成" -ForegroundColor Green

Write-Host "[2/4] 上传插件..." -ForegroundColor Yellow
aws s3 cp plugins.zip "s3://$MwaaBucket/plugins/" --region $AwsRegion
Write-Host "✓ 插件上传完成" -ForegroundColor Green

# 3. 上传requirements.txt
Write-Host "[3/4] 上传依赖文件..." -ForegroundColor Yellow
aws s3 cp requirements.txt "s3://$MwaaBucket/" --region $AwsRegion
Write-Host "✓ 依赖文件上传完成" -ForegroundColor Green

# 4. 上传配置文件
Write-Host "[4/4] 上传配置文件..." -ForegroundColor Yellow
aws s3 cp config/config.yaml "s3://$MwaaBucket/config/" --region $AwsRegion
Write-Host "✓ 配置文件上传完成" -ForegroundColor Green

# 清理临时文件
Write-Host "清理临时文件..." -ForegroundColor Yellow
Remove-Item plugins.zip -ErrorAction SilentlyContinue
Write-Host "✓ 清理完成" -ForegroundColor Green

Write-Host ""
Write-Host "=== 部署完成! ===" -ForegroundColor Green
Write-Host ""
Write-Host "注意事项:" -ForegroundColor Yellow
Write-Host "1. 请在MWAA环境中更新requirements.txt路径为: s3://$MwaaBucket/requirements.txt"
Write-Host "2. 请在MWAA环境中更新plugins.zip路径为: s3://$MwaaBucket/plugins/plugins.zip"
Write-Host "3. 更新后MWAA需要几分钟时间重新加载DAG"
Write-Host "4. 确保MWAA执行角色有Secrets Manager的访问权限"
Write-Host ""
Write-Host "查看部署状态:" -ForegroundColor Yellow
Write-Host "aws mwaa get-environment --name $MwaaEnvName --region $AwsRegion"
Write-Host ""
Write-Host "访问Airflow UI:" -ForegroundColor Yellow
Write-Host "aws mwaa create-web-login-token --name $MwaaEnvName --region $AwsRegion"

