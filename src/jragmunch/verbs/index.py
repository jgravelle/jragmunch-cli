"""`jragmunch index` - delegate to jcodemunch's index_folder."""
from __future__ import annotations

from pathlib import Path

from ..mcp_config import as_inline_json
from ..parsers import StreamResult
from ..runner import RunSpec, run


def execute(repo: Path) -> StreamResult:
    prompt = (
        f"Use the jcodemunch MCP tool `index_folder` to index the folder at "
        f"{repo}. Then call `list_repos` and report the repo id and symbol count."
    )
    spec = RunSpec(
        prompt=prompt,
        mcp_config_inline=as_inline_json(),
        add_dirs=[repo],
        cwd=repo,
    )
    return run(spec, timeout=600)
