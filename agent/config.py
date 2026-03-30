from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_AGENT_CONFIG_PATH = Path.home() / ".zhaocai-gateway" / "agent.json"
DEFAULT_OUTPUT_PATH = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_RELOAD_COMMAND = "openclaw gateway restart"


def default_preserve_path_for(output_path: str | Path = DEFAULT_OUTPUT_PATH) -> Path:
    return Path(output_path).expanduser().with_name("zhaocai-preserve.json")


DEFAULT_PRESERVE_PATH = default_preserve_path_for(DEFAULT_OUTPUT_PATH)


@dataclass
class AgentConfig:
    server_url: str
    sync_token: str
    device_id: int
    output_path: str = str(DEFAULT_OUTPUT_PATH)
    preserve_path: str = ""
    reload_command: str = DEFAULT_RELOAD_COMMAND
    last_version: int = 0
    last_etag: str = ""

    def __post_init__(self) -> None:
        if not self.preserve_path:
            self.preserve_path = str(default_preserve_path_for(self.output_path))


def load_agent_config(path: str | Path = DEFAULT_AGENT_CONFIG_PATH) -> AgentConfig:
    config_path = Path(path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return AgentConfig(**payload)


def save_agent_config(
    config: AgentConfig,
    path: str | Path = DEFAULT_AGENT_CONFIG_PATH,
) -> Path:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return config_path
