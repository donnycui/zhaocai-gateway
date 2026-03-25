#!/usr/bin/env python3
"""
Bootstrap script for the v2 control-plane runtime.

Usage:
  python deploy.py
"""

from __future__ import annotations

import secrets
import subprocess
import sys
from pathlib import Path
from shutil import which


def print_step(step_num: int, total: int, message: str) -> None:
    print(f"\n[{step_num}/{total}] {message}")
    print("-" * 50)


def print_success(message: str) -> None:
    print(f"[OK] {message}")


def print_error(message: str) -> None:
    print(f"[ERROR] {message}")
    raise SystemExit(1)


def run_command(cmd: str, *, capture: bool = True, cwd: Path | None = None) -> str | None:
    try:
        if capture:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
                cwd=cwd,
            )
            return result.stdout.strip()
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)
        return None
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Command failed: {cmd}\n{stderr}") from exc


def has_command(name: str) -> bool:
    return which(name) is not None


def generate_encryption_key() -> str:
    try:
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode()
    except Exception:
        return ""


def ensure_env_file(env_path: Path, admin_token: str, encryption_key: str) -> tuple[str, str]:
    if not env_path.exists():
        env_content = f"""# Runtime
ZHAOCAI_PORT=8000
ZHAOCAI_HOST=0.0.0.0
ZHAOCAI_LOG_LEVEL=info
ZHAOCAI_APP_TITLE=Zhaocai Gateway
ZHAOCAI_APP_DESCRIPTION=AI Provider Gateway + OpenClaw Control Plane
ZHAOCAI_APP_VERSION=2.0.0
ZHAOCAI_WEB_DIST=./web/dist

# Control plane storage
ZHAOCAI_ADMIN_TOKEN={admin_token}
ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db
ZHAOCAI_ENCRYPTION_KEY={encryption_key}

# Optional tunnel
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
    repo_root = Path.cwd()

    print("=" * 50)
    print("Zhaocai Gateway v2 bootstrap")
    print("=" * 50)

    print_step(1, 6, "Check Python version")
    if sys.version_info < (3, 9):
        print_error("Python 3.9+ is required.")
    print_success(f"Python version: {sys.version.split()[0]}")

    print_step(2, 6, "Create virtual environment")
    venv_path = repo_root / ".venv"
    if not venv_path.exists():
        run_command(f"{sys.executable} -m venv .venv", capture=False, cwd=repo_root)
        print_success(".venv created")
    else:
        print_success(".venv already exists")

    if sys.platform.startswith("win"):
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"

    print_step(3, 6, "Install Python dependencies")
    run_command(f"{pip_path} install --upgrade pip -q", capture=False, cwd=repo_root)
    run_command(f"{pip_path} install -r requirements.txt -q", capture=False, cwd=repo_root)
    print_success("Python dependencies installed")

    print_step(4, 6, "Create .env")
    admin_token = f"admin-{secrets.token_hex(16)}"
    encryption_key = generate_encryption_key()
    admin_token, encryption_key = ensure_env_file(
        env_path=repo_root / ".env",
        admin_token=admin_token,
        encryption_key=encryption_key,
    )

    print_step(5, 6, "Build web UI")
    if not has_command("npm"):
        print_error("npm is required to build web/dist for the v2 control plane UI.")
    run_command("npm install", capture=False, cwd=repo_root / "web")
    run_command("npm run build", capture=False, cwd=repo_root / "web")
    print_success("web/dist built")

    print_step(6, 6, "Verify installation")
    (repo_root / "data").mkdir(exist_ok=True)
    verify_result = run_command(
        f"{python_path} -c \"from zhaocai_gateway.main import app; print('OK')\"",
        cwd=repo_root,
    )
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
    print("  1. Start backend: .venv/bin/python -m zhaocai_gateway.main")
    print("  2. Open http://localhost:8000")
    print("  3. Paste the admin token into the top bar of the web UI")
    print("\nURLs:")
    print("  - Control plane UI: http://localhost:8000")
    print("  - Health API: http://localhost:8000/health")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print_error(str(exc))
