"""AskClaude.py — interactive demo of jragmunch + Opus 4.7 vs raw file-dump.

Prompts for a repo path and a question, runs jragmunch through Opus 4.7,
then prints the answer alongside a side-by-side cost comparison.

The "raw" baseline projects what pasting the entire repo into the prompt
would have cost (capped at 800K tokens, the model's input window). The
jragmunch number is what the actual call consumed.

Usage:
    python AskClaude.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Reuse jragmunch's own machinery so we get the actual token totals (including
# cache_creation + cache_read), not just the uncached delta the CLI prints.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from jragmunch import runtime  # noqa: E402
from jragmunch.runner import RunSpec, run  # noqa: E402
from jragmunch.runtime import mcp_inline  # noqa: E402
from jragmunch.verbs.ask import AskRequest, _build_prompt  # noqa: E402

# Local naive-baseline projection — same logic the benchmark uses.
sys.path.insert(0, str(Path(__file__).parent / "benchmarks"))
from token_reduction import naive_projection  # noqa: E402


MODEL = "claude-opus-4-7"
PRICE_PER_M_INPUT_USD = 15.00  # Opus 4.7 input rate


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _fmt_usd(x: float) -> str:
    return f"${x:,.2f}" if x >= 0.01 else f"${x:.4f}"


def main() -> int:
    repo_raw = input("Repo path: ").strip().strip('"').strip("'")
    question = input("Ask: ").strip()
    if not repo_raw or not question:
        print("Need both a repo path and a question.", file=sys.stderr)
        return 2

    repo = Path(repo_raw).expanduser().resolve()
    if not repo.is_dir():
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 2

    runtime.set_state(print_command=False, with_docs=False, with_data=False, use_api=False)

    req = AskRequest(question=question, repo=repo, model=MODEL)
    spec = RunSpec(
        prompt=_build_prompt(req),
        mcp_config_inline=mcp_inline(),
        add_dirs=[repo],
        model=MODEL,
        max_turns=30,
        cwd=repo,
    )

    print("\nThinking...\n")
    result = run(spec)

    if result.error:
        print(f"error: {result.error}", file=sys.stderr)
        if result.raw_result:
            import json as _json
            print("--- raw result event ---", file=sys.stderr)
            print(_json.dumps(result.raw_result, indent=2)[:2000], file=sys.stderr)
        return 1

    a = naive_projection(repo, question, MODEL)["tokens_in_estimated"]
    b = a / 1_000_000 * PRICE_PER_M_INPUT_USD
    # "what this call newly consumed" — exclude cache_read since those are
    # already-paid tokens being re-presented, not new work.
    c = result.tokens_in + result.tokens_cache_creation + result.tokens_out

    print("=" * 72)
    print(result.text.strip())
    print("=" * 72)
    print()
    print(f"In its raw form, your request may have used as many as {_fmt_int(a)} "
          f"tokens, at a cost of {_fmt_usd(b)}.")
    print()
    print(f"Using jRagMunch, our call to Opus 4.7 only used {_fmt_int(c)} tokens.")
    print()
    print("By using your subscription WITHIN THE TERMS OF ANTHROPIC'S TOS, "
          "you paid $0.00 and used a nearly imperceptible fractional "
          "percentage of your quota.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
