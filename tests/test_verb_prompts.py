from pathlib import Path

from jragmunch.gitctx import DiffSummary
from jragmunch.verbs import changelog as cl
from jragmunch.verbs import review


def test_review_prompt_contains_changed_files_and_severity():
    req = review.ReviewRequest(repo=Path("."), base="main", head="HEAD", severity="med")
    summary = DiffSummary(base="main", head="HEAD", changed_files=["a.py", "b/c.py"], diffstat="...")
    p = review._build_prompt(req, summary)
    assert "Minimum severity to report: med" in p
    assert "a.py" in p and "b/c.py" in p
    assert "get_changed_symbols" in p


def test_changelog_prompt_lists_commits_and_format():
    req = cl.ChangelogRequest(repo=Path("."), since="v1.0.0", fmt="json")
    p = cl._build_prompt(req, ["abc1234 fix: thing", "def5678 feat: stuff"])
    assert "v1.0.0" in p
    assert "Output format: json" in p
    assert "abc1234" in p and "def5678" in p
