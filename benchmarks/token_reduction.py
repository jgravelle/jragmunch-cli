"""Token-reduction benchmark: jragmunch (slice retrieval) vs naive file-dump baseline.

The slice strategy actually runs through `claude -p` with jcodemunch wired
in. The naive baseline is *projected*: we measure what dumping the same
files into a prompt would cost (using tiktoken or a char-based estimator)
without actually paying to send it. That's faithful to the comparison
because the naive anti-pattern is the same regardless of model — we just
need its input-token count and the model's per-token price.

Usage:
    python -m benchmarks.token_reduction --repo PATH [--questions FILE]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

from jragmunch.runner import RunSpec, run
from jragmunch.runtime import mcp_inline


DEFAULT_QUESTIONS = [
    "What does the public API of this package look like?",
    "Where is configuration loaded and how?",
    "What is the entrypoint and what does it do?",
]

# Pricing per 1M input tokens, in USD. Anchor to whatever model the slice
# strategy used so the comparison is apples-to-apples.
PRICE_PER_M_INPUT = {
    "claude-haiku-4-5-20251001": 1.00,
    "claude-sonnet-4-6": 3.00,
    "claude-opus-4-7": 15.00,
}


def _estimate_tokens(text: str) -> int:
    """Cheap, deterministic token estimator. Tries tiktoken; falls back to
    chars/3.5, which lands within ~10% of Claude's tokenizer for code/prose.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, int(len(text) / 3.5))


def slice_strategy(repo: Path, question: str) -> dict:
    spec = RunSpec(
        prompt=f"Use jcodemunch tools to answer concisely: {question}",
        mcp_config_inline=mcp_inline(),
        add_dirs=[repo],
        cwd=repo,
    )
    r = run(spec)
    return {
        "tokens_in_total": r.tokens_in_total,
        "tokens_in_uncached": r.tokens_in,
        "tokens_cache_creation": r.tokens_cache_creation,
        "tokens_cache_read": r.tokens_cache_read,
        "tokens_out": r.tokens_out,
        "cost_usd": r.cost_usd,
        "wall_time_ms": r.wall_time_ms,
        "model": r.model,
        "error": r.error,
    }


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "target"}


def naive_projection(repo: Path, question: str, model: str, max_tokens: int = 800_000) -> dict:
    """Estimate what a naive 'dump the repo into the prompt' baseline would
    cost. Mirrors what a developer without RAG would paste: as many relevant
    source files as fit in context. Capped at `max_tokens` so we don't claim
    a baseline larger than the model's window.

    Doesn't call claude — would blow Windows arg limits and burns money to
    measure something we can compute locally. Uses tiktoken when available,
    else a chars/3.5 heuristic.
    """
    candidates: list[Path] = []
    for ext in ("*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs", "*.java", "*.md"):
        for f in repo.rglob(ext):
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            candidates.append(f)

    blob_parts: list[str] = []
    running_tokens = 0
    files_included = 0
    for f in candidates:
        try:
            body = f.read_text(errors="ignore")
        except Exception:
            continue
        chunk = f"--- {f.relative_to(repo)} ---\n{body}"
        chunk_tokens = _estimate_tokens(chunk)
        if running_tokens + chunk_tokens > max_tokens:
            break
        blob_parts.append(chunk)
        running_tokens += chunk_tokens
        files_included += 1

    prompt = (
        "Below are file contents from a repo. Answer this question concisely:\n"
        f"{question}\n\n"
        "FILES:\n" + "\n\n".join(blob_parts)
    )
    tokens = _estimate_tokens(prompt)
    price = PRICE_PER_M_INPUT.get(model, 1.00)
    return {
        "files_available": len(candidates),
        "files_included": files_included,
        "tokens_in_estimated": tokens,
        "cost_usd_projected": tokens / 1_000_000 * price,
        "estimator": "tiktoken-cl100k_base" if "tiktoken" in sys.modules else "chars/3.5",
        "capped_at_tokens": max_tokens,
        "price_anchor_model": model,
        "price_per_m_input_usd": price,
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
    model_used = ""
    for q in questions:
        s = slice_strategy(args.repo, q)
        model_used = s.get("model") or model_used or "claude-haiku-4-5-20251001"
        n = naive_projection(args.repo, q, model_used)
        results["questions"].append({"question": q, "slice": s, "naive": n})
        slice_in.append(s["tokens_in_total"])
        naive_in.append(n["tokens_in_estimated"])
        slice_cost.append(s["cost_usd"])
        naive_cost.append(n["cost_usd_projected"])

    if slice_in and any(slice_in):
        ratio_cost = mean(naive_cost) / max(1e-9, mean(slice_cost))
        ratio_tokens = mean(naive_in) / max(1, mean(slice_in))
        n_questions = len(questions)
        results["summary"] = {
            "model": model_used,
            "questions": n_questions,
            "avg_cost_slice_actual_usd": round(mean(slice_cost), 4),
            "avg_cost_naive_projected_usd": round(mean(naive_cost), 4),
            "cost_reduction_x": round(ratio_cost, 2),
            "total_cost_slice_actual_usd": round(sum(slice_cost), 4),
            "total_cost_naive_projected_usd": round(sum(naive_cost), 4),
            "avg_tokens_in_slice_actual": int(mean(slice_in)),
            "avg_tokens_in_naive_projected": int(mean(naive_in)),
            "tokens_in_reduction_x": round(ratio_tokens, 2),
            "headline": (
                f"{ratio_cost:.1f}x cheaper per question on this repo "
                f"(${mean(slice_cost):.2f} vs ${mean(naive_cost):.2f}, model={model_used})"
            ),
            "note": (
                "naive baseline = entire repo source pasted into prompt, capped at 800K tokens, "
                "priced at the model's uncached input rate. Slice cost is what claude actually "
                "billed (cache pricing included). Token counts are not directly comparable "
                "because slice loads MCP tool definitions; lead with the cost figure."
            ),
        }

    args.out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
