#!/usr/bin/env python3
"""
Cross-platform bootstrap script for Zhaocai Gateway.

Usage:
  python deploy.py
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path


def print_step(step_num: int, total: int, message: str) -> None:
    print(f"\n[{step_num}/{total}] {message}")
    print("-" * 50)


def print_success(message: str) -> None:
    print(f"[OK] {message}")


def print_error(message: str) -> None:
    print(f"[ERROR] {message}")
    sys.exit(1)


def run_command(cmd: str, capture: bool = True) -> str | None:
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        subprocess.run(cmd, shell=True, check=True)
        return None
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Command failed: {cmd}\n{stderr}") from exc


def generate_encryption_key() -> str:
    try:
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode()
    except ImportError:
        return ""


def ensure_env_file(env_path: Path, admin_token: str, encryption_key: str) -> tuple[str, str]:
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
ZHAOCAI_ROUTING_SOURCE=hybrid
ZHAOCAI_CONTROL_SYNC_INTERVAL_SECONDS=5
ZHAOCAI_NODE_PROVIDER_MODE=gateway
ZHAOCAI_NODE_GATEWAY_PROVIDER_ID=zhaocai-gateway
ZHAOCAI_NODE_GATEWAY_BASE_URL=http://127.0.0.1:8000/v1
ZHAOCAI_NODE_GATEWAY_PROVIDER_TYPE=openai
ZHAOCAI_NODE_GATEWAY_AUTH_SCHEME=bearer
ZHAOCAI_NODE_GATEWAY_API_KEY=
ZHAOCAI_NODE_GATEWAY_EXTRA_HEADERS={}

# AI Provider API keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
NVIDIA_API_KEY=
DASHSCOPE_API_KEY=
SILICONFLOW_API_KEY=
OPENROUTER_API_KEY=

# Cloudflare tunnel token (optional)
CF_TUNNEL_TOKEN=
"""
        env_path.write_text(env_content, encoding="utf-8")
        print_success(".env created")
        return admin_token, encryption_key

    print_success(".env already exists, keeping existing values")
    current_admin = admin_token
    current_key = encryption_key
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("ZHAOCAI_ADMIN_TOKEN="):
            current_admin = line.split("=", 1)[1].strip()
        if line.startswith("ZHAOCAI_ENCRYPTION_KEY="):
            current_key = line.split("=", 1)[1].strip()
    return current_admin, current_key


def main() -> None:
    print("=" * 50)
    print("Zhaocai Gateway bootstrap")
    print("=" * 50)

    print_step(1, 6, "Check Python version")
    if sys.version_info < (3, 9):
        print_error("Python 3.9+ is required.")
    print_success(f"Python version: {sys.version.split()[0]}")

    print_step(2, 6, "Create virtual environment")
    venv_path = Path("venv")
    if not venv_path.exists():
        run_command(f"{sys.executable} -m venv venv", capture=False)
        print_success("Virtual environment created")
    else:
        print_success("Virtual environment already exists")

    if os.name == "nt":
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"

    print_step(3, 6, "Install dependencies")
    run_command(f"{pip_path} install --upgrade pip -q", capture=False)
    run_command(f"{pip_path} install -r requirements.txt -q", capture=False)
    print_success("Dependencies installed")

    print_step(4, 6, "Generate configuration")
    generated_admin_token = f"admin-{secrets.token_hex(16)}"
    generated_encryption_key = generate_encryption_key()
    admin_token, encryption_key = ensure_env_file(
        env_path=Path(".env"),
        admin_token=generated_admin_token,
        encryption_key=generated_encryption_key,
    )

    config_path = Path("config.yaml")
    example_path = Path("config.example.yaml")
    if not config_path.exists() and example_path.exists():
        config_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
        print_success("config.yaml created from config.example.yaml")
    else:
        print_success("config.yaml already exists")

    print_step(5, 6, "Create data directory")
    Path("data").mkdir(exist_ok=True)
    print_success("data directory ready")

    print_step(6, 6, "Verify installation")
    verify_result = run_command(f"{python_path} -c \"from gateway import app; print('OK')\"")
    if verify_result != "OK":
        print_error("Import verification failed")
    print_success("Install verification passed")

    print("\n" + "=" * 50)
    print("Bootstrap complete")
    print("=" * 50)
    print("\nImportant:")
    print(f"  Admin Token: {admin_token}")
    print(f"  Encryption Key: {encryption_key or '(not set)'}")
    print("\nNext:")
    print("  1. Fill API keys in .env")
    print("  2. Optionally adjust config.yaml")
    if os.name == "nt":
        print("  3. Run: venv\\Scripts\\python.exe gateway.py")
    else:
        print("  3. Run: source venv/bin/activate && python gateway.py")
    print("\nURLs:")
    print("  - API docs: http://localhost:8000/docs")
    print("  - Control panel: http://localhost:8000/control")
    print("  - Health API: http://localhost:8000/api/health")
    print("  - Health UI: http://localhost:8000/health-ui")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print_error(str(exc))
