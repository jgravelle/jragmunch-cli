"""`jragmunch run` - power-user passthrough."""
from __future__ import annotations

from pathlib import Path

from ..defaults import for_verb
from ..mcp_config import as_inline_json
from ..runtime import mcp_inline
from ..parsers import StreamResult
from ..runner import RunSpec, run


def execute(prompt: str, repo: Path | None = None, model: str | None = None) -> StreamResult:
    default_model, max_turns = for_verb("run")
    spec = RunSpec(
        prompt=prompt,
        mcp_config_inline=mcp_inline(),
        add_dirs=[repo] if repo else [],
        model=model or default_model,
        max_turns=max_turns,
        cwd=repo,
    )
    return run(spec)
