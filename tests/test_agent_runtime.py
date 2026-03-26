from pathlib import Path

from agent.cli import build_parser
from agent.config import DEFAULT_RELOAD_COMMAND, AgentConfig, load_agent_config, save_agent_config
from agent.install import launchd_install_artifact, systemd_install_artifact, write_install_artifact
from agent.openclaw_writer import write_openclaw_config


def test_agent_config_roundtrip(tmp_path: Path):
    config_path = tmp_path / "agent.json"
    config = AgentConfig(
        server_url="https://raspberrypi.tailnet.ts.net",
        sync_token="sync-token",
        device_id=7,
        output_path=str(tmp_path / "openclaw.json"),
        reload_command="",
        last_version=3,
        last_etag='"etag"',
    )

    save_agent_config(config, config_path)
    loaded = load_agent_config(config_path)

    assert loaded.server_url == config.server_url
    assert loaded.sync_token == "sync-token"
    assert loaded.last_version == 3


def test_agent_default_reload_command():
    config = AgentConfig(
        server_url="https://raspberrypi.tailnet.ts.net",
        sync_token="sync-token",
        device_id=1,
    )

    assert config.reload_command == DEFAULT_RELOAD_COMMAND


def test_write_openclaw_config_creates_backup(tmp_path: Path):
    target = tmp_path / "openclaw.json"
    target.write_text('{"old": true}', encoding="utf-8")

    backup_path = write_openclaw_config(target, {"new": True})

    assert backup_path is not None
    assert Path(backup_path).exists()
    assert target.read_text(encoding="utf-8").strip().startswith("{")
    assert '"new": true' in target.read_text(encoding="utf-8").lower()


def test_write_openclaw_config_merges_into_existing_document(tmp_path: Path):
    target = tmp_path / "openclaw.json"
    target.write_text(
        '{"channels":{"telegram":{"enabled":true}},"models":{"providers":{"old":{"api":"openai-completions","models":[]}}}}',
        encoding="utf-8",
    )

    write_openclaw_config(
        target,
        {
            "models": {
                "providers": {
                    "new": {
                        "api": "openai-completions",
                        "models": [{"id": "gpt-4.1", "name": "GPT-4.1"}],
                    }
                }
            },
            "agents": {"defaults": {"model": {"primary": "new/gpt-4.1", "fallbacks": []}}},
        },
    )

    merged = target.read_text(encoding="utf-8")

    assert '"telegram"' in merged
    assert '"old"' in merged
    assert '"new"' in merged
    assert '"primary": "new/gpt-4.1"' in merged


def test_agent_cli_has_expected_commands():
    parser = build_parser()
    subparsers = parser._subparsers._actions[1].choices

    assert sorted(subparsers.keys()) == [
        "install-launchd",
        "install-systemd",
        "register",
        "run",
        "sync-once",
    ]


def test_systemd_install_artifact_content(tmp_path: Path):
    artifact = systemd_install_artifact(
        python_path="/srv/zhaocai/.venv/bin/python",
        config_path="/srv/zhaocai/agent.json",
        interval_seconds=45,
        working_directory="/srv/zhaocai",
        output_path=str(tmp_path / "zhaocai-agent.service"),
    )

    assert "systemctl --user enable --now zhaocai-agent.service" not in artifact.content
    assert "ExecStart=/srv/zhaocai/.venv/bin/python -m agent.cli run --config-path /srv/zhaocai/agent.json --interval 45" in artifact.content


def test_launchd_install_artifact_content(tmp_path: Path):
    artifact = launchd_install_artifact(
        python_path="/Users/donny/.venv/bin/python",
        config_path="/Users/donny/.zhaocai-gateway/agent.json",
        interval_seconds=30,
        working_directory="/Users/donny/.zhaocai-gateway",
        output_path=str(tmp_path / "com.zhaocai.agent.plist"),
    )

    assert "<string>com.zhaocai.agent</string>" in artifact.content
    assert "<string>/Users/donny/.venv/bin/python</string>" in artifact.content
    assert "<string>--interval</string>" in artifact.content
    assert "<string>30</string>" in artifact.content


def test_write_install_artifact(tmp_path: Path):
    artifact = systemd_install_artifact(
        python_path="/srv/zhaocai/.venv/bin/python",
        config_path="/srv/zhaocai/agent.json",
        interval_seconds=60,
        working_directory="/srv/zhaocai",
        output_path=str(tmp_path / "systemd" / "zhaocai-agent.service"),
    )

    path = write_install_artifact(artifact)

    assert path.exists()
    assert "zhaocai-agent.service" in str(path)
