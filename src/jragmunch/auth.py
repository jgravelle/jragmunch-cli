"""Auth-mode detection and actual-cost computation.

`claude -p` always reports `total_cost_usd` in its `result` event. That number
is the API-list price for the work — what it WOULD have cost if billed via the
Anthropic API. But the local `claude` binary may be using a subscription
(Max/Pro OAuth) instead of an API key, in which case the user pays $0 and the
work counts against session/rate limits instead.

We detect auth mode the same way `claude` itself does: presence of
ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) in the environment.
"""
from __future__ import annotations

import os
from typing import Literal


AuthMode = Literal["api", "subscription"]


def detect_auth() -> AuthMode:
    """Return 'api' if an API key is set, else 'subscription'."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "api"
    return "subscription"


def actual_cost(notional_usd: float, mode: AuthMode | None = None) -> float:
    """Return the dollars actually billed for this run.

    Subscription mode: $0 (counts against session limits, not dollars).
    API mode: equal to the notional cost claude reported.
    """
    if mode is None:
        mode = detect_auth()
    return notional_usd if mode == "api" else 0.0
