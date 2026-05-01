"""Per-verb default model and turn caps.

Retrieval-bound verbs (ask, doctor, index, run, sweep) default to Haiku 4.5 —
fast, cheap, and plenty for tool-calling + light synthesis.

Reasoning-heavy verbs (review, refactor, tests, changelog) default to
Sonnet 4.6 — better judgment per dollar than Opus for these tasks.

Users can always override via --model.
"""
from __future__ import annotations

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

# Per-verb defaults: (model, max_turns).
# max_turns caps the agentic loop so retrieval-bound verbs can't sprawl into
# 20 tool calls when 5 would do.
VERB_DEFAULTS: dict[str, tuple[str, int]] = {
    "ask":       (HAIKU,  10),
    "doctor":    (HAIKU,  2),
    "index":     (HAIKU,  6),
    "run":       (HAIKU,  12),
    "sweep":     (HAIKU,  10),
    "review":    (SONNET, 16),
    "refactor":  (SONNET, 16),
    "tests":     (SONNET, 16),
    "changelog": (SONNET, 14),
}


def for_verb(verb: str) -> tuple[str, int]:
    return VERB_DEFAULTS.get(verb, (HAIKU, 8))
