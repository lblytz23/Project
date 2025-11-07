#!/bin/bash
# MWAA部署脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 配置变量
MWAA_BUCKET="your-mwaa-bucket"
AWS_REGION="us-east-1"
MWAA_ENV_NAME="your-mwaa-environment"

echo -e "${YELLOW}=== MWAA DAG部署脚本 ===${NC}"

# 检查必要的工具
command -v aws >/dev/null 2>&1 || { echo -e "${RED}错误: 需要安装AWS CLI${NC}" >&2; exit 1; }
command -v zip >/dev/null 2>&1 || { echo -e "${RED}错误: 需要安装zip${NC}" >&2; exit 1; }

# 获取用户输入
read -p "请输入MWAA S3桶名称 [${MWAA_BUCKET}]: " input_bucket
MWAA_BUCKET=${input_bucket:-$MWAA_BUCKET}

read -p "请输入AWS区域 [${AWS_REGION}]: " input_region
AWS_REGION=${input_region:-$AWS_REGION}

echo -e "${GREEN}开始部署...${NC}"

# 1. 上传DAG文件
echo -e "${YELLOW}[1/4] 上传DAG文件...${NC}"
aws s3 cp dags/gpu_server_cicd_dag.py "s3://${MWAA_BUCKET}/dags/" --region ${AWS_REGION}
echo -e "${GREEN}✓ DAG文件上传完成${NC}"

# 2. 打包并上传插件
echo -e "${YELLOW}[2/4] 打包插件...${NC}"
cd plugins
zip -r ../plugins.zip . -x "*.pyc" -x "__pycache__/*"
cd ..
echo -e "${GREEN}✓ 插件打包完成${NC}"

echo -e "${YELLOW}[2/4] 上传插件...${NC}"
aws s3 cp plugins.zip "s3://${MWAA_BUCKET}/plugins/" --region ${AWS_REGION}
echo -e "${GREEN}✓ 插件上传完成${NC}"

# 3. 上传requirements.txt
echo -e "${YELLOW}[3/4] 上传依赖文件...${NC}"
aws s3 cp requirements.txt "s3://${MWAA_BUCKET}/" --region ${AWS_REGION}
echo -e "${GREEN}✓ 依赖文件上传完成${NC}"

# 4. 上传配置文件（可选）
echo -e "${YELLOW}[4/4] 上传配置文件...${NC}"
aws s3 cp config/config.yaml "s3://${MWAA_BUCKET}/config/" --region ${AWS_REGION}
echo -e "${GREEN}✓ 配置文件上传完成${NC}"

# 清理临时文件
echo -e "${YELLOW}清理临时文件...${NC}"
rm -f plugins.zip
echo -e "${GREEN}✓ 清理完成${NC}"

echo ""
echo -e "${GREEN}=== 部署完成! ===${NC}"
echo ""
echo -e "${YELLOW}注意事项:${NC}"
echo "1. 请在MWAA环境中更新requirements.txt路径为: s3://${MWAA_BUCKET}/requirements.txt"
echo "2. 请在MWAA环境中更新plugins.zip路径为: s3://${MWAA_BUCKET}/plugins/plugins.zip"
echo "3. 更新后MWAA需要几分钟时间重新加载DAG"
echo "4. 确保MWAA执行角色有Secrets Manager的访问权限"
echo ""
echo -e "${YELLOW}查看部署状态:${NC}"
echo "aws mwaa get-environment --name ${MWAA_ENV_NAME} --region ${AWS_REGION}"
echo ""
echo -e "${YELLOW}访问Airflow UI:${NC}"
echo "aws mwaa create-web-login-token --name ${MWAA_ENV_NAME} --region ${AWS_REGION}"

