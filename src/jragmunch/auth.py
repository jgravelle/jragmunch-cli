"""Auth-mode detection and actual-cost computation.

`claude -p` always reports `total_cost_usd` in its `result` event. That number
is the API-list price for the work — what it WOULD have cost if billed via the
Anthropic API. But the local `claude` binary may be using a subscription
(Max/Pro OAuth) instead of an API key, in which case the user pays $0 in
dollars and the work runs against Anthropic's monthly Agent SDK credit
(starting 2026-06-15; previously counted against subscription session
limits). See README "Billing" section for the credit-exhaustion contract.

We detect auth mode the same way `claude` itself does: presence of
ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) in the environment.
"""
from __future__ import annotations

import os
from typing import Literal


AuthMode = Literal["api", "subscription"]


def detect_auth() -> AuthMode:
    """Return the auth mode the spawned `claude` subprocess will use.

    jragmunch defaults to subscription mode: it strips ANTHROPIC_API_KEY
    from the subprocess env before spawning claude, so claude falls back
    to OAuth (Max/Pro subscription). Pass --use-api to opt in to billing.
    """
    from .runtime import get as _get_runtime

    if not _get_runtime().use_api:
        return "subscription"
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "api"
    return "subscription"


def actual_cost(notional_usd: float, mode: AuthMode | None = None) -> float:
    """Return the dollars actually billed for this run.

    Subscription mode: $0 while inside the monthly Agent SDK credit
                       (the default state). If extra-usage is enabled and
                       the credit is exhausted, the subprocess will pass
                       through real dollars — but `claude -p` still
                       reports the same `total_cost_usd` field, and we
                       still report `$0` here since the user-facing
                       billing surface is opaque to the subprocess.
    API mode:          equal to the notional cost claude reported.
    """
    if mode is None:
        mode = detect_auth()
    return notional_usd if mode == "api" else 0.0
