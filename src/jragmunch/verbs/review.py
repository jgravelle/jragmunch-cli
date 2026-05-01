"""`jragmunch review` - diff-aware PR review using jcodemunch slice retrieval."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import gitctx
from ..mcp_config import as_inline_json
from ..runtime import mcp_inline
from ..parsers import StreamResult
from ..runner import RunSpec, run


SYSTEM_PREAMBLE = (
    "You are reviewing a code change. Use jcodemunch MCP tools to retrieve "
    "context for each changed symbol: get_changed_symbols, get_blast_radius, "
    "get_call_hierarchy, get_symbol_source. Do NOT read whole files. "
    "For each finding, report: severity (low|med|high), file:line, the "
    "concrete risk, and a suggested fix. Group by severity. Be terse."
)


@dataclass
class ReviewRequest:
    repo: Path
    base: str = "main"
    head: str = "HEAD"
    severity: str = "low"
    model: str | None = None


@dataclass
class ReviewResponse:
    base: str
    head: str
    changed_files: list[str]
    result: str
    meta: dict
    error: str | None = None


def _build_prompt(req: ReviewRequest, summary: gitctx.DiffSummary) -> str:
    parts = [SYSTEM_PREAMBLE, ""]
    parts.append(f"Repo: {req.repo}")
    parts.append(f"Base: {req.base}    Head: {req.head}")
    parts.append(f"Minimum severity to report: {req.severity}")
    parts.append("")
    parts.append("Changed files:")
    for f in summary.changed_files[:200]:
        parts.append(f"  - {f}")
    parts.append("")
    parts.append("Diffstat:")
    parts.append(summary.diffstat or "(empty)")
    parts.append("")
    parts.append(
        "Steps: (1) call get_changed_symbols between base and head; "
        "(2) for each high-impact symbol, call get_blast_radius; "
        "(3) inspect with get_symbol_source as needed; "
        "(4) emit findings grouped by severity."
    )
    return "\n".join(parts)


def execute(req: ReviewRequest) -> ReviewResponse:
    if not gitctx.is_repo(req.repo):
        return ReviewResponse(
            base=req.base,
            head=req.head,
            changed_files=[],
            result="",
            meta={},
            error=f"{req.repo} is not a git repository",
        )
    summary = gitctx.summarize_diff(req.repo, req.base, req.head)
    if not summary.changed_files:
        return ReviewResponse(
            base=req.base,
            head=req.head,
            changed_files=[],
            result="No changed files between base and head.",
            meta={},
        )
    spec = RunSpec(
        prompt=_build_prompt(req, summary),
        mcp_config_inline=mcp_inline(),
        add_dirs=[req.repo],
        model=req.model,
        cwd=req.repo,
    )
    result = run(spec)
    return _to_response(req, summary, result)


def _to_response(
    req: ReviewRequest, summary: gitctx.DiffSummary, result: StreamResult
) -> ReviewResponse:
    return ReviewResponse(
        base=req.base,
        head=req.head,
        changed_files=summary.changed_files,
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
