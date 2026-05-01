"""The `claude -p` subprocess driver.

This is the only module that touches `subprocess`. Everything else operates on
`StreamResult` objects so verbs and tests stay pure.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .parsers import StreamResult, parse_stream


DEFAULT_ALLOWED_TOOLS = [
    "mcp__jcodemunch__*",
    "mcp__jcodemunch-mcp__*",  # match user's globally-registered name variant
    "Read",
    "Glob",
    "Grep",
]


@dataclass
class RunSpec:
    prompt: str
    allowed_tools: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_TOOLS))
    mcp_config_path: Path | None = None
    mcp_config_inline: str | None = None
    add_dirs: list[Path] = field(default_factory=list)
    model: str | None = None
    permission_mode: str = "default"
    cwd: Path | None = None
    extra_args: list[str] = field(default_factory=list)


def claude_path() -> str | None:
    return shutil.which("claude")


def build_argv(spec: RunSpec) -> list[str]:
    claude = claude_path() or "claude"
    argv: list[str] = [claude, "-p", spec.prompt]
    argv += ["--output-format", "stream-json", "--include-partial-messages", "--verbose"]
    if spec.allowed_tools:
        argv += ["--allowedTools", ",".join(spec.allowed_tools)]
    if spec.mcp_config_path:
        argv += ["--mcp-config", str(spec.mcp_config_path), "--strict-mcp-config"]
    elif spec.mcp_config_inline:
        argv += ["--mcp-config", spec.mcp_config_inline, "--strict-mcp-config"]
    for d in spec.add_dirs:
        argv += ["--add-dir", str(d)]
    if spec.model:
        argv += ["--model", spec.model]
    if spec.permission_mode and spec.permission_mode != "default":
        argv += ["--permission-mode", spec.permission_mode]
    argv += spec.extra_args
    return argv


def _build_subprocess_env(use_api: bool) -> dict[str, str]:
    """Return the env dict for the spawned claude. Strips ANTHROPIC_API_KEY /
    ANTHROPIC_AUTH_TOKEN unless --use-api was set, so claude falls back to
    subscription (OAuth) auth and the user is not billed.
    """
    env = dict(os.environ)
    if not use_api:
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
    return env


def run(spec: RunSpec, *, timeout: float | None = None) -> StreamResult:
    from . import runtime  # local import to avoid cycle

    if runtime.get().print_command:
        return StreamResult(text=format_command(spec))
    argv = build_argv(spec)
    proc = subprocess.run(
        argv,
        cwd=str(spec.cwd) if spec.cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        env=_build_subprocess_env(runtime.get().use_api),
    )
    result = parse_stream(proc.stdout.splitlines())
    if proc.returncode != 0 and not result.error:
        result.error = (
            f"claude exited with code {proc.returncode}. stderr: {proc.stderr.strip()[:500]}"
        )
    return result


def format_command(spec: RunSpec) -> str:
    """Human-readable rendering of the argv we would invoke. For --print-command."""
    argv = build_argv(spec)
    parts: list[str] = []
    for a in argv:
        if any(c in a for c in ' "\n'):
            parts.append('"' + a.replace('"', '\\"') + '"')
        else:
            parts.append(a)
    return " ".join(parts)
