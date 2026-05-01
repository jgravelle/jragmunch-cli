from pathlib import Path

from jragmunch.fanout import FanoutOutcome
from jragmunch.parsers import StreamResult
from jragmunch.verbs import refactor, sweep
from jragmunch.verbs import tests_gen as tg


def _fake_outcome(key: str, text: str, *, error: str | None = None) -> FanoutOutcome:
    r = StreamResult(text=text, tokens_in=10, tokens_out=5, cost_usd=0.001, wall_time_ms=100)
    if error:
        r.error = error
    return FanoutOutcome(key=key, result=r)


def test_refactor_prompt_includes_description_and_target():
    req = refactor.RefactorRequest(repo=Path("."), description="rename foo to bar", targets_query="foo")
    p = refactor._target_prompt(req, "pkg.mod.foo")
    assert "rename foo to bar" in p
    assert "pkg.mod.foo" in p
    assert "unified diff" in p


def test_refactor_aggregate_collects_diffs_and_errors():
    req = refactor.RefactorRequest(repo=Path("."), description="x", targets_query="y")
    outcomes = [
        _fake_outcome("a", "```diff\n--- a\n+++ b\n```"),
        _fake_outcome("b", "", error="boom"),
    ]
    resp = refactor._aggregate(req, ["a", "b"], outcomes)
    assert "a" in resp.diffs
    assert "b" in resp.errors
    assert resp.aggregate_meta["targets"] == 2
    assert resp.aggregate_meta["errors"] == 1


def test_tests_prompt_uses_get_untested_symbols():
    req = tg.TestsRequest(repo=Path("."))
    enum_p = tg._enumerate_prompt(req)
    assert "get_untested_symbols" in enum_p


def test_tests_aggregate_collects_files():
    outcomes = [_fake_outcome("sym1", "```python\n# tests/x.py\n```")]
    resp = tg._aggregate(["sym1"], outcomes)
    assert "sym1" in resp.files
    assert resp.aggregate_meta["targets"] == 1


def test_sweep_validates_action():
    req = sweep.SweepRequest(repo=Path("."), pattern="TODO", action="bogus")
    resp = sweep.execute(req)
    assert resp.errors


def test_sweep_aggregate():
    req = sweep.SweepRequest(repo=Path("."), pattern="TODO", action="report")
    outcomes = [_fake_outcome("a.py:10", "remove this"), _fake_outcome("b.py:20", "keep")]
    resp = sweep._aggregate(req, ["a.py:10", "b.py:20"], outcomes)
    assert len(resp.outputs) == 2
    assert resp.aggregate_meta["occurrences"] == 2
