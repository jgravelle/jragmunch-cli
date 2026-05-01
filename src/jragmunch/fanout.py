"""Parallel subprocess orchestrator for fan-out verbs (refactor, tests, sweep)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from .parsers import StreamResult
from .runner import RunSpec, run


@dataclass
class FanoutItem:
    key: str
    spec: RunSpec


@dataclass
class FanoutOutcome:
    key: str
    result: StreamResult


def fan_out(
    items: list[FanoutItem],
    *,
    parallel: int = 4,
    on_done: Callable[[FanoutOutcome], None] | None = None,
    timeout: float | None = None,
) -> list[FanoutOutcome]:
    outcomes: list[FanoutOutcome] = []
    with ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
        future_to_key = {ex.submit(run, item.spec, timeout=timeout): item.key for item in items}
        for fut in as_completed(future_to_key):
            key = future_to_key[fut]
            res = fut.result()
            outcome = FanoutOutcome(key=key, result=res)
            outcomes.append(outcome)
            if on_done:
                on_done(outcome)
    return outcomes
