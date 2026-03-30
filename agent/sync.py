from __future__ import annotations

import time
from dataclasses import dataclass

from agent.client import AgentClient
from agent.config import AgentConfig, save_agent_config
from agent.openclaw_writer import run_reload_command, write_openclaw_config


@dataclass
class SyncResult:
    changed: bool
    version: int
    etag: str
    backup_path: str | None = None


def sync_once(config: AgentConfig, client: AgentClient, *, persist_path: str | None = None) -> SyncResult:
    meta = client.get_config_meta(sync_token=config.sync_token)
    version = int(meta["version"])
    etag = str(meta["etag"])

    if config.last_version == version and config.last_etag == etag:
        return SyncResult(changed=False, version=version, etag=etag)

    payload = client.get_config(sync_token=config.sync_token)
    backup_path = write_openclaw_config(
        config.output_path,
        payload,
        preserve_path=config.preserve_path,
    )
    run_reload_command(config.reload_command)
    client.report_applied(sync_token=config.sync_token, version=version, status="applied")

    config.last_version = version
    config.last_etag = etag
    if persist_path is not None:
        save_agent_config(config, persist_path)

    return SyncResult(
        changed=True,
        version=version,
        etag=etag,
        backup_path=backup_path,
    )


def run_sync_loop(
    config: AgentConfig,
    client: AgentClient,
    *,
    persist_path: str,
    interval_seconds: int = 60,
) -> None:
    while True:
        sync_once(config, client, persist_path=persist_path)
        time.sleep(max(1, interval_seconds))
