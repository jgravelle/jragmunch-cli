"""Git helpers for verbs that need diffs / changed files / tags.

Pure subprocess wrappers; never mutate the repo.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout


@dataclass
class DiffSummary:
    base: str
    head: str
    changed_files: list[str]
    diffstat: str


def is_repo(repo: Path) -> bool:
    out = _git(repo, "rev-parse", "--is-inside-work-tree").strip()
    return out == "true"


def current_branch(repo: Path) -> str:
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()


def changed_files(repo: Path, base: str, head: str = "HEAD") -> list[str]:
    out = _git(repo, "diff", "--name-only", f"{base}...{head}")
    return [line for line in out.splitlines() if line.strip()]


def diffstat(repo: Path, base: str, head: str = "HEAD") -> str:
    return _git(repo, "diff", "--stat", f"{base}...{head}").strip()


def summarize_diff(repo: Path, base: str, head: str = "HEAD") -> DiffSummary:
    return DiffSummary(
        base=base,
        head=head,
        changed_files=changed_files(repo, base, head),
        diffstat=diffstat(repo, base, head),
    )


def latest_tag(repo: Path) -> str | None:
    out = _git(repo, "describe", "--tags", "--abbrev=0").strip()
    return out or None


def commits_since(repo: Path, since: str, head: str = "HEAD") -> list[str]:
    out = _git(repo, "log", f"{since}..{head}", "--pretty=%h %s")
    return [line for line in out.splitlines() if line.strip()]
