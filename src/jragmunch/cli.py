"""jragmunch CLI entrypoint."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from . import __version__, runtime
from .auth import actual_cost, detect_auth
from .verbs import ask as ask_verb
from .verbs import changelog as changelog_verb
from .verbs import doctor as doctor_verb
from .verbs import index as index_verb
from .verbs import refactor as refactor_verb
from .verbs import review as review_verb
from .verbs import run_passthrough
from .verbs import sweep as sweep_verb
from .verbs import tests_gen as tests_verb


app = typer.Typer(
    name="jragmunch",
    help="Maximal token-efficient RAG for headless Claude. Auth-agnostic; slice-level retrieval.",
    no_args_is_help=True,
    add_completion=False,
)


_globals: dict = {"print_command": False, "with_docs": False, "with_data": False}


@app.callback()
def _root(
    print_command: bool = typer.Option(
        False, "--print-command", help="Print the claude -p invocation that would run, then exit."
    ),
    with_docs: bool = typer.Option(False, "--with-docs", help="Also wire jdocmunch MCP."),
    with_data: bool = typer.Option(False, "--with-data", help="Also wire jdatamunch MCP."),
    use_api: bool = typer.Option(
        False,
        "--use-api",
        help=(
            "Bill via the Anthropic API (using ANTHROPIC_API_KEY). "
            "Default OFF: jragmunch strips the API key from the subprocess "
            "env so claude uses your subscription (Max/Pro) and you pay $0."
        ),
    ),
) -> None:
    _globals["print_command"] = print_command
    _globals["with_docs"] = with_docs
    _globals["with_data"] = with_data
    runtime.set_state(
        print_command=print_command,
        with_docs=with_docs,
        with_data=with_data,
        use_api=use_api,
    )


def _finalize_meta(meta: dict) -> dict:
    """Augment a verb's _meta with auth-aware cost fields.

    Adds:
      - cost_notional_usd : what claude reported (would-be API price)
      - cost_actual_usd   : what you were actually billed (0 on subscription)
      - auth_mode         : 'api' | 'subscription'

    Leaves the original cost_usd field alone for back-compat.
    """
    if not meta:
        return meta
    mode = detect_auth()
    notional = float(meta.get("cost_usd", 0.0))
    out = dict(meta)
    out["cost_notional_usd"] = notional
    out["cost_actual_usd"] = actual_cost(notional, mode)
    out["auth_mode"] = mode
    return out


def _emit(meta: dict) -> None:
    """Print cost line to stderr."""
    if not meta:
        return
    mode = detect_auth()
    notional = float(meta.get("cost_usd", 0.0))
    actual = actual_cost(notional, mode)
    line = (
        f"[tokens in={meta.get('tokens_in', 0)} out={meta.get('tokens_out', 0)}  "
        f"cost actual=${actual:.4f} (notional=${notional:.4f}, auth={mode})  "
        f"time={meta.get('wall_time_ms', 0)}ms]"
    )
    typer.echo(line, err=True)


@app.command()
def version() -> None:
    """Print version."""
    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Verify claude CLI + MCP wiring."""
    report = doctor_verb.diagnose()
    typer.echo(report.render())
    raise typer.Exit(code=0 if report.ok else 1)


@app.command()
def ask(
    question: str = typer.Argument(..., help="The question to ask."),
    repo: Optional[Path] = typer.Option(None, "--repo", help="Repo path (default: cwd)."),
    scope: Optional[str] = typer.Option(None, "--scope", help="Optional scope hint (symbol|file|dir)."),
    model: Optional[str] = typer.Option(None, "--model", help="Override model id."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON on stdout."),
) -> None:
    """Retrieval-augmented Q&A over an indexed repo."""
    req = ask_verb.AskRequest(
        question=question,
        repo=repo or Path.cwd(),
        scope=scope,
        model=model,
    )
    resp = ask_verb.execute(req)
    if resp.error:
        typer.echo(f"error: {resp.error}", err=True)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "verb": "ask",
                    "question": resp.question,
                    "result": resp.result,
                    "citations": resp.citations,
                    "_meta": _finalize_meta(resp.meta),
                    "error": resp.error,
                },
                indent=2,
            )
        )
    else:
        typer.echo(resp.result)
        _emit(resp.meta)
    raise typer.Exit(code=1 if resp.error else 0)


@app.command()
def index(
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repo path to index."),
) -> None:
    """Index a repo via jcodemunch."""
    result = index_verb.execute(repo)
    if result.error:
        typer.echo(f"error: {result.error}", err=True)
        raise typer.Exit(code=1)
    typer.echo(result.text)
    _emit(
        {
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": result.cost_usd,
            "wall_time_ms": result.wall_time_ms,
        }
    )


@app.command(name="run")
def run_cmd(
    prompt: str = typer.Argument(..., help="Free-form prompt."),
    repo: Optional[Path] = typer.Option(None, "--repo", help="Repo path."),
    model: Optional[str] = typer.Option(None, "--model", help="Override model id."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON on stdout."),
) -> None:
    """Power-user prompt passthrough with jcodemunch wired in."""
    result = run_passthrough.execute(prompt, repo=repo, model=model)
    meta = {
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost_usd": result.cost_usd,
        "wall_time_ms": result.wall_time_ms,
        "mcp_servers": result.mcp_servers,
        "model": result.model,
    }
    if json_out:
        typer.echo(
            json.dumps(
                {"verb": "run", "result": result.text, "_meta": _finalize_meta(meta), "error": result.error},
                indent=2,
            )
        )
    else:
        if result.error:
            typer.echo(f"error: {result.error}", err=True)
        typer.echo(result.text)
        _emit(meta)
    raise typer.Exit(code=1 if result.error else 0)


@app.command()
def review(
    base: str = typer.Option("main", "--base", help="Base ref to diff against."),
    head: str = typer.Option("HEAD", "--head", help="Head ref."),
    repo: Optional[Path] = typer.Option(None, "--repo", help="Repo path (default: cwd)."),
    severity: str = typer.Option("low", "--severity", help="Minimum severity (low|med|high)."),
    model: Optional[str] = typer.Option(None, "--model", help="Override model id."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON on stdout."),
) -> None:
    """Diff-aware review using jcodemunch slice retrieval."""
    req = review_verb.ReviewRequest(
        repo=repo or Path.cwd(),
        base=base,
        head=head,
        severity=severity,
        model=model,
    )
    resp = review_verb.execute(req)
    if resp.error:
        typer.echo(f"error: {resp.error}", err=True)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "verb": "review",
                    "base": resp.base,
                    "head": resp.head,
                    "changed_files": resp.changed_files,
                    "result": resp.result,
                    "_meta": _finalize_meta(resp.meta),
                    "error": resp.error,
                },
                indent=2,
            )
        )
    else:
        typer.echo(resp.result)
        if resp.meta:
            _emit(resp.meta)
    raise typer.Exit(code=1 if resp.error else 0)


@app.command()
def changelog(
    since: str = typer.Option(..., "--since", help="Tag or ref to start from."),
    head: str = typer.Option("HEAD", "--head", help="Head ref."),
    repo: Optional[Path] = typer.Option(None, "--repo", help="Repo path (default: cwd)."),
    fmt: str = typer.Option("md", "--format", help="Output format: md|json."),
    model: Optional[str] = typer.Option(None, "--model", help="Override model id."),
    json_out: bool = typer.Option(False, "--json", help="Wrap full response in JSON envelope."),
) -> None:
    """Summarize changes since a tag using slice retrieval."""
    req = changelog_verb.ChangelogRequest(
        repo=repo or Path.cwd(),
        since=since,
        head=head,
        fmt=fmt,
        model=model,
    )
    resp = changelog_verb.execute(req)
    if resp.error:
        typer.echo(f"error: {resp.error}", err=True)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "verb": "changelog",
                    "since": resp.since,
                    "head": resp.head,
                    "commits": resp.commits,
                    "result": resp.result,
                    "_meta": _finalize_meta(resp.meta),
                    "error": resp.error,
                },
                indent=2,
            )
        )
    else:
        typer.echo(resp.result)
        if resp.meta:
            _emit(resp.meta)
    raise typer.Exit(code=1 if resp.error else 0)


@app.command()
def refactor(
    description: str = typer.Argument(..., help="Refactor description."),
    targets: str = typer.Option(..., "--targets", help="Search query for refactor targets."),
    repo: Optional[Path] = typer.Option(None, "--repo", help="Repo path (default: cwd)."),
    parallel: int = typer.Option(4, "--parallel", help="Parallel subprocess count."),
    max_targets: int = typer.Option(50, "--max", help="Maximum targets to refactor."),
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Dry-run (default) or apply."),
    model: Optional[str] = typer.Option(None, "--model"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Fan-out batch refactor across matched targets (dry-run by default)."""
    req = refactor_verb.RefactorRequest(
        repo=repo or Path.cwd(),
        description=description,
        targets_query=targets,
        dry_run=dry_run,
        parallel=parallel,
        max_targets=max_targets,
        model=model,
    )
    resp = refactor_verb.execute(req)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "verb": "refactor",
                    "description": resp.description,
                    "targets": resp.targets,
                    "diffs": resp.diffs,
                    "errors": resp.errors,
                    "_meta": _finalize_meta(resp.aggregate_meta),
                    "_meta_per_target": resp.meta_per_target,
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"# Refactor: {resp.description}")
        typer.echo(f"# Targets: {len(resp.targets)} | Errors: {len(resp.errors)}")
        for key, diff in resp.diffs.items():
            typer.echo(f"\n## {key}\n{diff}")
        for key, err in resp.errors.items():
            typer.echo(f"\n## ERROR: {key}\n{err}", err=True)
        _emit(resp.aggregate_meta)
    raise typer.Exit(code=1 if resp.errors and not resp.diffs else 0)


@app.command()
def tests(
    symbols: Optional[str] = typer.Option(None, "--symbols", help="Symbol-name filter."),
    repo: Optional[Path] = typer.Option(None, "--repo"),
    max_targets: int = typer.Option(20, "--max"),
    parallel: int = typer.Option(4, "--parallel"),
    model: Optional[str] = typer.Option(None, "--model"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Generate tests for untested symbols via fan-out."""
    req = tests_verb.TestsRequest(
        repo=repo or Path.cwd(),
        symbols_query=symbols,
        max_targets=max_targets,
        parallel=parallel,
        model=model,
    )
    resp = tests_verb.execute(req)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "verb": "tests",
                    "targets": resp.targets,
                    "files": resp.files,
                    "errors": resp.errors,
                    "_meta": _finalize_meta(resp.aggregate_meta),
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"# Tests generated: {len(resp.files)} | Errors: {len(resp.errors)}")
        for key, body in resp.files.items():
            typer.echo(f"\n## {key}\n{body}")
        for key, err in resp.errors.items():
            typer.echo(f"\n## ERROR: {key}\n{err}", err=True)
        _emit(resp.aggregate_meta)
    raise typer.Exit(code=1 if resp.errors and not resp.files else 0)


@app.command()
def sweep(
    pattern: str = typer.Argument(..., help="Pattern to sweep (e.g. 'TODO\\(remove\\)')."),
    action: str = typer.Option("report", "--action", help="remove|annotate|report"),
    repo: Optional[Path] = typer.Option(None, "--repo"),
    max_targets: int = typer.Option(100, "--max"),
    parallel: int = typer.Option(4, "--parallel"),
    model: Optional[str] = typer.Option(None, "--model"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Pattern-driven cleanup sweep (TODO removal, deprecation migration, etc.)."""
    req = sweep_verb.SweepRequest(
        repo=repo or Path.cwd(),
        pattern=pattern,
        action=action,
        parallel=parallel,
        max_targets=max_targets,
        model=model,
    )
    resp = sweep_verb.execute(req)
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "verb": "sweep",
                    "pattern": resp.pattern,
                    "action": resp.action,
                    "occurrences": resp.occurrences,
                    "outputs": resp.outputs,
                    "errors": resp.errors,
                    "_meta": _finalize_meta(resp.aggregate_meta),
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"# Sweep: {resp.pattern} ({resp.action})")
        typer.echo(f"# Occurrences: {len(resp.occurrences)} | Errors: {len(resp.errors)}")
        for key, body in resp.outputs.items():
            typer.echo(f"\n## {key}\n{body}")
        for key, err in resp.errors.items():
            typer.echo(f"\n## ERROR: {key}\n{err}", err=True)
        _emit(resp.aggregate_meta)
    raise typer.Exit(code=1 if resp.errors and not resp.outputs else 0)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
