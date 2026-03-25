from pathlib import Path

from agent.cli import build_parser
from agent.config import AgentConfig, load_agent_config, save_agent_config
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


def test_write_openclaw_config_creates_backup(tmp_path: Path):
    target = tmp_path / "openclaw.json"
    target.write_text('{"old": true}', encoding="utf-8")

    backup_path = write_openclaw_config(target, {"new": True})

    assert backup_path is not None
    assert Path(backup_path).exists()
    assert target.read_text(encoding="utf-8").strip().startswith("{")
    assert '"new": true' in target.read_text(encoding="utf-8").lower()


def test_agent_cli_has_expected_commands():
    parser = build_parser()
    subparsers = parser._subparsers._actions[1].choices

    assert sorted(subparsers.keys()) == ["register", "run", "sync-once"]
