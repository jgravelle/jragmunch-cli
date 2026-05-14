# jragmunch-cli

[![PyPI version](https://img.shields.io/pypi/v/jragmunch.svg)](https://pypi.org/project/jragmunch/)
[![Downloads](https://img.shields.io/pypi/dm/jragmunch.svg)](https://pypistats.org/packages/jragmunch)
[![Python versions](https://img.shields.io/pypi/pyversions/jragmunch.svg)](https://pypi.org/project/jragmunch/)
[![License](https://img.shields.io/pypi/l/jragmunch.svg)](https://github.com/jgravelle/jragmunch-cli/blob/master/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/jgravelle/jragmunch-cli?style=social)](https://github.com/jgravelle/jragmunch-cli/stargazers)

**Maximal token-efficient RAG for headless Claude.** Uses your existing `claude` CLI; auth-agnostic; slice-level retrieval powered by [jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp).

## Billing: SDK credit by default, API on opt-in

**Starting June 15, 2026**, Anthropic's Pro and Max subscriptions include a
**monthly Agent SDK credit** that scales with subscription tier (**$20**
Pro, **$100** Max 5x, **$200** Max 20x) covering `claude -p` and
SDK-based tools like jragmunch. By default, jragmunch strips
`ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN` from the subprocess
environment before spawning `claude`, so the CLI uses your Claude OAuth
login and runs against that SDK credit. ([Anthropic announcement](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan))

- **Inside your monthly SDK credit:** $0 actual dollars.
- **Past the credit:** Anthropic's "extra usage" kicks in if you've
  enabled it (opt-in, manually toggleable in Anthropic's billing
  settings); otherwise the call fails. Heavy users will want to either
  enable extra usage or pass `--use-api`.
- **Your subscription session limits are not touched.** Those stay
  reserved for interactive use of Claude Code and chat. (Pre-June-15
  behavior was the opposite: programmatic `claude -p` consumed session
  quota. The Agent SDK credit replaces that arrangement.)

If you'd rather bill via the API directly, pass `--use-api` and bring
your own `ANTHROPIC_API_KEY`:

```bash
jragmunch --use-api ask "..."
```

Every verb prints the cost split:

```
[tokens in=24 out=1273  cost actual=$0.0000 (notional=$0.5334, auth=subscription)  time=27549ms]
```

- **`actual`** — dollars billed to your Anthropic account by this call.
  In subscription mode this is $0 while you're inside your monthly SDK
  credit; it goes non-zero only if extra usage is enabled and the
  credit is exhausted.
- **`notional`** — what the work would have cost via the API. `claude -p`
  computes this regardless of auth mode; we surface it as a "what it
  might have cost" yardstick. Useful for tracking SDK-credit burn rate
  even while `actual` stays at $0.
- **`auth`** — `subscription` or `api`. Run `jragmunch doctor` to see
  your resolved mode.

### When to use which mode

Anthropic's [Claude Code Legal and Compliance docs](https://code.claude.com/docs/en/legal-and-compliance)
distinguish *individual ordinary use* from *business / always-on /
multi-contributor* use. jragmunch's defaults are tuned to that line.

| You are… | Recommended mode | Why |
|---|---|---|
| A solo developer running verbs interactively on your own machine | **subscription** (default) | Anthropic explicitly permits "ordinary, individual usage of Claude Code." The monthly SDK credit comfortably covers typical interactive use. |
| A solo developer wiring `jragmunch review` into your **own personal repo's CI** with `CLAUDE_CODE_OAUTH_TOKEN` | **subscription** (default) | Permitted as long as you're the only contributor whose work it acts on. Watch the `notional` cost line — heavy CI use can burn the SDK credit faster than interactive use. |
| A team running CI bots on a shared/commercial repo | `--use-api` | Anthropic requires API keys for "business or always-on deployments." |
| Multi-developer or commercial automation | `--use-api` | Subscriptions are not the right billing surface for shared use. |
| Heavy parallel fan-out (`refactor --parallel 16`, `tests --max 100`) | `--use-api` | A single fan-out can blow past your monthly SDK credit; API-mode keeps the cost predictable and avoids extra-usage opt-in. |

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
