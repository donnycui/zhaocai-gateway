from __future__ import annotations

import getpass
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil

from agent.config import (
    AgentTarget,
    DEFAULT_AGENT_CONFIG_PATH,
    default_output_path_for,
    load_agent_config,
)


@dataclass(frozen=True)
class InstallArtifact:
    path: Path
    content: str


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def build_systemd_service(
    *,
    target: AgentTarget,
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
) -> str:
    service_title = "Zhaocai Hermes Node Agent" if target == "hermes" else "Zhaocai Gateway Node Agent"
    target_flag = f" --target {target}" if target == "hermes" else ""
    return f"""[Unit]
Description={service_title}
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={working_directory}
ExecStart={python_path} -m agent.cli run{target_flag} --config-path {config_path} --interval {interval_seconds}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""


def build_launchd_plist(
    *,
    target: AgentTarget,
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
) -> str:
    launchd_label = "com.zhaocai.hermes-agent" if target == "hermes" else "com.zhaocai.agent"
    target_lines = (
        "      <string>--target</string>\n"
        f"      <string>{target}</string>\n"
        if target == "hermes"
        else ""
    )
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
  <dict>
    <key>Label</key>
    <string>{launchd_label}</string>
    <key>ProgramArguments</key>
    <array>
      <string>{python_path}</string>
      <string>-m</string>
      <string>agent.cli</string>
      <string>run</string>
{target_lines}      <string>--config-path</string>
      <string>{config_path}</string>
      <string>--interval</string>
      <string>{interval_seconds}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{working_directory}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{working_directory}/agent.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{working_directory}/agent.stderr.log</string>
  </dict>
</plist>
"""


def systemd_install_artifact(
    *,
    target: AgentTarget = "openclaw",
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
    output_path: str | None = None,
) -> InstallArtifact:
    target_path = (
        Path(output_path)
        if output_path
        else default_service_path("systemd", target)
    )
    content = build_systemd_service(
        target=target,
        python_path=python_path,
        config_path=config_path,
        interval_seconds=interval_seconds,
        working_directory=working_directory,
    )
    return InstallArtifact(path=target_path, content=content)


def launchd_install_artifact(
    *,
    target: AgentTarget = "openclaw",
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
    output_path: str | None = None,
) -> InstallArtifact:
    target_path = (
        Path(output_path)
        if output_path
        else default_service_path("launchd", target)
    )
    content = build_launchd_plist(
        target=target,
        python_path=python_path,
        config_path=config_path,
        interval_seconds=interval_seconds,
        working_directory=working_directory,
    )
    return InstallArtifact(path=target_path, content=content)


def write_install_artifact(artifact: InstallArtifact) -> Path:
    artifact.path.parent.mkdir(parents=True, exist_ok=True)
    artifact.path.write_text(artifact.content, encoding="utf-8")
    return artifact.path


def default_working_directory() -> str:
    return str(Path.home() / ".zhaocai-gateway")


def default_python_path() -> str:
    return str(Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python")


def current_username() -> str:
    return getpass.getuser()


def _writable_or_creatable(path: str | Path) -> bool:
    target = Path(path).expanduser()
    if target.exists():
        return os.access(target, os.W_OK)
    parent = target.parent
    return parent.exists() and os.access(parent, os.W_OK)


def detect_service_manager(system_name: str | None = None) -> str:
    normalized = (system_name or os.uname().sysname).lower()
    if normalized == "darwin":
        return "launchd"
    if normalized == "linux":
        return "systemd"
    raise ValueError(f"Unsupported platform for agent install: {normalized}")


def default_service_path(service_manager: str, target: AgentTarget = "openclaw") -> Path:
    if service_manager == "launchd":
        file_name = "com.zhaocai.hermes-agent.plist" if target == "hermes" else "com.zhaocai.agent.plist"
        return Path.home() / "Library" / "LaunchAgents" / file_name
    file_name = "zhaocai-hermes-agent.service" if target == "hermes" else "zhaocai-agent.service"
    return Path.home() / ".config" / "systemd" / "user" / file_name


def install_artifact_for_manager(
    *,
    service_manager: str,
    target: AgentTarget = "openclaw",
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
    output_path: str | None = None,
) -> InstallArtifact:
    if service_manager == "launchd":
        return launchd_install_artifact(
            target=target,
            python_path=python_path,
            config_path=config_path,
            interval_seconds=interval_seconds,
            working_directory=working_directory,
            output_path=output_path,
        )
    if service_manager == "systemd":
        return systemd_install_artifact(
            target=target,
            python_path=python_path,
            config_path=config_path,
            interval_seconds=interval_seconds,
            working_directory=working_directory,
            output_path=output_path,
        )
    raise ValueError(f"Unsupported service manager: {service_manager}")


def install_next_steps(
    service_manager: str,
    artifact_path: str | Path,
    target: AgentTarget = "openclaw",
) -> list[str]:
    path = str(artifact_path)
    if service_manager == "launchd":
        return [
            f"launchctl unload {path} >/dev/null 2>&1 || true",
            f"launchctl load {path}",
        ]
    service_name = "zhaocai-hermes-agent.service" if target == "hermes" else "zhaocai-agent.service"
    return [
        "systemctl --user daemon-reload",
        f"systemctl --user enable --now {service_name}",
        f"systemctl --user status {service_name}",
    ]


def collect_doctor_checks(
    *,
    config_path: str | Path = DEFAULT_AGENT_CONFIG_PATH,
    target: AgentTarget = "openclaw",
    service_manager: str | None = None,
    service_path: str | Path | None = None,
    working_directory: str | Path | None = None,
    command_lookup=None,
) -> list[DoctorCheck]:
    lookup = command_lookup or shutil.which
    manager = service_manager or detect_service_manager()
    config_file = Path(config_path).expanduser()
    checks: list[DoctorCheck] = []
    effective_target = target

    if config_file.exists():
        try:
            config = load_agent_config(config_file)
            effective_target = config.target
            checks.append(DoctorCheck("agent 配置", True, f"已找到 {config_file}"))
            output_path = Path(config.output_path).expanduser()
            reload_command = config.reload_command
        except Exception as exc:
            checks.append(DoctorCheck("agent 配置", False, f"配置文件不可读取: {exc}"))
            output_path = default_output_path_for(target).expanduser()
            reload_command = ""
    else:
        checks.append(DoctorCheck("agent 配置", False, f"未找到 {config_file}"))
        output_path = default_output_path_for(target).expanduser()
        reload_command = ""

    resolved_service_path = (
        Path(service_path).expanduser()
        if service_path
        else default_service_path(manager, effective_target)
    )

    output_dir = output_path.parent
    output_writable = _writable_or_creatable(output_dir)
    output_label = "Hermes 配置目录" if effective_target == "hermes" else "OpenClaw 配置目录"
    checks.append(
        DoctorCheck(
            output_label,
            output_writable,
            f"{output_dir} {'可写' if output_writable else '不可写'}",
        )
    )

    if reload_command:
        try:
            executable = shlex.split(reload_command)[0]
        except ValueError as exc:
            checks.append(DoctorCheck("重启命令", False, f"命令格式错误: {exc}"))
        else:
            resolved = executable if Path(executable).exists() else lookup(executable)
            checks.append(
                DoctorCheck(
                    "重启命令",
                    bool(resolved),
                    f"{reload_command} {'可用' if resolved else '未找到'}",
                )
            )
    else:
        checks.append(DoctorCheck("重启命令", False, "未配置 reload_command"))

    checks.append(
        DoctorCheck(
            f"{manager} 服务文件",
            resolved_service_path.exists(),
            f"{resolved_service_path} {'已存在' if resolved_service_path.exists() else '未生成'}",
        )
    )

    working_directory_path = Path(working_directory or default_working_directory()).expanduser()
    working_directory_ok = _writable_or_creatable(working_directory_path)
    checks.append(
        DoctorCheck(
            "工作目录",
            working_directory_ok,
            f"{working_directory_path} {'可写' if working_directory_ok else '不可写'}",
        )
    )

    return checks
