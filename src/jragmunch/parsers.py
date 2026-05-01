"""Stream-json event parser for `claude -p --output-format stream-json`.

Each line of stdout is a JSON object. We care about three event kinds:

- `system` with `subtype: "init"` — reports loaded MCP servers; used to verify wiring.
- `assistant` / `user` deltas — accumulated to reconstruct the final answer if needed.
- `result` — terminal event with cost, tokens, duration, and the final text.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, Iterator


@dataclass
class StreamResult:
    text: str = ""
    mcp_servers: list[str] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    wall_time_ms: int = 0
    model: str = ""
    raw_init: dict | None = None
    raw_result: dict | None = None
    error: str | None = None


def iter_events(lines: Iterable[str]) -> Iterator[dict]:
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def parse_stream(lines: Iterable[str]) -> StreamResult:
    out = StreamResult()
    for ev in iter_events(lines):
        kind = ev.get("type")
        if kind == "system" and ev.get("subtype") == "init":
            out.raw_init = ev
            servers = ev.get("mcp_servers") or []
            if isinstance(servers, list):
                out.mcp_servers = [
                    s.get("name", "") if isinstance(s, dict) else str(s) for s in servers
                ]
            out.model = ev.get("model", out.model)
        elif kind == "result":
            out.raw_result = ev
            out.text = ev.get("result", "") or out.text
            usage = ev.get("usage") or {}
            out.tokens_in = int(usage.get("input_tokens", 0))
            out.tokens_out = int(usage.get("output_tokens", 0))
            out.cost_usd = float(ev.get("total_cost_usd", 0.0))
            out.wall_time_ms = int(ev.get("duration_ms", 0))
            if ev.get("is_error"):
                out.error = ev.get("result") or "claude reported is_error=true"
    return out


def has_server(result: StreamResult, name: str) -> bool:
    return any(s.lower() == name.lower() for s in result.mcp_servers)
