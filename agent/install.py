from __future__ import annotations

import getpass
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil

from agent.config import DEFAULT_AGENT_CONFIG_PATH, DEFAULT_OUTPUT_PATH, load_agent_config


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
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
) -> str:
    return f"""[Unit]
Description=Zhaocai Gateway Node Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={working_directory}
ExecStart={python_path} -m agent.cli run --config-path {config_path} --interval {interval_seconds}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""


def build_launchd_plist(
    *,
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
) -> str:
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
  <dict>
    <key>Label</key>
    <string>com.zhaocai.agent</string>
    <key>ProgramArguments</key>
    <array>
      <string>{python_path}</string>
      <string>-m</string>
      <string>agent.cli</string>
      <string>run</string>
      <string>--config-path</string>
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
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
    output_path: str | None = None,
) -> InstallArtifact:
    target = (
        Path(output_path)
        if output_path
        else Path.home() / ".config" / "systemd" / "user" / "zhaocai-agent.service"
    )
    content = build_systemd_service(
        python_path=python_path,
        config_path=config_path,
        interval_seconds=interval_seconds,
        working_directory=working_directory,
    )
    return InstallArtifact(path=target, content=content)


def launchd_install_artifact(
    *,
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
    output_path: str | None = None,
) -> InstallArtifact:
    target = (
        Path(output_path)
        if output_path
        else Path.home() / "Library" / "LaunchAgents" / "com.zhaocai.agent.plist"
    )
    content = build_launchd_plist(
        python_path=python_path,
        config_path=config_path,
        interval_seconds=interval_seconds,
        working_directory=working_directory,
    )
    return InstallArtifact(path=target, content=content)


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


def default_service_path(service_manager: str) -> Path:
    if service_manager == "launchd":
        return Path.home() / "Library" / "LaunchAgents" / "com.zhaocai.agent.plist"
    return Path.home() / ".config" / "systemd" / "user" / "zhaocai-agent.service"


def install_artifact_for_manager(
    *,
    service_manager: str,
    python_path: str,
    config_path: str,
    interval_seconds: int,
    working_directory: str,
    output_path: str | None = None,
) -> InstallArtifact:
    if service_manager == "launchd":
        return launchd_install_artifact(
            python_path=python_path,
            config_path=config_path,
            interval_seconds=interval_seconds,
            working_directory=working_directory,
            output_path=output_path,
        )
    if service_manager == "systemd":
        return systemd_install_artifact(
            python_path=python_path,
            config_path=config_path,
            interval_seconds=interval_seconds,
            working_directory=working_directory,
            output_path=output_path,
        )
    raise ValueError(f"Unsupported service manager: {service_manager}")


def install_next_steps(service_manager: str, artifact_path: str | Path) -> list[str]:
    path = str(artifact_path)
    if service_manager == "launchd":
        return [
            f"launchctl unload {path} >/dev/null 2>&1 || true",
            f"launchctl load {path}",
        ]
    return [
        "systemctl --user daemon-reload",
        "systemctl --user enable --now zhaocai-agent.service",
        "systemctl --user status zhaocai-agent.service",
    ]


def collect_doctor_checks(
    *,
    config_path: str | Path = DEFAULT_AGENT_CONFIG_PATH,
    service_manager: str | None = None,
    service_path: str | Path | None = None,
    working_directory: str | Path | None = None,
    command_lookup=None,
) -> list[DoctorCheck]:
    lookup = command_lookup or shutil.which
    manager = service_manager or detect_service_manager()
    config_file = Path(config_path).expanduser()
    resolved_service_path = Path(service_path).expanduser() if service_path else default_service_path(manager)
    checks: list[DoctorCheck] = []

    if config_file.exists():
        try:
            config = load_agent_config(config_file)
            checks.append(DoctorCheck("agent 配置", True, f"已找到 {config_file}"))
            output_path = Path(config.output_path).expanduser()
            reload_command = config.reload_command
        except Exception as exc:
            checks.append(DoctorCheck("agent 配置", False, f"配置文件不可读取: {exc}"))
            output_path = Path(DEFAULT_OUTPUT_PATH).expanduser()
            reload_command = ""
    else:
        checks.append(DoctorCheck("agent 配置", False, f"未找到 {config_file}"))
        output_path = Path(DEFAULT_OUTPUT_PATH).expanduser()
        reload_command = ""

    output_dir = output_path.parent
    output_writable = _writable_or_creatable(output_dir)
    checks.append(
        DoctorCheck(
            "OpenClaw 配置目录",
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
