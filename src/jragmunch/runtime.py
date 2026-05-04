"""Runtime flags shared between CLI layer and verb implementations.

Verbs read from this module so they don't need to thread global flags through
every function signature.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Runtime:
    print_command: bool = False
    with_docs: bool = False
    with_data: bool = False
    use_api: bool = False  # default: subscription auth (no API key billing)
    config_dir: Path | None = None  # explicit override for CLAUDE_CONFIG_DIR


_state = Runtime()


def set_state(
    *,
    print_command: bool = False,
    with_docs: bool = False,
    with_data: bool = False,
    use_api: bool = False,
    config_dir: Path | None = None,
) -> None:
    _state.print_command = print_command
    _state.with_docs = with_docs
    _state.with_data = with_data
    _state.use_api = use_api
    _state.config_dir = config_dir


def get() -> Runtime:
    return _state


def mcp_inline() -> str:
    """Return the inline MCP config JSON honoring current with_docs/with_data flags."""
    from .mcp_config import as_inline_json

    return as_inline_json(with_docs=_state.with_docs, with_data=_state.with_data)
