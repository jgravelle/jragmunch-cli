"""`jragmunch run` - power-user passthrough."""
from __future__ import annotations

from pathlib import Path

from ..mcp_config import as_inline_json
from ..runtime import mcp_inline
from ..parsers import StreamResult
from ..runner import RunSpec, run


def execute(prompt: str, repo: Path | None = None, model: str | None = None) -> StreamResult:
    spec = RunSpec(
        prompt=prompt,
        mcp_config_inline=mcp_inline(),
        add_dirs=[repo] if repo else [],
        model=model,
        cwd=repo,
    )
    return run(spec)
