"""`jragmunch tests` - generate tests for untested symbols via fan-out."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..fanout import FanoutItem, FanoutOutcome, fan_out
from ..mcp_config import as_inline_json
from ..runner import RunSpec, run as run_subprocess


SYSTEM_PREAMBLE = (
    "Generate tests for ONE target symbol. Use jcodemunch "
    "`get_symbol_source`, `get_call_hierarchy`, and `get_related_symbols` "
    "to understand inputs, outputs, and usage. Emit ONLY the test file "
    "contents in a single fenced code block, with the file path on the "
    "first line as a comment. Use the project's existing test framework."
)


@dataclass
class TestsRequest:
    repo: Path
    symbols_query: str | None = None
    max_targets: int = 20
    parallel: int = 4
    model: str | None = None


@dataclass
class TestsResponse:
    targets: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    aggregate_meta: dict = field(default_factory=dict)


def _enumerate_prompt(req: TestsRequest) -> str:
    if req.symbols_query:
        return (
            f"In {req.repo}, list up to {req.max_targets} symbols matching "
            f"{req.symbols_query!r} that lack tests. Use jcodemunch "
            f"`get_untested_symbols` first; filter via `search_symbols` if "
            f"needed. Return ONLY newline-separated fully-qualified names. No prose."
        )
    return (
        f"In {req.repo}, list up to {req.max_targets} highest-importance "
        f"untested symbols using jcodemunch `get_untested_symbols` ranked by "
        f"`get_symbol_importance`. Return ONLY newline-separated names. No prose."
    )


def _target_prompt(req: TestsRequest, target: str) -> str:
    return "\n".join(
        [
            SYSTEM_PREAMBLE,
            "",
            f"Repo: {req.repo}",
            f"Target symbol: {target}",
            "",
            "Output: a single fenced code block containing the test file. "
            "First line of the block must be a comment with the intended "
            "file path (e.g., `# tests/test_foo.py`).",
        ]
    )


def _enumerate_targets(req: TestsRequest) -> list[str]:
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


def execute(req: TestsRequest) -> TestsResponse:
    targets = _enumerate_targets(req)
    if not targets:
        return TestsResponse(targets=[])
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
    return _aggregate(targets, outcomes)


def _aggregate(targets: list[str], outcomes: list[FanoutOutcome]) -> TestsResponse:
    resp = TestsResponse(targets=targets)
    tokens_in = tokens_out = 0
    cost = 0.0
    wall = 0
    for o in outcomes:
        if o.result.error:
            resp.errors[o.key] = o.result.error
        else:
            resp.files[o.key] = o.result.text
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
