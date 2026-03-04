#!/usr/bin/env python3
"""
Zhaocai Gateway 部署脚本 (Windows/Linux 通用)
"""

import os
import sys
import subprocess
import secrets
from pathlib import Path

def print_step(step_num, total, message):
    print(f"\n[{step_num}/{total}] {message}")
    print("-" * 50)

def print_success(message):
    print(f"[OK] {message}")

def print_error(message):
    print(f"[ERROR] {message}")
    sys.exit(1)

def run_command(cmd, capture=True):
    """运行命令并返回结果"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=True)
            return None
    except subprocess.CalledProcessError as e:
        return None

def generate_encryption_key():
    """生成 Fernet 加密密钥"""
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        # 如果 cryptography 未安装，使用备选方案
        return secrets.token_urlsafe(32)

def main():
    print("=" * 50)
    print("Zhaocai Gateway 部署脚本")
    print("=" * 50)

    # 检查 Python 版本
    print_step(1, 6, "检查 Python 版本")
    if sys.version_info < (3, 9):
        print_error("需要 Python 3.9 或更高版本")
    print_success(f"Python 版本: {sys.version.split()[0]}")

    # 创建虚拟环境
    print_step(2, 6, "创建虚拟环境")
    venv_path = Path("venv")
    if not venv_path.exists():
        run_command(f"{sys.executable} -m venv venv")
        print_success("虚拟环境已创建")
    else:
        print_success("虚拟环境已存在")

    # 获取虚拟环境的 pip 路径
    if os.name == 'nt':  # Windows
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:  # Linux/Mac
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"

    # 安装依赖
    print_step(3, 6, "安装依赖")
    run_command(f"{pip_path} install --upgrade pip -q")
    run_command(f"{pip_path} install -r requirements.txt -q")
    print_success("依赖安装完成")

    # 生成配置
    print_step(4, 6, "生成配置文件")

    encryption_key = generate_encryption_key()
    admin_token = f"admin-{secrets.token_hex(16)}"

    # 创建 .env 文件
    env_path = Path(".env")
    if not env_path.exists():
        env_content = f"""# Gateway runtime
ZHAOCAI_PORT=8000
ZHAOCAI_HOST=0.0.0.0
ZHAOCAI_LOG_LEVEL=info
ZHAOCAI_CONFIG=./config.yaml

# Control plane
ZHAOCAI_ADMIN_TOKEN={admin_token}
ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db
ZHAOCAI_ENCRYPTION_KEY={encryption_key}

# AI Provider API keys (请填入你的实际 API Key)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
NVIDIA_API_KEY=
DASHSCOPE_API_KEY=
SILICONFLOW_API_KEY=
OPENROUTER_API_KEY=

# Cloudflare tunnel token (optional)
CF_TUNNEL_TOKEN=
"""
        env_path.write_text(env_content, encoding='utf-8')
        print_success(".env 文件已创建")
    else:
        print_success(".env 文件已存在，跳过创建")
        # 读取现有的 token
        env_lines = env_path.read_text(encoding='utf-8').split('\n')
        for line in env_lines:
            if line.startswith('ZHAOCAI_ADMIN_TOKEN='):
                admin_token = line.split('=', 1)[1]
            if line.startswith('ZHAOCAI_ENCRYPTION_KEY='):
                encryption_key = line.split('=', 1)[1]

    # 创建 config.yaml
    config_path = Path("config.yaml")
    if not config_path.exists():
        example_path = Path("config.example.yaml")
        if example_path.exists():
            config_path.write_text(example_path.read_text(encoding='utf-8'), encoding='utf-8')
            print_success("config.yaml 已创建")
    else:
        print_success("config.yaml 已存在，跳过创建")

    # 创建数据目录
    print_step(5, 6, "创建数据目录")
    Path("data").mkdir(exist_ok=True)
    print_success("数据目录已准备")

    # 验证安装
    print_step(6, 6, "验证安装")
    try:
        # 尝试导入关键模块
        result = run_command(f"{python_path} -c \"from gateway import app; print('OK')\"")
        if result == "OK":
            print_success("安装验证通过")
        else:
            print_error("导入验证失败，请检查依赖")
    except Exception as e:
        print_error(f"验证失败: {e}")

    # 显示完成信息
    print("\n" + "=" * 50)
    print("部署完成！")
    print("=" * 50)
    print(f"\n重要信息：")
    print(f"  Admin Token: {admin_token}")
    print(f"  加密密钥: {encryption_key}")
    print(f"\n下一步：")
    print("  1. 编辑 .env 文件，填入你的 API Key")
    print("  2. 编辑 config.yaml，配置 Provider（可选）")

    if os.name == 'nt':
        print(f"  3. 运行: venv\\Scripts\\python.exe gateway.py")
    else:
        print(f"  3. 运行: source venv/bin/activate && python gateway.py")

    print(f"\n访问地址：")
    print("  - API 文档: http://localhost:8000/docs")
    print("  - 控制面板: http://localhost:8000/control")
    print("  - 健康检查: http://localhost:8000/health")
    print("")

if __name__ == "__main__":
    main()
