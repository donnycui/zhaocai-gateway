#!/bin/bash
set -e

echo "=========================================="
echo "Zhaocai Gateway 部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python 版本
echo -e "${YELLOW}[1/6] 检查 Python 版本...${NC}"
python_version=$(python3 --version 2>/dev/null || python --version 2>/dev/null)
if [[ $python_version != *"3."* ]]; then
    echo -e "${RED}错误: 需要 Python 3.9+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 版本: $python_version${NC}"

# 创建虚拟环境
echo -e "${YELLOW}[2/6] 创建虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv 2>/dev/null || python -m venv venv
    echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
else
    echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
fi

# 激活虚拟环境
echo -e "${YELLOW}[3/6] 激活虚拟环境并安装依赖...${NC}"
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# 生成加密密钥
echo -e "${YELLOW}[4/6] 生成配置文件...${NC}"
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ADMIN_TOKEN="admin-$(openssl rand -hex 16 2>/dev/null || python -c "import secrets; print(secrets.token_hex(16))")"

# 创建 .env 文件（如果不存在）
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Gateway runtime
ZHAOCAI_PORT=8000
ZHAOCAI_HOST=0.0.0.0
ZHAOCAI_LOG_LEVEL=info
ZHAOCAI_CONFIG=./config.yaml

# Control plane
ZHAOCAI_ADMIN_TOKEN=$ADMIN_TOKEN
ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db
ZHAOCAI_ENCRYPTION_KEY=$ENCRYPTION_KEY

# AI Provider API keys (请填入你的实际 API Key)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
NVIDIA_API_KEY=
DASHSCOPE_API_KEY=
SILICONFLOW_API_KEY=
OPENROUTER_API_KEY=

# Cloudflare tunnel token (optional)
CF_TUNNEL_TOKEN=
EOF
    echo -e "${GREEN}✓ .env 文件已创建${NC}"
else
    echo -e "${YELLOW}! .env 文件已存在，跳过创建${NC}"
fi

# 创建 config.yaml（如果不存在）
if [ ! -f "config.yaml" ]; then
    cp config.example.yaml config.yaml
    echo -e "${GREEN}✓ config.yaml 已创建${NC}"
else
    echo -e "${YELLOW}! config.yaml 已存在，跳过创建${NC}"
fi

# 创建数据目录
mkdir -p data
echo -e "${GREEN}✓ 数据目录已创建${NC}"

# 显示配置信息
echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${YELLOW}重要信息：${NC}"
echo -e "  Admin Token: ${GREEN}$ADMIN_TOKEN${NC}"
echo -e "  加密密钥: ${GREEN}$ENCRYPTION_KEY${NC}"
echo ""
echo -e "${YELLOW}下一步：${NC}"
echo "  1. 编辑 .env 文件，填入你的 API Key"
echo "  2. 编辑 config.yaml，配置 Provider（可选）"
echo "  3. 运行: source venv/bin/activate && python gateway.py"
echo ""
echo -e "${YELLOW}访问地址：${NC}"
echo "  - API 文档: http://localhost:8000/docs"
echo "  - 控制面板: http://localhost:8000/control"
echo "  - 健康检查: http://localhost:8000/health"
echo ""
