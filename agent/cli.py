from __future__ import annotations

import argparse
import platform
import socket
from pathlib import Path

from agent.client import AgentClient
from agent.config import (
    DEFAULT_AGENT_CONFIG_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_RELOAD_COMMAND,
    AgentConfig,
    load_agent_config,
    save_agent_config,
)
from agent.install import (
    default_python_path,
    default_working_directory,
    launchd_install_artifact,
    systemd_install_artifact,
    write_install_artifact,
)
from agent.sync import run_sync_loop, sync_once


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Zhaocai Gateway node agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register this node with the control plane")
    register.add_argument("--server", required=True, help="Base URL for the control plane")
    register.add_argument("--token", required=True, help="One-time pairing token")
    register.add_argument(
        "--config-path",
        default=str(DEFAULT_AGENT_CONFIG_PATH),
        help="Where to save the agent config",
    )
    register.add_argument(
        "--output-path",
        default=str(DEFAULT_OUTPUT_PATH),
        help="OpenClaw config target path",
    )
    register.add_argument(
        "--reload-cmd",
        default=DEFAULT_RELOAD_COMMAND,
        help="Optional command to reload OpenClaw after config updates",
    )
    register.add_argument("--hostname", default=socket.gethostname(), help="Hostname to register")
    register.add_argument("--platform", default=platform.system().lower(), help="Platform label to register")

    sync_once_parser = subparsers.add_parser("sync-once", help="Run a single config sync")
    sync_once_parser.add_argument(
        "--config-path",
        default=str(DEFAULT_AGENT_CONFIG_PATH),
        help="Agent config path",
    )

    run_parser = subparsers.add_parser("run", help="Run the sync loop")
    run_parser.add_argument(
        "--config-path",
        default=str(DEFAULT_AGENT_CONFIG_PATH),
        help="Agent config path",
    )
    run_parser.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")

    install_systemd = subparsers.add_parser(
        "install-systemd",
        help="Generate a systemd user service file for the node agent",
    )
    install_systemd.add_argument(
        "--config-path",
        default=str(DEFAULT_AGENT_CONFIG_PATH),
        help="Agent config path",
    )
    install_systemd.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")
    install_systemd.add_argument(
        "--python-path",
        default=default_python_path(),
        help="Python interpreter path used by the service",
    )
    install_systemd.add_argument(
        "--working-directory",
        default=default_working_directory(),
        help="Working directory for runtime logs and state",
    )
    install_systemd.add_argument(
        "--output",
        default="",
        help="Optional explicit output path for the generated service file",
    )

    install_launchd = subparsers.add_parser(
        "install-launchd",
        help="Generate a launchd plist for the node agent",
    )
    install_launchd.add_argument(
        "--config-path",
        default=str(DEFAULT_AGENT_CONFIG_PATH),
        help="Agent config path",
    )
    install_launchd.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")
    install_launchd.add_argument(
        "--python-path",
        default=default_python_path(),
        help="Python interpreter path used by launchd",
    )
    install_launchd.add_argument(
        "--working-directory",
        default=default_working_directory(),
        help="Working directory for runtime logs and state",
    )
    install_launchd.add_argument(
        "--output",
        default="",
        help="Optional explicit output path for the generated plist",
    )

    return parser


def handle_register(args: argparse.Namespace) -> int:
    client = AgentClient(args.server)
    result = client.register(
        pairing_token=args.token,
        hostname=args.hostname,
        platform=args.platform,
    )
    config = AgentConfig(
        server_url=args.server,
        sync_token=result["sync_token"],
        device_id=int(result["device"]["id"]),
        output_path=args.output_path,
        reload_command=args.reload_cmd,
    )
    config_path = save_agent_config(config, args.config_path)
    print(f"registered device_id={config.device_id}")
    print(f"config saved to {config_path}")
    return 0


def handle_sync_once(args: argparse.Namespace) -> int:
    config_path = Path(args.config_path)
    config = load_agent_config(config_path)
    client = AgentClient(config.server_url)
    result = sync_once(config, client, persist_path=str(config_path))
    state = "updated" if result.changed else "unchanged"
    print(f"sync {state} version={result.version} etag={result.etag}")
    if result.backup_path:
        print(f"backup={result.backup_path}")
    return 0


def handle_run(args: argparse.Namespace) -> int:
    config_path = Path(args.config_path)
    config = load_agent_config(config_path)
    client = AgentClient(config.server_url)
    run_sync_loop(config, client, persist_path=str(config_path), interval_seconds=args.interval)
    return 0


def handle_install_systemd(args: argparse.Namespace) -> int:
    artifact = systemd_install_artifact(
        python_path=args.python_path,
        config_path=args.config_path,
        interval_seconds=args.interval,
        working_directory=args.working_directory,
        output_path=args.output or None,
    )
    path = write_install_artifact(artifact)
    print(f"systemd service written to {path}")
    print("next: systemctl --user daemon-reload && systemctl --user enable --now zhaocai-agent.service")
    return 0


def handle_install_launchd(args: argparse.Namespace) -> int:
    artifact = launchd_install_artifact(
        python_path=args.python_path,
        config_path=args.config_path,
        interval_seconds=args.interval,
        working_directory=args.working_directory,
        output_path=args.output or None,
    )
    path = write_install_artifact(artifact)
    print(f"launchd plist written to {path}")
    print(f"next: launchctl load {path}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "register":
        return handle_register(args)
    if args.command == "sync-once":
        return handle_sync_once(args)
    if args.command == "run":
        return handle_run(args)
    if args.command == "install-systemd":
        return handle_install_systemd(args)
    if args.command == "install-launchd":
        return handle_install_launchd(args)

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
