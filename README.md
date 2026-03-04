# Zhaocai Gateway 💰

招财网关 - 一个轻量级、可扩展的 API 网关，支持多 provider 路由、负载均衡和Cloudflare Tunnel 暴露。

## 特性

- 🚀 **轻量级** - 纯 Python 实现，低资源占用
- 🔄 **多 Provider 路由** - 支持多个 AI provider 的智能路由
- ⚖️ **负载均衡** - 自动 fallback 和重试机制
- 🔒 **Cloudflare Tunnel 支持** - 内置 tunnel 配置支持
- 📊 **可观测性** - 请求日志和基础指标
- 🔧 **易于配置** - YAML 配置文件

## 快速开始

### 1. 安装

```bash
git clone https://github.com/yourusername/zhaocai-gateway.git
cd zhaocai-gateway
pip install -r requirements.txt
```

### 2. 配置

复制示例配置并修改：

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 添加你的 API keys
```

### 3. 启动

```bash
python gateway.py
```

网关默认运行在 `http://localhost:8000`

## Cloudflare Tunnel 配置

### 方式 1：使用现有 tunnel

编辑你的 cloudflared 配置（通常位于 `~/.cloudflared/config.yml` 或 `/etc/cloudflared/config.yml`）：

```yaml
tunnel: <your-tunnel-id>
credentials-file: /path/to/your/credentials.json

protocol: http2

ingress:
  - hostname: zhaocai.yourdomain.com
    service: http://localhost:8000
    
  # ... 其他服务
  
  - service: http_status:404
```

重启 cloudflared：

```bash
sudo systemctl restart cloudflared
# 或
cloudflared tunnel run <tunnel-name>
```

### 方式 2：创建新 tunnel

```bash
# 登录 cloudflare
cloudflared tunnel login

# 创建 tunnel
cloudflared tunnel create zhaocai

# 查看 tunnel ID
cloudflared tunnel list

# 配置 DNS 路由
curl -X POST "https://api.cloudflare.com/client/v4/zones/<zone-id>/dns_records" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "zhaocai",
    "content": "<tunnel-id>.cfargotunnel.com",
    "proxied": true
  }'
```

## 配置说明

### config.yaml

```yaml
# 网关基础配置
gateway:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  
# Provider 配置
providers:
  openai:
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    models:
      - "gpt-4"
      - "gpt-3.5-turbo"
    weight: 1.0
    
  anthropic:
    base_url: "https://api.anthropic.com"
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      - "claude-3-opus"
    weight: 1.0

# 路由规则
routing:
  strategy: "round_robin"  # round_robin, weighted, priority
  fallback_enabled: true
  max_retries: 3
  
# 日志配置
logging:
  level: "info"
  format: "json"  # json, text
  
# 限流配置
rate_limit:
  enabled: true
  requests_per_minute: 60
  burst: 10
```

## API 使用

### 聊天补全

```bash
curl http://zhaocai.yourdomain.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-gateway-key" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### 健康检查

```bash
curl http://zhaocai.yourdomain.com/health
```

### Provider 列表

```bash
curl http://zhaocai.yourdomain.com/v1/providers
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ZHAOCAI_PORT` | 网关端口 | `8000` |
| `ZHAOCAI_HOST` | 绑定地址 | `0.0.0.0` |
| `ZHAOCAI_CONFIG` | 配置文件路径 | `./config.yaml` |
| `ZHAOCAI_LOG_LEVEL` | 日志级别 | `info` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |

## Docker 部署

```bash
# 构建镜像
docker build -t zhaocai-gateway .

# 运行
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY="sk-xxx" \
  -v $(pwd)/config.yaml:/app/config.yaml \
  --name zhaocai \
  zhaocai-gateway
```

### Docker Compose

```yaml
version: '3.8'

services:
  zhaocai:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./config.yaml:/app/config.yaml
    restart: unless-stopped
    
  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel run --token ${CF_TUNNEL_TOKEN}
    restart: unless-stopped
    depends_on:
      - zhaocai
```

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest

# 代码格式化
black gateway.py
isort gateway.py
```

## 架构

```
┌─────────────────┐
│   Cloudflare    │
│     Tunnel      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Zhaocai Gateway │
│     :8000       │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Provider│ │Provider│
│   A    │ │   B    │
└────────┘ └────────┘
```

## 贡献

欢迎 PR！请先开 issue 讨论大改动。

## License

MIT

---

💰 祝你招财进宝，API 永不宕机！
