"""`jragmunch doctor` - verify claude CLI + MCP wiring."""
from __future__ import annotations

from dataclasses import dataclass

from ..mcp_config import as_inline_json
from ..parsers import has_server
from ..runner import RunSpec, claude_path, run


@dataclass
class DoctorReport:
    claude_found: bool
    claude_path: str | None
    jcodemunch_loaded: bool
    mcp_servers: list[str]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.claude_found and self.jcodemunch_loaded and self.error is None

    def render(self) -> str:
        lines: list[str] = []
        lines.append(f"claude CLI:      {'OK ' + (self.claude_path or '') if self.claude_found else 'NOT FOUND on PATH'}")
        lines.append(f"jcodemunch MCP:  {'loaded' if self.jcodemunch_loaded else 'NOT LOADED'}")
        if self.mcp_servers:
            lines.append(f"MCP servers:     {', '.join(self.mcp_servers)}")
        if self.error:
            lines.append(f"error:           {self.error}")
        lines.append("")
        lines.append("status: " + ("READY" if self.ok else "NOT READY"))
        return "\n".join(lines)


def diagnose() -> DoctorReport:
    cp = claude_path()
    if cp is None:
        return DoctorReport(
            claude_found=False,
            claude_path=None,
            jcodemunch_loaded=False,
            mcp_servers=[],
            error="`claude` not on PATH. Install with: npm install -g @anthropic-ai/claude-code",
        )
    spec = RunSpec(
        prompt="ping. respond with 'pong' and nothing else.",
        mcp_config_inline=as_inline_json(),
    )
    result = run(spec, timeout=60)
    return DoctorReport(
        claude_found=True,
        claude_path=cp,
        jcodemunch_loaded=has_server(result, "jcodemunch"),
        mcp_servers=result.mcp_servers,
        error=result.error,
    )
