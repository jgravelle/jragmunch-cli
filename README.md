# jragmunch-cli

**Maximal token-efficient RAG for headless Claude.** Uses your existing `claude` CLI; auth-agnostic; slice-level retrieval powered by [jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp).

## Why

Headless Claude (`claude -p`) is the right substrate for code automation — CI bots, batch refactors, fan-out agents, internal "chat with your repo" services. The default pattern is "stuff the relevant files into the prompt and pray," which burns tokens on code the model never needed.

`jragmunch` wraps `claude -p` with jcodemunch pre-wired so the model retrieves slices on demand instead of receiving giant context dumps.

## Install

```bash
pip install jragmunch
jragmunch doctor
```

Requires the `claude` CLI on PATH (`npm install -g @anthropic-ai/claude-code`) and [jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp) registered as an MCP server.

## Usage

```bash
jragmunch ask "how does auth work in this repo"
jragmunch ask "what does AuthMiddleware.verify do" --json
jragmunch index --repo .
jragmunch run "Refactor the rate-limiter to use a token bucket"
```

## Verbs (v0.1)

| Verb | Status | Purpose |
|------|--------|---------|
| `doctor` | shipped | Verify `claude` + MCP wiring |
| `ask` | shipped | Retrieval-augmented Q&A |
| `index` | shipped | Index a repo via jcodemunch |
| `run` | shipped | Power-user prompt passthrough |
| `review` | shipped | Diff-aware PR review |
| `changelog` | shipped | Summarize changes since tag |
| `refactor` | shipped | Fan-out batch refactor |
| `tests` | shipped | Generate tests for untested symbols |
| `sweep` | shipped | Pattern-driven cleanup |

See [PRD.md](PRD.md) for the full product spec.

## Principles

- **Auth-agnostic.** Whatever auth the local `claude` binary uses, jragmunch uses.
- **Slice, don't dump.** Default behavior is jcodemunch retrieval.
- **Structured output.** Every verb returns JSON with citations and `_meta` (tokens, cost, wall time).
- **Composable.** `--print-command` shows the exact `claude -p` invocation that would run.

## License

Apache 2.0
