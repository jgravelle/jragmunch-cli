"""Runtime flags shared between CLI layer and verb implementations.

Verbs read from this module so they don't need to thread global flags through
every function signature.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Runtime:
    print_command: bool = False
    with_docs: bool = False
    with_data: bool = False


_state = Runtime()


def set_state(*, print_command: bool = False, with_docs: bool = False, with_data: bool = False) -> None:
    _state.print_command = print_command
    _state.with_docs = with_docs
    _state.with_data = with_data


def get() -> Runtime:
    return _state


def mcp_inline() -> str:
    """Return the inline MCP config JSON honoring current with_docs/with_data flags."""
    from .mcp_config import as_inline_json

    return as_inline_json(with_docs=_state.with_docs, with_data=_state.with_data)
