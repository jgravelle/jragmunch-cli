# PRD: jRAGmunch-CLI

> **Maximal token-efficient RAG for headless Claude. Uses your existing `claude` CLI; auth-agnostic; slice-level retrieval.**

---

## 1. Context & Motivation

### The problem
Headless Claude (`claude -p`) is the right substrate for code automation — CI bots, batch refactors, fan-out agents, internal "chat with your repo" services. But every team that builds on it hits the same wall: **context bloat**. The default pattern is "stuff the relevant files into the prompt and pray," which:

- Burns tokens on code the model never needed.
- Fills the window before the model can reason.
- Forces brittle hand-rolled retrieval (grep + heuristics) per project.
- Produces shallower answers than interactive Claude Code, because Claude Code itself uses MCP-driven retrieval that headless callers usually don't replicate.

Meanwhile, **jcodemunch-mcp** already solves slice-level retrieval — `search_symbols`, `get_symbol_source`, `get_blast_radius`, `get_changed_symbols`, and ~80 more — and it's tool-callable from any Claude session, including headless. The two pieces fit together; nobody has packaged the join.

### The opportunity
A thin, opinionated CLI that wraps `claude -p` with jcodemunch (and optionally jdocmunch, jdatamunch) pre-wired, with sane allowlists, structured output, and ergonomic verbs (`ask`, `review`, `refactor`, `sweep`, `tests`). The CLI is auth-agnostic: whatever the local `claude` binary is configured to use, jragmunch uses. No new auth surface, no API-key handling, no embeddings infra to stand up.

### Intended outcome
- A single `pip install jragmunch` (or `npm i -g`) that gives any developer slice-level RAG over their codebase via headless Claude.
- A composable building block for fan-out automation: PR review bots, doc-drift watchers, batch refactors, test generators, multi-repo sweeps.
- A flagship demonstration of the jmunch suite — every feature is grounded in a real MCP server we already ship.

### Non-goals
- **Not** a replacement for Claude Code's interactive TUI.
- **Not** a hosted service or daemon (v1 is local CLI only).
- **Not** an API-key management layer; we delegate entirely to `claude`.
- **Not** a vector DB or embeddings product; jcodemunch already handles retrieval.

---

## 2. Users & Use Cases

### Primary personas
1. **Solo dev / power user** — wants `jragmunch ask "how does auth work here"` to answer in 30s without burning their interactive context.
2. **Platform/DevEx engineer** — wires `jragmunch review` into CI, `jragmunch sweep` into scheduled cleanup jobs.
3. **Agent builder** — uses `jragmunch` as a subprocess primitive inside larger automation, parses its JSON output.

### Anchor use cases
| # | Scenario | Verb |
|---|----------|------|
| 1 | "Explain this symbol / file / subsystem" | `ask` |
| 2 | "Review this PR / diff / branch" | `review` |
| 3 | "Apply this rename / migration across the repo" | `refactor` |
| 4 | "Generate tests for untested symbols" | `tests` |
| 5 | "Sweep TODOs / deprecations / dead code" | `sweep` |
| 6 | "Summarize what changed since tag X" | `changelog` |
| 7 | "Answer arbitrary question, return JSON" | `ask --json` (programmatic) |

---

## 3. Product Principles

1. **Auth-agnostic.** Never touch credentials. `claude` is the auth boundary.
2. **Slice, don't dump.** Default behavior is jcodemunch retrieval; whole-file reads are an opt-in escape hatch.
3. **Structured output by default.** Every verb returns parseable JSON; pretty rendering is a flag.
4. **Composable, not magical.** Each verb is a thin wrapper over a documented `claude -p` invocation. `--print-command` shows exactly what would run.
5. **Fail loud, fail fast.** If jcodemunch isn't loaded, error before spending tokens. Parse `system/init` from stream-json to verify MCP wiring.
6. **No lock-in.** All state lives in user's existing `claude` config + jcodemunch index. Uninstalling jragmunch leaves nothing behind.

---

## 4. Functional Requirements

### 4.1 CLI surface (v1)

```
jragmunch ask       <question> [--repo PATH] [--scope <symbol|file|dir>] [--json]
jragmunch review    [--base BRANCH] [--pr N] [--severity low|med|high]
jragmunch refactor  <description> [--dry-run] [--targets QUERY]
jragmunch tests     [--symbols QUERY] [--max N]
jragmunch sweep     <pattern> [--action remove|annotate|report]
jragmunch changelog [--since TAG] [--format md|json]
jragmunch index     [--repo PATH]                # delegate to jcodemunch index_folder
jragmunch doctor                                 # verify claude CLI + MCP wiring
jragmunch run       <free-form prompt>           # power-user passthrough
```

Global flags: `--mcp-config`, `--allowed-tools`, `--add-dir`, `--model`, `--output json|text|stream`, `--print-command`, `--verbose`.

### 4.2 Behavior

- **Auto-index.** On first invocation in a repo, check `list_repos`. If absent, prompt to run `jragmunch index` (or auto-index with `--yes`).
- **MCP allowlist.** Default `--allowedTools` is `mcp__jcodemunch__*,Read,Glob,Grep`. Extendable via config or flag.
- **MCP config pinning.** `--mcp-config` accepts a path or inline JSON; defaults to a minimal pinned set (jcodemunch only) so user's other MCP servers don't leak in and slow startup.
- **Init verification.** Use `--output-format stream-json --include-partial-messages`; read `system/init`; abort with a clear error if jcodemunch isn't connected.
- **Cost reporting.** Every verb prints `tokens_in / tokens_out / cost_usd / wall_time` (parsed from `result` event) on stderr. JSON output includes them under `_meta`.
- **Permission mode.** Default `--permission-mode default` (prompts blocked → fail fast). `--yolo` maps to `bypassPermissions` for trusted CI.
- **Fan-out.** `refactor`, `tests`, `sweep` support `--parallel N` to spawn N subprocesses, each with narrow context. Aggregator merges results.

### 4.3 Configuration

`~/.jragmunch/config.toml`:
```toml
[defaults]
model = "claude-opus-4-7"
allowed_tools = ["mcp__jcodemunch__*", "Read", "Glob", "Grep"]
parallel = 4
output = "text"

[mcp]
config_path = "~/.jragmunch/mcp.json"   # pinned MCP set

[verbs.review]
severity_threshold = "med"
include_blast_radius = true
```

Per-repo override at `<repo>/.jragmunch.toml`.

### 4.4 Output contract

Every verb's `--output json` returns:
```json
{
  "verb": "ask",
  "question": "...",
  "result": "...",            // markdown answer
  "citations": [               // jcodemunch retrieval trail
    { "symbol": "AuthMiddleware.verify", "file": "src/auth.ts", "lines": "42-87" }
  ],
  "_meta": {
    "tokens_in": 1840, "tokens_out": 612,
    "cost_usd": 0.0231, "wall_time_ms": 4210,
    "mcp_servers": ["jcodemunch"],
    "model": "claude-opus-4-7"
  }
}
```

Stable schema across versions (semver-bumped on breaking changes).

---

## 5. Non-Functional Requirements

| Dimension | Target |
|-----------|--------|
| Cold-start latency (`ask`) | < 6s on indexed 10k-symbol repo |
| Token efficiency vs. naïve "load files" | ≥ 5× reduction on retrieval-bound tasks |
| Install footprint | Single Python (or Node) package, no native deps beyond `claude` itself |
| Platform support | macOS, Linux, Windows (PowerShell-tested) |
| Python | 3.10+ |
| License | Apache 2.0, consistent with mcp-retrieval-spec |

---

## 6. Architecture

```
┌─────────────────────────┐
│  jragmunch CLI (Python) │
│  ─ verb dispatcher      │
│  ─ prompt builder       │
│  ─ MCP-config pinner    │
│  ─ stream-json parser   │
│  ─ fan-out orchestrator │
└──────────┬──────────────┘
           │ subprocess
           ▼
┌─────────────────────────┐         ┌────────────────────────┐
│   claude -p (headless)  │ ◀─MCP──▶│  jcodemunch-mcp        │
│   uses local auth       │         │  (slice retrieval)     │
└─────────────────────────┘         └────────────────────────┘
```

- Pure orchestration layer; zero model calls of its own.
- One module per verb (`verbs/ask.py`, `verbs/review.py`, …); shared `runner.py` handles the `claude -p` subprocess.
- `runner.py` is the only file that touches `subprocess`; everything else is pure functions for testability.

### Key files (proposed)
- `src/jragmunch/cli.py` — entrypoint, click/typer.
- `src/jragmunch/runner.py` — `claude -p` subprocess driver.
- `src/jragmunch/mcp_config.py` — pinned MCP-config generator.
- `src/jragmunch/verbs/` — one file per verb.
- `src/jragmunch/parsers.py` — stream-json event parser, cost extractor.
- `src/jragmunch/fanout.py` — parallel subprocess orchestrator.
- `tests/` — pytest, with `claude` CLI mocked via fixture.

---

## 7. Verb Specs (priority order)

### v1.0 (MVP)
- **`ask`** — single-shot retrieval-augmented Q&A. Default verb; demonstrates the core value.
- **`doctor`** — verify `claude` is on PATH, MCP wires up, jcodemunch responds. Run on first install.
- **`index`** — passthrough to `mcp__jcodemunch__index_folder`.
- **`run`** — power-user passthrough; builds prompt + flags, runs, returns JSON.

### v1.1
- **`review`** — diff-aware, uses `get_changed_symbols` + `get_blast_radius`.
- **`changelog`** — uses `get_changed_symbols` since tag.

### v1.2
- **`refactor`** — fan-out, dry-run by default, writes patch files.
- **`tests`** — fan-out over `get_untested_symbols`.
- **`sweep`** — pattern-driven cleanup (TODO removal, deprecation migration).

---

## 8. Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| Users perceive product as "API replacement," provoking Anthropic | Marketing copy is strictly technical (token-efficient, headless, MCP-native); never mentions cost, "free", or "without API." Auth-agnostic framing throughout. |
| `claude -p` rate limits break fan-out | `--parallel` defaults to 4; document subscription limits; recommend API-key auth for heavy fan-out. |
| jcodemunch index stale → bad answers | `doctor` checks freshness; verbs re-index on detected drift via `check_embedding_drift`. |
| Stream-json schema changes upstream | Pin a minimum `claude` version in `doctor`; degrade gracefully on unknown event types. |
| Windows path / shell quoting bugs | CI matrix includes Windows + PowerShell; integration tests exercise paths with spaces. |

---

## 9. Success Metrics

- **Adoption:** 500+ GitHub stars within 90 days of launch (jcodemunch-mcp comparable: 1500+).
- **Token win:** Published benchmark showing ≥5× token reduction vs. "load files into context" baseline on 3 reference repos.
- **Ecosystem pull-through:** ≥30% of jragmunch users are new to jcodemunch-mcp (measured via `index_folder` first-call telemetry, opt-in).
- **Issue quality:** <10% of issues are auth/config related (proxy for ergonomics).

---

## 10. Rollout Plan

1. **Week 1–2:** Skeleton + `runner.py` + `doctor` + `ask`. Internal dogfood on jcodemunch-mcp's own repo.
2. **Week 3:** `index`, `run`, structured output contract locked. Alpha release to a handful of users.
3. **Week 4–5:** `review` + `changelog`. Public v1.0 on PyPI.
4. **Week 6–8:** `refactor`, `tests`, `sweep`, fan-out hardening. v1.2.
5. **Ongoing:** jdocmunch + jdatamunch optional integrations (`ask --with-docs`, `ask --with-data`).

---

## 11. Open Questions

1. **Python or Node?** Python aligns with jcodemunch-mcp's stack and `pip install` ergonomics; Node aligns with Claude Code's own ecosystem. *Recommendation: Python, with a thin `npx jragmunch` shim later.*
2. **Telemetry?** Opt-in only. What's the minimum useful signal? (Probably: verb name, success/fail, token totals — no prompts, no code.)
3. **Plugin model?** Should third parties be able to register new verbs? Defer to v2.
4. **Branding tier:** standalone product, or `jcodemunch-cli` sub-brand? *Recommendation: standalone, cross-promoted.*

---

## 12. Verification

Before shipping v1.0:
- `jragmunch doctor` passes on macOS, Linux, Windows with both subscription-auth and API-key-auth `claude`.
- `jragmunch ask "what does X do"` on jcodemunch-mcp's own repo returns a correct, citation-grounded answer in <6s.
- Token-reduction benchmark reproduced from a published script (committed to repo).
- Stream-json `system/init` parsing verified against `claude` v[pin].
- Fan-out integration test: 10 parallel `ask` invocations complete without rate-limit failures under default config.

---

## Critical files to create
- `src/jragmunch/cli.py`
- `src/jragmunch/runner.py`
- `src/jragmunch/mcp_config.py`
- `src/jragmunch/parsers.py`
- `src/jragmunch/verbs/{ask,doctor,index,run,review,changelog,refactor,tests,sweep}.py`
- `src/jragmunch/fanout.py`
- `tests/` (mirroring above)
- `pyproject.toml`, `README.md`, `LICENSE` (Apache 2.0)
- `benchmarks/token_reduction.py`
