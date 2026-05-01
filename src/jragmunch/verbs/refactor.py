"""`jragmunch refactor` - fan-out batch refactor across matched targets.

Strategy:
  1. Use jcodemunch search_symbols / search_text to enumerate targets.
  2. Spawn one subprocess per target with narrow context.
  3. Each subprocess emits a unified diff in stdout (dry-run by default).
  4. Aggregator collects diffs into a single patch file or applies them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..fanout import FanoutItem, FanoutOutcome, fan_out
from ..mcp_config import as_inline_json
from ..runner import RunSpec


SYSTEM_PREAMBLE = (
    "You are performing a focused refactor on ONE target symbol or file. "
    "Use jcodemunch tools (get_symbol_source, get_call_hierarchy, "
    "get_blast_radius) to retrieve context. Then emit a unified diff and "
    "NOTHING ELSE. Wrap the diff in a single fenced ```diff block. Do not "
    "modify files yourself."
)


@dataclass
class RefactorRequest:
    repo: Path
    description: str
    targets_query: str  # jcodemunch search_symbols query OR ripgrep pattern
    dry_run: bool = True
    parallel: int = 4
    model: str | None = None
    max_targets: int = 50


@dataclass
class RefactorResponse:
    description: str
    targets: list[str] = field(default_factory=list)
    diffs: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    meta_per_target: dict[str, dict] = field(default_factory=dict)
    aggregate_meta: dict = field(default_factory=dict)


def _enumerate_prompt(req: RefactorRequest) -> str:
    return (
        f"List up to {req.max_targets} concrete refactor targets in {req.repo} "
        f"matching the query: {req.targets_query!r}. Use jcodemunch "
        f"`search_symbols` (preferred) or `search_text` to find them. "
        f"Return ONLY a newline-separated list of fully-qualified symbol names "
        f"or file:line locators. No prose."
    )


def _target_prompt(req: RefactorRequest, target: str) -> str:
    return "\n".join(
        [
            SYSTEM_PREAMBLE,
            "",
            f"Repo: {req.repo}",
            f"Target: {target}",
            f"Refactor description: {req.description}",
            "",
            "Emit only a unified diff in a fenced ```diff block.",
        ]
    )


def _enumerate_targets(req: RefactorRequest) -> list[str]:
    from ..runner import run as run_subprocess

    spec = RunSpec(
        prompt=_enumerate_prompt(req),
        mcp_config_inline=as_inline_json(),
        add_dirs=[req.repo],
        model=req.model,
        cwd=req.repo,
    )
    result = run_subprocess(spec)
    targets = [
        line.strip().lstrip("-* ").strip()
        for line in result.text.splitlines()
        if line.strip()
    ]
    return targets[: req.max_targets]


def execute(req: RefactorRequest) -> RefactorResponse:
    targets = _enumerate_targets(req)
    if not targets:
        return RefactorResponse(description=req.description, targets=[])

    items = [
        FanoutItem(
            key=t,
            spec=RunSpec(
                prompt=_target_prompt(req, t),
                mcp_config_inline=as_inline_json(),
                add_dirs=[req.repo],
                model=req.model,
                cwd=req.repo,
            ),
        )
        for t in targets
    ]
    outcomes = fan_out(items, parallel=req.parallel)
    return _aggregate(req, targets, outcomes)


def _aggregate(
    req: RefactorRequest, targets: list[str], outcomes: list[FanoutOutcome]
) -> RefactorResponse:
    resp = RefactorResponse(description=req.description, targets=targets)
    tokens_in = tokens_out = 0
    cost = 0.0
    wall = 0
    for o in outcomes:
        if o.result.error:
            resp.errors[o.key] = o.result.error
        else:
            resp.diffs[o.key] = o.result.text
        resp.meta_per_target[o.key] = {
            "tokens_in": o.result.tokens_in,
            "tokens_out": o.result.tokens_out,
            "cost_usd": o.result.cost_usd,
            "wall_time_ms": o.result.wall_time_ms,
        }
        tokens_in += o.result.tokens_in
        tokens_out += o.result.tokens_out
        cost += o.result.cost_usd
        wall = max(wall, o.result.wall_time_ms)
    resp.aggregate_meta = {
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost,
        "wall_time_ms": wall,
        "targets": len(targets),
        "errors": len(resp.errors),
    }
    return resp
