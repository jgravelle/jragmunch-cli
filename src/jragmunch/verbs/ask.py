"""`jragmunch ask` - retrieval-augmented Q&A over an indexed repo."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mcp_config import as_inline_json
from ..parsers import StreamResult
from ..runner import RunSpec, run


SYSTEM_PREAMBLE = (
    "You answer questions about a code repository. "
    "ALWAYS use jcodemunch MCP tools (search_symbols, get_symbol_source, "
    "get_file_outline, get_call_hierarchy, search_text) to retrieve only the "
    "slices you need. Do NOT read whole files unless a tool result tells you to. "
    "Cite each claim with file paths and symbol names you actually retrieved."
)


@dataclass
class AskRequest:
    question: str
    repo: Path | None = None
    scope: str | None = None  # symbol|file|dir hint
    model: str | None = None


@dataclass
class AskResponse:
    question: str
    result: str
    citations: list[dict]
    meta: dict
    error: str | None = None


def _build_prompt(req: AskRequest) -> str:
    parts = [SYSTEM_PREAMBLE, ""]
    if req.repo:
        parts.append(f"Working repo: {req.repo}")
    if req.scope:
        parts.append(f"Scope hint: {req.scope}")
    parts.append("")
    parts.append("Question:")
    parts.append(req.question)
    parts.append("")
    parts.append(
        "End your answer with a 'Citations:' section listing each "
        "(symbol, file, line-range) you relied on."
    )
    return "\n".join(parts)


def execute(req: AskRequest) -> AskResponse:
    spec = RunSpec(
        prompt=_build_prompt(req),
        mcp_config_inline=as_inline_json(),
        add_dirs=[req.repo] if req.repo else [],
        model=req.model,
        cwd=req.repo,
    )
    result = run(spec)
    return _to_response(req, result)


def _to_response(req: AskRequest, result: StreamResult) -> AskResponse:
    return AskResponse(
        question=req.question,
        result=result.text,
        citations=[],  # v0.1: parsing of citations from result text deferred
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
