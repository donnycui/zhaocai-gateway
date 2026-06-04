from __future__ import annotations

import os
from typing import Literal


NodeTarget = Literal["openclaw", "hermes"]
PlatformFamily = Literal["macos", "linux"]


def resolve_public_base_url(explicit: str | None = None) -> str:
    value = (explicit or os.getenv("ZHAOCAI_NODE_PUBLIC_BASE_URL") or "https://zhaocai.mintstudio.cn").strip()
    return value.rstrip("/")


def resolve_node_repo_url(explicit: str | None = None) -> str:
    return (explicit or os.getenv("ZHAOCAI_NODE_GIT_REPO_URL") or "https://github.com/donnycui/zhaocai-gateway.git").strip()


def resolve_node_git_ref(target: NodeTarget, explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    target_specific = os.getenv(
        "ZHAOCAI_NODE_HERMES_GIT_REF" if target == "hermes" else "ZHAOCAI_NODE_OPENCLAW_GIT_REF"
    )
    if target_specific:
        return target_specific.strip()
    general = os.getenv("ZHAOCAI_NODE_GIT_REF")
    if general:
        return general.strip()
    return "codex/hermes-module" if target == "hermes" else "main"


def infer_platform_family(platform: str, device_type: str) -> PlatformFamily:
    lowered = f"{platform} {device_type}".lower()
    if any(token in lowered for token in ("darwin", "mac", "macbook")):
        return "macos"
    return "linux"


def build_install_command(
    *,
    target: NodeTarget,
    pairing_token: str,
    platform: str,
    device_type: str,
    public_base_url: str | None = None,
    repo_url: str | None = None,
    git_ref: str | None = None,
) -> str:
    family = infer_platform_family(platform, device_type)
    resolved_base_url = resolve_public_base_url(public_base_url)
    resolved_repo_url = resolve_node_repo_url(repo_url)
    resolved_git_ref = resolve_node_git_ref(target, git_ref)

    config_path = "$HOME/.zhaocai-gateway/hermes-agent.json" if target == "hermes" else "$HOME/.zhaocai-gateway/agent.json"
    output_path = "$HOME/.hermes/config.yaml" if target == "hermes" else "$HOME/.openclaw/openclaw.json"
    launchd_plist = "com.zhaocai.hermes-agent.plist" if target == "hermes" else "com.zhaocai.agent.plist"
    systemd_service = "zhaocai-hermes-agent.service" if target == "hermes" else "zhaocai-agent.service"

    setup_lines = [
        f"[ -d zhaocai-gateway ] || git clone {resolved_repo_url}",
        "cd zhaocai-gateway",
        "git fetch origin",
    ]
    if target == "hermes":
        setup_lines.extend(
            [
                f"git switch {resolved_git_ref} 2>/dev/null || git switch -c {resolved_git_ref} --track origin/{resolved_git_ref}",
                "git pull --ff-only",
            ]
        )
    elif resolved_git_ref == "main":
        setup_lines.extend([
            "git switch main",
            "git pull --ff-only",
        ])
    else:
        setup_lines.extend([
            f"git switch {resolved_git_ref} 2>/dev/null || git switch -c {resolved_git_ref} --track origin/{resolved_git_ref}",
            "git pull --ff-only",
        ])

    register_lines = [
        ".venv/bin/python -m agent.cli register \\",
    ]
    if target == "hermes":
        register_lines.append("  --target hermes \\")
    register_lines.extend(
        [
            f"  --server {resolved_base_url} \\",
            f"  --token {pairing_token} \\",
            f'  --config-path "{config_path}" \\',
            f'  --output-path "{output_path}"',
        ]
    )
    if target == "openclaw":
        register_lines[-1] += ' \\'
        register_lines.append('  --reload-cmd "$(command -v openclaw) gateway restart"')
    elif family == "macos":
        register_lines[-1] += " \\"
        register_lines.append("  --reload-cmd /usr/bin/true")

    sync_command = f'.venv/bin/python -m agent.cli sync-once{" --target hermes" if target == "hermes" else ""} --config-path "{config_path}"'

    if family == "linux":
        doctor_command = f'.venv/bin/python -m agent.cli doctor{" --target hermes" if target == "hermes" else ""} --config-path "{config_path}" --service-manager systemd'
        install_command = [
            ".venv/bin/python -m agent.cli install \\",
        ]
        if target == "hermes":
            install_command.append("  --target hermes \\")
        install_command.extend(
            [
                f'  --config-path "{config_path}" \\',
                "  --service-manager systemd \\",
                '  --python-path "$PWD/.venv/bin/python" \\',
                '  --working-directory "$PWD"',
            ]
        )
        return "\n".join(
            [
                "sudo apt update",
                "sudo apt install -y python3-venv",
                *setup_lines,
                "python3 -m venv .venv",
                ".venv/bin/pip install -r requirements.txt",
                *register_lines,
                sync_command,
                doctor_command,
                *install_command,
                "systemctl --user daemon-reload",
                f"systemctl --user enable --now {systemd_service}",
                f"systemctl --user status {systemd_service}",
            ]
        )

    doctor_command = f'.venv/bin/python -m agent.cli doctor{" --target hermes" if target == "hermes" else ""} --config-path "{config_path}"'
    install_command = f'.venv/bin/python -m agent.cli install{" --target hermes" if target == "hermes" else ""} --config-path "{config_path}"'
    return "\n".join(
        [
            *setup_lines,
            "python3 -m venv .venv",
            ".venv/bin/pip install -r requirements.txt",
            *register_lines,
            sync_command,
            doctor_command,
            install_command,
            f"launchctl unload ~/Library/LaunchAgents/{launchd_plist} >/dev/null 2>&1 || true",
            f"launchctl load ~/Library/LaunchAgents/{launchd_plist}",
        ]
    )
