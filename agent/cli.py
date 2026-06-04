from __future__ import annotations

import argparse
import platform
import socket
from pathlib import Path

from agent.client import AgentClient
from agent.config import (
    AgentConfig,
    AgentTarget,
    default_agent_config_path_for,
    default_output_path_for,
    default_reload_command_for,
    load_agent_config,
    save_agent_config,
)
from agent.install import (
    collect_doctor_checks,
    default_python_path,
    default_working_directory,
    detect_service_manager,
    install_artifact_for_manager,
    install_next_steps,
    launchd_install_artifact,
    systemd_install_artifact,
    write_install_artifact,
)
from agent.sync import run_sync_loop, sync_once


def _add_target_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        choices=["openclaw", "hermes"],
        default="openclaw",
        help="Target runtime to manage",
    )


def _resolve_config_path(raw_path: str, target: AgentTarget) -> str:
    return raw_path or str(default_agent_config_path_for(target))


def _resolve_output_path(raw_path: str, target: AgentTarget) -> str:
    return raw_path or str(default_output_path_for(target))


def _resolve_reload_command(raw_command: str, target: AgentTarget) -> str:
    return raw_command or default_reload_command_for(target)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Zhaocai Gateway node agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register this node with the control plane")
    _add_target_argument(register)
    register.add_argument("--server", required=True, help="Base URL for the control plane")
    register.add_argument("--token", required=True, help="One-time pairing token")
    register.add_argument(
        "--config-path",
        default="",
        help="Where to save the agent config",
    )
    register.add_argument(
        "--output-path",
        default="",
        help="Target config output path",
    )
    register.add_argument(
        "--reload-cmd",
        default="",
        help="Optional command to reload the target runtime after config updates",
    )
    register.add_argument("--hostname", default=socket.gethostname(), help="Hostname to register")
    register.add_argument("--platform", default=platform.system().lower(), help="Platform label to register")

    sync_once_parser = subparsers.add_parser("sync-once", help="Run a single config sync")
    _add_target_argument(sync_once_parser)
    sync_once_parser.add_argument(
        "--config-path",
        default="",
        help="Agent config path",
    )

    run_parser = subparsers.add_parser("run", help="Run the sync loop")
    _add_target_argument(run_parser)
    run_parser.add_argument(
        "--config-path",
        default="",
        help="Agent config path",
    )
    run_parser.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")

    install_parser = subparsers.add_parser(
        "install",
        help="Generate the recommended background service file for this platform",
    )
    _add_target_argument(install_parser)
    install_parser.add_argument(
        "--config-path",
        default="",
        help="Agent config path",
    )
    install_parser.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")
    install_parser.add_argument(
        "--python-path",
        default=default_python_path(),
        help="Python interpreter path used by the service",
    )
    install_parser.add_argument(
        "--working-directory",
        default=default_working_directory(),
        help="Working directory for runtime logs and state",
    )
    install_parser.add_argument(
        "--service-manager",
        choices=["auto", "systemd", "launchd"],
        default="auto",
        help="Override the detected background service manager",
    )
    install_parser.add_argument(
        "--output",
        default="",
        help="Optional explicit output path for the generated service file",
    )

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check whether this node is ready for background sync",
    )
    _add_target_argument(doctor_parser)
    doctor_parser.add_argument(
        "--config-path",
        default="",
        help="Agent config path",
    )
    doctor_parser.add_argument(
        "--service-manager",
        choices=["auto", "systemd", "launchd"],
        default="auto",
        help="Override the detected background service manager",
    )
    doctor_parser.add_argument(
        "--service-path",
        default="",
        help="Optional explicit service definition path to check",
    )
    doctor_parser.add_argument(
        "--working-directory",
        default=default_working_directory(),
        help="Working directory to check for logs and runtime state",
    )

    install_systemd = subparsers.add_parser(
        "install-systemd",
        help="Generate a systemd user service file for the node agent",
    )
    _add_target_argument(install_systemd)
    install_systemd.add_argument(
        "--config-path",
        default="",
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
    _add_target_argument(install_launchd)
    install_launchd.add_argument(
        "--config-path",
        default="",
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
    config_path = _resolve_config_path(args.config_path, args.target)
    output_path = _resolve_output_path(args.output_path, args.target)
    reload_command = _resolve_reload_command(args.reload_cmd, args.target)
    client = AgentClient(args.server, target=args.target)
    result = client.register(
        pairing_token=args.token,
        hostname=args.hostname,
        platform=args.platform,
    )
    config = AgentConfig(
        server_url=args.server,
        sync_token=result["sync_token"],
        device_id=int(result["device"]["id"]),
        target=args.target,
        output_path=output_path,
        reload_command=reload_command,
    )
    config_path = save_agent_config(config, config_path)
    print(f"registered device_id={config.device_id}")
    print(f"config saved to {config_path}")
    return 0


def handle_sync_once(args: argparse.Namespace) -> int:
    config_path = Path(_resolve_config_path(args.config_path, args.target))
    config = load_agent_config(config_path)
    client = AgentClient(config.server_url, target=config.target)
    result = sync_once(config, client, persist_path=str(config_path))
    state = "updated" if result.changed else "unchanged"
    print(f"sync {state} version={result.version} etag={result.etag}")
    if result.backup_path:
        print(f"backup={result.backup_path}")
    return 0


def handle_run(args: argparse.Namespace) -> int:
    config_path = Path(_resolve_config_path(args.config_path, args.target))
    config = load_agent_config(config_path)
    client = AgentClient(config.server_url, target=config.target)
    run_sync_loop(config, client, persist_path=str(config_path), interval_seconds=args.interval)
    return 0


def handle_install(args: argparse.Namespace) -> int:
    try:
        service_manager = (
            detect_service_manager(platform.system())
            if args.service_manager == "auto"
            else args.service_manager
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    artifact = install_artifact_for_manager(
        service_manager=service_manager,
        target=args.target,
        python_path=args.python_path,
        config_path=_resolve_config_path(args.config_path, args.target),
        interval_seconds=args.interval,
        working_directory=args.working_directory,
        output_path=args.output or None,
    )
    path = write_install_artifact(artifact)
    print(f"{service_manager} service written to {path}")
    print("next:")
    for step in install_next_steps(service_manager, path, target=args.target):
        print(f"  {step}")
    return 0


def handle_install_systemd(args: argparse.Namespace) -> int:
    artifact = systemd_install_artifact(
        target=args.target,
        python_path=args.python_path,
        config_path=_resolve_config_path(args.config_path, args.target),
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
        target=args.target,
        python_path=args.python_path,
        config_path=_resolve_config_path(args.config_path, args.target),
        interval_seconds=args.interval,
        working_directory=args.working_directory,
        output_path=args.output or None,
    )
    path = write_install_artifact(artifact)
    print(f"launchd plist written to {path}")
    print(f"next: launchctl load {path}")
    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    try:
        service_manager = (
            detect_service_manager(platform.system())
            if args.service_manager == "auto"
            else args.service_manager
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    checks = collect_doctor_checks(
        config_path=_resolve_config_path(args.config_path, args.target),
        target=args.target,
        service_manager=service_manager,
        service_path=args.service_path or None,
        working_directory=args.working_directory,
    )
    ok = True
    print(f"service manager: {service_manager}")
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")
        ok = ok and check.ok
    return 0 if ok else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "register":
        return handle_register(args)
    if args.command == "sync-once":
        return handle_sync_once(args)
    if args.command == "run":
        return handle_run(args)
    if args.command == "install":
        return handle_install(args)
    if args.command == "install-systemd":
        return handle_install_systemd(args)
    if args.command == "install-launchd":
        return handle_install_launchd(args)
    if args.command == "doctor":
        return handle_doctor(args)

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
