"""`jragmunch index` - delegate to jcodemunch's index_folder."""
from __future__ import annotations

from pathlib import Path

from ..defaults import for_verb
from ..mcp_config import as_inline_json
from ..runtime import mcp_inline
from ..parsers import StreamResult
from ..runner import RunSpec, run


def execute(repo: Path) -> StreamResult:
    prompt = (
        f"Use the jcodemunch MCP tool `index_folder` to index the folder at "
        f"{repo}. Then call `list_repos` and report the repo id and symbol count."
    )
    default_model, max_turns = for_verb("index")
    spec = RunSpec(
        prompt=prompt,
        mcp_config_inline=mcp_inline(),
        add_dirs=[repo],
        model=default_model,
        max_turns=max_turns,
        cwd=repo,
    )
    return run(spec, timeout=600)
