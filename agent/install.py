from __future__ import annotations

import getpass
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstallArtifact:
    path: Path
    content: str


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
