"""`jragmunch sweep` - pattern-driven cleanup (TODO removal, deprecation, etc.)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..fanout import FanoutItem, FanoutOutcome, fan_out
from ..mcp_config import as_inline_json
from ..runner import RunSpec, run as run_subprocess


ACTIONS = ("remove", "annotate", "report")


SYSTEM_PREAMBLE = (
    "You are sweeping ONE occurrence found by a pattern. Use jcodemunch "
    "`get_symbol_source` and `get_blast_radius` for context. Output depends on "
    "action: 'remove' -> emit a unified diff that removes the occurrence and "
    "any now-dead code; 'annotate' -> emit a diff that adds a clarifying "
    "comment; 'report' -> emit a single line of plain text describing what "
    "should be done. Wrap diffs in ```diff fences."
)


@dataclass
class SweepRequest:
    repo: Path
    pattern: str
    action: str = "report"
    parallel: int = 4
    model: str | None = None
    max_targets: int = 100


@dataclass
class SweepResponse:
    pattern: str
    action: str
    occurrences: list[str] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    aggregate_meta: dict = field(default_factory=dict)


def _enumerate_prompt(req: SweepRequest) -> str:
    return (
        f"In {req.repo}, use jcodemunch `search_text` to find occurrences of "
        f"the pattern: {req.pattern!r}. Return up to {req.max_targets} "
        f"newline-separated `file:line` locators and NOTHING else."
    )


def _target_prompt(req: SweepRequest, occurrence: str) -> str:
    return "\n".join(
        [
            SYSTEM_PREAMBLE,
            "",
            f"Repo: {req.repo}",
            f"Pattern: {req.pattern}",
            f"Action: {req.action}",
            f"Occurrence: {occurrence}",
        ]
    )


def _enumerate(req: SweepRequest) -> list[str]:
    spec = RunSpec(
        prompt=_enumerate_prompt(req),
        mcp_config_inline=as_inline_json(),
        add_dirs=[req.repo],
        model=req.model,
        cwd=req.repo,
    )
    result = run_subprocess(spec)
    return [
        line.strip().lstrip("-* ").strip()
        for line in result.text.splitlines()
        if line.strip()
    ][: req.max_targets]


def execute(req: SweepRequest) -> SweepResponse:
    if req.action not in ACTIONS:
        return SweepResponse(
            pattern=req.pattern,
            action=req.action,
            errors={"_": f"action must be one of {ACTIONS}"},
        )
    occurrences = _enumerate(req)
    if not occurrences:
        return SweepResponse(pattern=req.pattern, action=req.action, occurrences=[])
    items = [
        FanoutItem(
            key=occ,
            spec=RunSpec(
                prompt=_target_prompt(req, occ),
                mcp_config_inline=as_inline_json(),
                add_dirs=[req.repo],
                model=req.model,
                cwd=req.repo,
            ),
        )
        for occ in occurrences
    ]
    outcomes = fan_out(items, parallel=req.parallel)
    return _aggregate(req, occurrences, outcomes)


def _aggregate(
    req: SweepRequest, occurrences: list[str], outcomes: list[FanoutOutcome]
) -> SweepResponse:
    resp = SweepResponse(pattern=req.pattern, action=req.action, occurrences=occurrences)
    tokens_in = tokens_out = 0
    cost = 0.0
    wall = 0
    for o in outcomes:
        if o.result.error:
            resp.errors[o.key] = o.result.error
        else:
            resp.outputs[o.key] = o.result.text
        tokens_in += o.result.tokens_in
        tokens_out += o.result.tokens_out
        cost += o.result.cost_usd
        wall = max(wall, o.result.wall_time_ms)
    resp.aggregate_meta = {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost,
        "wall_time_ms": wall,
        "occurrences": len(occurrences),
        "errors": len(resp.errors),
    }
    return resp
