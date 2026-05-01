"""Token-reduction benchmark: jragmunch (slice retrieval) vs naive file-dump baseline.

Runs both strategies for the same set of questions on the same repo, then
reports tokens_in / tokens_out / cost_usd per strategy and the ratio.

Usage:
    python -m benchmarks.token_reduction --repo PATH --questions questions.txt

The naive baseline disables MCP and instead pre-loads concatenated files into
the prompt. We don't ship that as a verb because it's the anti-pattern this
project exists to replace - it lives only here to quantify the win.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean

from jragmunch.parsers import parse_stream
from jragmunch.runner import RunSpec, run
from jragmunch.runtime import mcp_inline


DEFAULT_QUESTIONS = [
    "What does the public API of this package look like?",
    "Where is configuration loaded and how?",
    "What is the entrypoint and what does it do?",
]


def slice_strategy(repo: Path, question: str) -> dict:
    spec = RunSpec(
        prompt=f"Use jcodemunch tools to answer concisely: {question}",
        mcp_config_inline=mcp_inline(),
        add_dirs=[repo],
        cwd=repo,
    )
    r = run(spec)
    return {
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "cost_usd": r.cost_usd,
        "wall_time_ms": r.wall_time_ms,
        "error": r.error,
    }


def naive_strategy(repo: Path, question: str, max_files: int = 30) -> dict:
    files: list[Path] = []
    for ext in ("*.py", "*.ts", "*.js", "*.go", "*.rs", "*.md"):
        files.extend(repo.rglob(ext))
        if len(files) >= max_files:
            break
    files = files[:max_files]
    blob_parts: list[str] = []
    for f in files:
        try:
            blob_parts.append(f"--- {f.relative_to(repo)} ---\n{f.read_text(errors='ignore')}")
        except Exception:
            continue
    prompt = (
        "Below are file contents from a repo. Answer this question concisely:\n"
        f"{question}\n\n"
        "FILES:\n" + "\n\n".join(blob_parts)
    )
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "stream-json", "--include-partial-messages", "--verbose"],
        capture_output=True,
        text=True,
        cwd=str(repo),
    )
    r = parse_stream(proc.stdout.splitlines())
    return {
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "cost_usd": r.cost_usd,
        "wall_time_ms": r.wall_time_ms,
        "error": r.error,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--questions", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=Path("benchmark_results.json"))
    args = ap.parse_args()

    if args.questions and args.questions.is_file():
        questions = [q.strip() for q in args.questions.read_text().splitlines() if q.strip()]
    else:
        questions = DEFAULT_QUESTIONS

    results: dict = {"repo": str(args.repo), "questions": [], "summary": {}}
    slice_in, naive_in = [], []
    slice_cost, naive_cost = [], []
    for q in questions:
        s = slice_strategy(args.repo, q)
        n = naive_strategy(args.repo, q)
        results["questions"].append({"question": q, "slice": s, "naive": n})
        slice_in.append(s["tokens_in"])
        naive_in.append(n["tokens_in"])
        slice_cost.append(s["cost_usd"])
        naive_cost.append(n["cost_usd"])

    if slice_in and any(slice_in):
        ratio_tokens = mean(naive_in) / max(1, mean(slice_in))
        ratio_cost = mean(naive_cost) / max(1e-9, mean(slice_cost))
        results["summary"] = {
            "avg_tokens_in_slice": mean(slice_in),
            "avg_tokens_in_naive": mean(naive_in),
            "tokens_in_reduction_ratio": ratio_tokens,
            "avg_cost_slice": mean(slice_cost),
            "avg_cost_naive": mean(naive_cost),
            "cost_reduction_ratio": ratio_cost,
        }

    args.out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
