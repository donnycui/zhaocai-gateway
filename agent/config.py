from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


AgentTarget = Literal["openclaw", "hermes"]

DEFAULT_AGENT_CONFIG_PATH = Path.home() / ".zhaocai-gateway" / "agent.json"
DEFAULT_HERMES_AGENT_CONFIG_PATH = Path.home() / ".zhaocai-gateway" / "hermes-agent.json"
DEFAULT_OUTPUT_PATH = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_HERMES_OUTPUT_PATH = Path.home() / ".hermes" / "config.yaml"
DEFAULT_RELOAD_COMMAND = "openclaw gateway restart"
DEFAULT_HERMES_RELOAD_COMMAND = (
    "systemctl --user restart hermes-gateway && "
    "systemctl --user restart hermes-webui"
)


def default_agent_config_path_for(target: AgentTarget = "openclaw") -> Path:
    if target == "hermes":
        return DEFAULT_HERMES_AGENT_CONFIG_PATH
    return DEFAULT_AGENT_CONFIG_PATH


def default_output_path_for(target: AgentTarget = "openclaw") -> Path:
    if target == "hermes":
        return DEFAULT_HERMES_OUTPUT_PATH
    return DEFAULT_OUTPUT_PATH


def default_reload_command_for(target: AgentTarget = "openclaw") -> str:
    if target == "hermes":
        return DEFAULT_HERMES_RELOAD_COMMAND
    return DEFAULT_RELOAD_COMMAND


def default_preserve_path_for(output_path: str | Path = DEFAULT_OUTPUT_PATH) -> Path:
    return Path(output_path).expanduser().with_name("zhaocai-preserve.json")


DEFAULT_PRESERVE_PATH = default_preserve_path_for(DEFAULT_OUTPUT_PATH)


@dataclass
class AgentConfig:
    server_url: str
    sync_token: str
    device_id: int
    target: AgentTarget = "openclaw"
    output_path: str = ""
    preserve_path: str = ""
    reload_command: str | None = None
    last_version: int = 0
    last_etag: str = ""

    def __post_init__(self) -> None:
        if self.target not in {"openclaw", "hermes"}:
            raise ValueError(f"Unsupported agent target: {self.target}")
        if not self.output_path:
            self.output_path = str(default_output_path_for(self.target))
        if self.reload_command is None:
            self.reload_command = default_reload_command_for(self.target)
        if self.target == "openclaw" and not self.preserve_path:
            self.preserve_path = str(default_preserve_path_for(self.output_path))
        if self.target == "hermes":
            self.preserve_path = ""


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
