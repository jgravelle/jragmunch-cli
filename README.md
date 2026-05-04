# jragmunch-cli

[![PyPI version](https://img.shields.io/pypi/v/jragmunch.svg)](https://pypi.org/project/jragmunch/)
[![Downloads](https://img.shields.io/pypi/dm/jragmunch.svg)](https://pypistats.org/packages/jragmunch)
[![Python versions](https://img.shields.io/pypi/pyversions/jragmunch.svg)](https://pypi.org/project/jragmunch/)
[![License](https://img.shields.io/pypi/l/jragmunch.svg)](https://github.com/jgravelle/jragmunch-cli/blob/master/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/jgravelle/jragmunch-cli?style=social)](https://github.com/jgravelle/jragmunch-cli/stargazers)

**Maximal token-efficient RAG for headless Claude.** Uses your existing `claude` CLI; auth-agnostic; slice-level retrieval powered by [jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp).

## Billing: subscription by default, API on opt-in

**By default, jragmunch never bills your Anthropic API account.** It strips
`ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from the subprocess environment
before spawning `claude`, so the CLI uses your **Max / Pro Claude OAuth login
while respecting their TOS** — you pay $0 in dollars, the work counts against
your subscription's session limits.

If you want to bill via the API instead, pass `--use-api`:

```bash
jragmunch --use-api ask "..."
```

Every verb prints the cost split:

```
[tokens in=24 out=1273  cost actual=$0.0000 (notional=$0.5334, auth=subscription)  time=27549ms]
```

- **`actual`** — what you were really billed (always $0 in subscription mode).
- **`notional`** — what the work would have cost via the API. `claude -p`
  computes this regardless of auth mode; we surface it as a "what it might
  have cost" yardstick.
- **`auth`** — `subscription` or `api`. Run `jragmunch doctor` to see your
  resolved mode.

### When to use which mode

Anthropic's [Claude Code Legal and Compliance docs](https://code.claude.com/docs/en/legal-and-compliance)
distinguish *individual ordinary use* from *business / always-on / multi-contributor* use.
jragmunch's defaults are tuned to that line.

| You are… | Recommended mode | Why |
|---|---|---|
| A solo developer running verbs interactively on your own machine | **subscription** (default) | Anthropic explicitly permits "ordinary, individual usage of Claude Code." |
| A solo developer wiring `jragmunch review` into your **own personal repo's CI** with `CLAUDE_CODE_OAUTH_TOKEN` | **subscription** (default) | Permitted as long as you're the only contributor whose work it acts on. |
| A team running CI bots on a shared/commercial repo | `--use-api` | Anthropic requires API keys for "business or always-on deployments." |
| Multi-developer or commercial automation | `--use-api` | Subscriptions are not the right billing surface for shared use. |
| Heavy parallel fan-out (`refactor --parallel 16`, `tests --max 100`) | `--use-api` | High-throughput patterns aren't what subscription session limits are designed for. |

When in doubt, pass `--use-api` and bring your own `ANTHROPIC_API_KEY`.

### Multi-profile users (`CLAUDE_CONFIG_DIR`)

If you swap between Claude profiles (work and personal, for example) by
exporting `CLAUDE_CONFIG_DIR`, jragmunch propagates that variable to the
spawned `claude -p` subprocess automatically. You can also set it
explicitly per-invocation with `--config-dir`, which overrides any
inherited value:

```bash
# Inherit from shell env
CLAUDE_CONFIG_DIR=~/.claude.work jragmunch ask "..."

# Or set explicitly per-call
jragmunch --config-dir ~/.claude.personal ask "..."
```

### What jragmunch is *not*

jragmunch is **not** an "agent harness" or a re-implementation of Claude Code.
It shells out to the official `claude` CLI binary you installed via
`npm install -g @anthropic-ai/claude-code` and parses its `--output-format
stream-json` output. It does not replace, wrap, or proxy Anthropic's models —
it just gives `claude -p` better retrieval via MCP. Anthropic's TOS permits
this category of usage; the policy nuance above is about *where* you run it,
not *what tool* you run.

## Why

Headless Claude (`claude -p`) is the right substrate for retrieval-driven workflows — code Q&A, diff-aware review, batch refactors, "chat with your repo" use cases. The default pattern is "stuff the relevant files into the prompt and pray," which burns tokens on code the model never needed.

`jragmunch` wraps `claude -p` with jcodemunch pre-wired so the model retrieves slices on demand instead of receiving giant context dumps. (For team or always-on CI usage, see [the auth-mode table above](#when-to-use-which-mode) — pass `--use-api` and bring your own API key.)

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

## Try the side-by-side demo: `AskClaude.py`

`AskClaude.py` (in the repo root) is an interactive script that asks one
question and shows you, in plain English, what jragmunch saved you.

```bash
git clone https://github.com/jgravelle/jragmunch-cli
cd jragmunch-cli
pip install -e ".[dev]"
pip install tiktoken              # optional, for accurate token estimates
python AskClaude.py
```

It prompts for a local repo path and a question, then prints the answer
followed by a comparison block:

```
In its raw form, your request may have used as many as 799,037 tokens,
at a cost of $11.99.

Using jRagMunch, our call to Opus 4.7 only used 24,771 tokens.

By using your subscription WITHIN THE TERMS OF ANTHROPIC'S TOS, you paid
$0.00 and used a nearly imperceptible fractional percentage of your quota.
```

The "raw" number is a local projection of what pasting the entire repo
into the prompt would have cost (capped at the model's input window).
The jragmunch number is the actual marginal tokens this call consumed
(input + cache creation + output — cache reads excluded since those are
already-paid context being re-presented). Cost figures price the naive
projection at Opus 4.7's uncached input rate; subscription mode pays $0
either way.

Use it as a one-shot demo, a sanity check on your own repos, or a
template for embedding jragmunch in other tools.

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


## Principles

- **Auth-agnostic.** Whatever auth the local `claude` binary uses, jragmunch uses.
- **Slice, don't dump.** Default behavior is jcodemunch retrieval.
- **Structured output.** Every verb returns JSON with citations and `_meta` (tokens, cost, wall time).
- **Composable.** `--print-command` shows the exact `claude -p` invocation that would run.

## License

Apache 2.0
