#!/usr/bin/env python3
"""
Zhaocai Gateway - 招财网关
A lightweight API gateway for AI providers with Cloudflare Tunnel support.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, Optional
from contextlib import asynccontextmanager

import httpx
import yaml
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(
    level=getattr(logging, os.getenv("ZHAOCAI_LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============== 数据模型 ==============

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    api_key: str
    models: List[str]
    weight: float = 1.0
    timeout: int = 60
    enabled: bool = True


@dataclass
class ProviderStatus:
    name: str
    healthy: bool = True
    last_check: float = field(default_factory=time.time)
    request_count: int = 0
    error_count: int = 0
    latency_ms: float = 0.0


# ============== 核心类 ==============

class ProviderManager:
    """管理多个 provider 的路由和健康检查"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.providers: Dict[str, ProviderConfig] = {}
        self.status: Dict[str, ProviderStatus] = {}
        self.config = self._load_config(config_path)
        self._init_providers()
        
    def _load_config(self, path: str) -> dict:
        """加载配置文件"""
        if not os.path.exists(path):
            logger.warning(f"Config file not found: {path}, using defaults")
            return self._default_config()
        
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
            
        # 展开环境变量
        config = self._expand_env_vars(config)
        return config
    
    def _expand_env_vars(self, obj):
        """递归展开配置中的环境变量"""
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            default = ""
            if ":-" in env_var:
                env_var, default = env_var.split(":-", 1)
            return os.getenv(env_var, default)
        return obj
    
    def _default_config(self) -> dict:
        """默认配置"""
        return {
            "gateway": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 4
            },
            "providers": {},
            "routing": {
                "strategy": "round_robin",
                "fallback_enabled": True,
                "max_retries": 3
            }
        }
    
    def _init_providers(self):
        """初始化 provider"""
        providers_config = self.config.get("providers", {})
        
        for name, cfg in providers_config.items():
            if not cfg.get("enabled", True):
                logger.info(f"Provider {name} is disabled")
                continue
                
            provider = ProviderConfig(
                name=name,
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                models=cfg.get("models", []),
                weight=cfg.get("weight", 1.0),
                timeout=cfg.get("timeout", 60)
            )
            self.providers[name] = provider
            self.status[name] = ProviderStatus(name=name)
            logger.info(f"Loaded provider: {name} with models: {provider.models}")
    
    def get_provider_for_model(self, model: str) -> Optional[ProviderConfig]:
        """根据模型名获取 provider"""
        for name, provider in self.providers.items():
            if model in provider.models or model.startswith(f"{name}/"):
                if self.status[name].healthy:
                    return provider
        return None
    
    def get_all_models(self) -> List[Dict]:
        """获取所有可用模型"""
        models = []
        for name, provider in self.providers.items():
            for model in provider.models:
                models.append({
                    "id": model,
                    "object": "model",
                    "owned_by": name
                })
        return models
    
    def update_status(self, name: str, healthy: bool, latency_ms: float = 0):
        """更新 provider 状态"""
        if name in self.status:
            self.status[name].healthy = healthy
            self.status[name].last_check = time.time()
            self.status[name].latency_ms = latency_ms
            if not healthy:
                self.status[name].error_count += 1
    
    async def health_check(self) -> Dict[str, any]:
        """执行健康检查"""
        results = {}
        async with httpx.AsyncClient() as client:
            for name, provider in self.providers.items():
                try:
                    start = time.time()
                    # 简单的健康检查 - 尝试访问 base_url
                    resp = await client.get(
                        f"{provider.base_url}/models",
                        headers={"Authorization": f"Bearer {provider.api_key}"},
                        timeout=10
                    )
                    latency = (time.time() - start) * 1000
                    healthy = resp.status_code == 200
                    self.update_status(name, healthy, latency)
                    results[name] = {"healthy": healthy, "latency_ms": latency}
                except Exception as e:
                    self.update_status(name, False)
                    results[name] = {"healthy": False, "error": str(e)}
        return results


class GatewayServer:
    """网关服务核心"""
    
    def __init__(self):
        config_path = os.getenv("ZHAOCAI_CONFIG", "config.yaml")
        self.provider_manager = ProviderManager(config_path)
        self.request_count = 0
        self.error_count = 0
        
    async def chat_completion(self, request: ChatCompletionRequest) -> Dict:
        """处理聊天补全请求"""
        model = request.model
        
        # 查找 provider
        provider = self.provider_manager.get_provider_for_model(model)
        if not provider:
            # 尝试使用 model 名作为 provider 前缀
            if "/" in model:
                provider_name, actual_model = model.split("/", 1)
                if provider_name in self.provider_manager.providers:
                    provider = self.provider_manager.providers[provider_name]
                    request.model = actual_model
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model {model} not available in any provider"
            )
        
        # 转发请求
        async with httpx.AsyncClient(timeout=provider.timeout) as client:
            try:
                start = time.time()
                
                # 构建请求体
                payload = request.model_dump(exclude_none=True)
                
                headers = {
                    "Authorization": f"Bearer {provider.api_key}",
                    "Content-Type": "application/json"
                }
                
                # 根据不同 provider 调整端点
                if "anthropic" in provider.base_url.lower():
                    endpoint = f"{provider.base_url}/v1/messages"
                    # Anthropic 格式转换
                    payload = self._convert_to_anthropic_format(payload)
                else:
                    endpoint = f"{provider.base_url}/chat/completions"
                
                resp = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers
                )
                
                latency = (time.time() - start) * 1000
                self.provider_manager.status[provider.name].request_count += 1
                self.provider_manager.status[provider.name].latency_ms = latency
                
                if resp.status_code != 200:
                    self.provider_manager.status[provider.name].error_count += 1
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=resp.text
                    )
                
                result = resp.json()
                
                # 如果是 Anthropic，转换回 OpenAI 格式
                if "anthropic" in provider.base_url.lower():
                    result = self._convert_from_anthropic_format(result, model)
                
                return result
                
            except httpx.TimeoutException:
                self.provider_manager.status[provider.name].error_count += 1
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Request timeout"
                )
            except Exception as e:
                self.provider_manager.status[provider.name].error_count += 1
                logger.error(f"Error calling {provider.name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=str(e)
                )
    
    def _convert_to_anthropic_format(self, payload: Dict) -> Dict:
        """将 OpenAI 格式转换为 Anthropic 格式"""
        messages = payload.get("messages", [])
        system_msg = None
        clean_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                clean_messages.append(msg)
        
        anthropic_payload = {
            "model": payload["model"],
            "messages": clean_messages,
            "max_tokens": payload.get("max_tokens", 4096),
        }
        
        if system_msg:
            anthropic_payload["system"] = system_msg
        if "temperature" in payload:
            anthropic_payload["temperature"] = payload["temperature"]
        if payload.get("stream"):
            anthropic_payload["stream"] = True
            
        return anthropic_payload
    
    def _convert_from_anthropic_format(self, result: Dict, model: str) -> Dict:
        """将 Anthropic 格式转换为 OpenAI 格式"""
        return {
            "id": result.get("id", "chatcmpl-" + str(int(time.time()))),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("content", [{}])[0].get("text", "")
                },
                "finish_reason": "stop"
            }],
            "usage": result.get("usage", {})
        }


# ============== FastAPI 应用 ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行健康检查
    logger.info("Starting Zhaocai Gateway...")
    await gateway.provider_manager.health_check()
    logger.info("Health check completed")
    yield
    # 关闭时清理
    logger.info("Shutting down Zhaocai Gateway...")


app = FastAPI(
    title="Zhaocai Gateway",
    description="招财网关 - AI Provider Gateway with Cloudflare Tunnel support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局网关实例
gateway = GatewayServer()


@app.get("/")
async def root():
    """根路径 - 返回基本信息"""
    return {
        "name": "Zhaocai Gateway",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查端点"""
    health_results = await gateway.provider_manager.health_check()
    return {
        "status": "healthy",
        "providers": health_results,
        "timestamp": time.time()
    }


@app.get("/v1/models")
async def list_models():
    """列出所有可用模型（OpenAI 兼容格式）"""
    models = gateway.provider_manager.get_all_models()
    return {
        "object": "list",
        "data": models
    }


@app.get("/v1/providers")
async def list_providers():
    """列出所有 provider 及其状态"""
    return {
        "providers": [
            {
                "name": name,
                "base_url": cfg.base_url,
                "models": cfg.models,
                "weight": cfg.weight,
                "enabled": cfg.enabled,
                "status": {
                    "healthy": gateway.provider_manager.status[name].healthy,
                    "request_count": gateway.provider_manager.status[name].request_count,
                    "error_count": gateway.provider_manager.status[name].error_count,
                    "latency_ms": gateway.provider_manager.status[name].latency_ms
                }
            }
            for name, cfg in gateway.provider_manager.providers.items()
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """聊天补全端点（OpenAI 兼容）"""
    result = await gateway.chat_completion(request)
    return result


@app.get("/metrics")
async def metrics():
    """基础指标"""
    return {
        "requests_total": sum(s.request_count for s in gateway.provider_manager.status.values()),
        "errors_total": sum(s.error_count for s in gateway.provider_manager.status.values()),
        "providers": {
            name: {
                "healthy": status.healthy,
                "requests": status.request_count,
                "errors": status.error_count,
                "latency_ms": status.latency_ms
            }
            for name, status in gateway.provider_manager.status.items()
        }
    }


# ============== 主入口 ==============

def main():
    import uvicorn
    
    config = gateway.provider_manager.config
    host = os.getenv("ZHAOCAI_HOST", config.get("gateway", {}).get("host", "0.0.0.0"))
    port = int(os.getenv("ZHAOCAI_PORT", config.get("gateway", {}).get("port", 8000)))
    workers = config.get("gateway", {}).get("workers", 1)
    
    logger.info(f"Starting Zhaocai Gateway on {host}:{port}")
    logger.info(f"Workers: {workers}")
    logger.info(f"Providers: {list(gateway.provider_manager.providers.keys())}")
    
    uvicorn.run(
        "gateway:app",
        host=host,
        port=port,
        workers=workers if workers > 1 else 1,
        reload=False
    )


if __name__ == "__main__":
    main()
