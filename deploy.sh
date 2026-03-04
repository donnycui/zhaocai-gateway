#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "Zhaocai Gateway bootstrap"
echo "=========================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[1/6] Check Python version...${NC}"
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo -e "${RED}Error: python is not installed${NC}"
  exit 1
fi

PY_VERSION="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
$PYTHON_BIN - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit(1)
PY
if [ $? -ne 0 ]; then
  echo -e "${RED}Error: Python 3.9+ is required${NC}"
  exit 1
fi
echo -e "${GREEN}OK Python version: $PY_VERSION${NC}"

echo -e "${YELLOW}[2/6] Create virtual environment...${NC}"
if [ ! -d "venv" ]; then
  $PYTHON_BIN -m venv venv
  echo -e "${GREEN}OK virtual environment created${NC}"
else
  echo -e "${GREEN}OK virtual environment already exists${NC}"
fi

echo -e "${YELLOW}[3/6] Activate virtual environment and install dependencies...${NC}"
if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  # shellcheck disable=SC1091
  source venv/Scripts/activate
fi
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}OK dependencies installed${NC}"

echo -e "${YELLOW}[4/6] Generate configuration files...${NC}"
ENCRYPTION_KEY="$(python - <<'PY'
try:
    from cryptography.fernet import Fernet
    print(Fernet.generate_key().decode())
except Exception:
    print("")
PY
)"
ADMIN_TOKEN="admin-$(python - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)"

if [ ! -f ".env" ]; then
  cat > .env <<EOF
# Gateway runtime
ZHAOCAI_PORT=8000
ZHAOCAI_HOST=0.0.0.0
ZHAOCAI_LOG_LEVEL=info
ZHAOCAI_CONFIG=./config.yaml

# Control plane
ZHAOCAI_ADMIN_TOKEN=$ADMIN_TOKEN
ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db
ZHAOCAI_ENCRYPTION_KEY=$ENCRYPTION_KEY

# AI Provider API keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
NVIDIA_API_KEY=
DASHSCOPE_API_KEY=
SILICONFLOW_API_KEY=
OPENROUTER_API_KEY=

# Cloudflare tunnel token (optional)
CF_TUNNEL_TOKEN=
EOF
  echo -e "${GREEN}OK .env created${NC}"
else
  echo -e "${YELLOW}Skip .env creation because it already exists${NC}"
fi

if [ ! -f "config.yaml" ]; then
  cp config.example.yaml config.yaml
  echo -e "${GREEN}OK config.yaml created${NC}"
else
  echo -e "${YELLOW}Skip config.yaml creation because it already exists${NC}"
fi

echo -e "${YELLOW}[5/6] Create data directory...${NC}"
mkdir -p data
echo -e "${GREEN}OK data directory ready${NC}"

echo -e "${YELLOW}[6/6] Verify installation...${NC}"
python -c "from gateway import app; print('OK')" >/dev/null
echo -e "${GREEN}OK install verification passed${NC}"

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}Bootstrap complete${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "  Admin Token: $ADMIN_TOKEN"
if [ -n "$ENCRYPTION_KEY" ]; then
  echo "  Encryption Key: $ENCRYPTION_KEY"
else
  echo "  Encryption Key: (not set - cryptography unavailable)"
fi
echo ""
echo -e "${YELLOW}Next:${NC}"
echo "  1. Fill API keys in .env"
echo "  2. Optionally adjust config.yaml"
echo "  3. Run: python gateway.py"
echo ""
echo -e "${YELLOW}URLs:${NC}"
echo "  - API docs: http://localhost:8000/docs"
echo "  - Control panel: http://localhost:8000/control"
echo "  - Health API: http://localhost:8000/api/health"
echo "  - Health UI: http://localhost:8000/health-ui"
