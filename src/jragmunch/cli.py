"""jragmunch CLI entrypoint."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .verbs import ask as ask_verb
from .verbs import changelog as changelog_verb
from .verbs import doctor as doctor_verb
from .verbs import index as index_verb
from .verbs import review as review_verb
from .verbs import run_passthrough


app = typer.Typer(
    name="jragmunch",
    help="Maximal token-efficient RAG for headless Claude. Auth-agnostic; slice-level retrieval.",
    no_args_is_help=True,
    add_completion=False,
)


def _emit(meta: dict) -> None:
    """Print cost line to stderr."""
    line = (
        f"[tokens in={meta.get('tokens_in', 0)} out={meta.get('tokens_out', 0)}  "
        f"cost=${meta.get('cost_usd', 0.0):.4f}  "
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
                    "_meta": resp.meta,
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
                {"verb": "run", "result": result.text, "_meta": meta, "error": result.error},
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
                    "_meta": resp.meta,
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
                    "_meta": resp.meta,
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
