"""`jragmunch changelog` - summarize changes since a tag using slice retrieval."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import gitctx
from ..defaults import for_verb
from ..mcp_config import as_inline_json
from ..runtime import mcp_inline
from ..parsers import StreamResult
from ..runner import RunSpec, run


SYSTEM_PREAMBLE = (
    "You produce a changelog from git history and code-level changes. Use "
    "jcodemunch tools (get_changed_symbols, get_symbol_diff) to identify "
    "what actually changed at the API level, not just what files moved. "
    "Group entries under: Added, Changed, Fixed, Removed, Internal. Be terse."
)


@dataclass
class ChangelogRequest:
    repo: Path
    since: str
    head: str = "HEAD"
    fmt: str = "md"  # md|json
    model: str | None = None


@dataclass
class ChangelogResponse:
    since: str
    head: str
    commits: list[str]
    result: str
    meta: dict
    error: str | None = None


def _build_prompt(req: ChangelogRequest, commits: list[str]) -> str:
    parts = [SYSTEM_PREAMBLE, ""]
    parts.append(f"Repo: {req.repo}")
    parts.append(f"Since: {req.since}    Head: {req.head}")
    parts.append(f"Output format: {req.fmt}")
    parts.append("")
    parts.append("Commits in range:")
    for c in commits[:500]:
        parts.append(f"  {c}")
    parts.append("")
    parts.append(
        "Use get_changed_symbols between the two refs to find API-level changes. "
        "Then emit a changelog. If format is 'md', emit GitHub-flavored markdown "
        "with H2 sections. If 'json', emit a JSON object with arrays per category."
    )
    return "\n".join(parts)


def execute(req: ChangelogRequest) -> ChangelogResponse:
    if not gitctx.is_repo(req.repo):
        return ChangelogResponse(
            since=req.since,
            head=req.head,
            commits=[],
            result="",
            meta={},
            error=f"{req.repo} is not a git repository",
        )
    commits = gitctx.commits_since(req.repo, req.since, req.head)
    if not commits:
        return ChangelogResponse(
            since=req.since,
            head=req.head,
            commits=[],
            result=f"No commits between {req.since} and {req.head}.",
            meta={},
        )
    default_model, max_turns = for_verb("changelog")
    spec = RunSpec(
        prompt=_build_prompt(req, commits),
        mcp_config_inline=mcp_inline(),
        add_dirs=[req.repo],
        model=req.model or default_model,
        max_turns=max_turns,
        cwd=req.repo,
    )
    result = run(spec)
    return _to_response(req, commits, result)


def _to_response(
    req: ChangelogRequest, commits: list[str], result: StreamResult
) -> ChangelogResponse:
    return ChangelogResponse(
        since=req.since,
        head=req.head,
        commits=commits,
        result=result.text,
        meta={
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_usd,
            "wall_time_ms": result.wall_time_ms,
            "mcp_servers": result.mcp_servers,
            "model": result.model,
        },
        error=result.error,
    )
