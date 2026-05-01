import os

from jragmunch.auth import actual_cost, detect_auth


def test_detect_subscription_when_no_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert detect_auth() == "subscription"


def test_detect_api_when_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert detect_auth() == "api"


def test_actual_cost_zero_on_subscription():
    assert actual_cost(0.4260, mode="subscription") == 0.0


def test_actual_cost_passthrough_on_api():
    assert actual_cost(0.4260, mode="api") == 0.4260
