#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "Zhaocai Gateway v2 bootstrap"
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

$PYTHON_BIN - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit(1)
PY
echo -e "${GREEN}OK Python version: $($PYTHON_BIN -c 'import sys; print(sys.version.split()[0])')${NC}"

echo -e "${YELLOW}[2/6] Create virtual environment...${NC}"
if [ ! -d ".venv" ]; then
  $PYTHON_BIN -m venv .venv
  echo -e "${GREEN}OK .venv created${NC}"
else
  echo -e "${GREEN}OK .venv already exists${NC}"
fi

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  # shellcheck disable=SC1091
  source .venv/Scripts/activate
fi

echo -e "${YELLOW}[3/6] Install Python dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}OK Python dependencies installed${NC}"

echo -e "${YELLOW}[4/6] Create .env...${NC}"
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
# Runtime
ZHAOCAI_PORT=8000
ZHAOCAI_HOST=0.0.0.0
ZHAOCAI_LOG_LEVEL=info
ZHAOCAI_APP_TITLE=Zhaocai Gateway
ZHAOCAI_APP_DESCRIPTION=AI Provider Gateway + OpenClaw Control Plane
ZHAOCAI_APP_VERSION=2.0.0
ZHAOCAI_WEB_DIST=./web/dist

# Control plane storage
ZHAOCAI_ADMIN_TOKEN=$ADMIN_TOKEN
ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db
ZHAOCAI_ENCRYPTION_KEY=$ENCRYPTION_KEY

# Optional tunnel
CF_TUNNEL_TOKEN=
EOF
  echo -e "${GREEN}OK .env created${NC}"
else
  echo -e "${GREEN}OK .env already exists${NC}"
fi

echo -e "${YELLOW}[5/6] Build web UI...${NC}"
if ! command -v npm >/dev/null 2>&1; then
  echo -e "${RED}Error: npm is required to build web/dist${NC}"
  exit 1
fi
(
  cd web
  npm install
  npm run build
)
echo -e "${GREEN}OK web/dist built${NC}"

echo -e "${YELLOW}[6/6] Verify installation...${NC}"
mkdir -p data
python -c "from zhaocai_gateway.main import app; print('OK')" >/dev/null
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
echo "  1. Start backend: .venv/bin/python -m zhaocai_gateway.main"
echo "  2. Open http://localhost:8000"
echo "  3. Paste the admin token into the top bar of the web UI"
