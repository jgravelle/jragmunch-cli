"""Pinned MCP-config generator.

Produces a minimal `{"mcpServers": {...}}` payload so the spawned `claude -p`
subprocess only sees the servers we want it to see (jcodemunch by default),
regardless of what the user has registered globally.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_JCODEMUNCH_COMMAND = "jcodemunch-mcp"


@dataclass
class McpServerSpec:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {"command": self.command}
        if self.args:
            d["args"] = self.args
        if self.env:
            d["env"] = self.env
        return d


def default_servers() -> dict[str, McpServerSpec]:
    return {
        "jcodemunch": McpServerSpec(command=DEFAULT_JCODEMUNCH_COMMAND),
    }


def build_config(servers: dict[str, McpServerSpec] | None = None) -> dict:
    servers = servers or default_servers()
    return {"mcpServers": {name: spec.to_dict() for name, spec in servers.items()}}


def write_config(path: Path, servers: dict[str, McpServerSpec] | None = None) -> Path:
    cfg = build_config(servers)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return path


def as_inline_json(servers: dict[str, McpServerSpec] | None = None) -> str:
    return json.dumps(build_config(servers))
