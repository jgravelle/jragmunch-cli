import os

from jragmunch import runtime
from jragmunch.auth import actual_cost, detect_auth
from jragmunch.runner import _build_subprocess_env


def test_default_is_subscription_even_when_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    runtime.set_state(use_api=False)
    assert detect_auth() == "subscription"


def test_use_api_with_key_returns_api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    runtime.set_state(use_api=True)
    assert detect_auth() == "api"
    runtime.set_state(use_api=False)


def test_use_api_without_key_falls_back_to_subscription(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    runtime.set_state(use_api=True)
    assert detect_auth() == "subscription"
    runtime.set_state(use_api=False)


def test_actual_cost_zero_on_subscription():
    assert actual_cost(0.4260, mode="subscription") == 0.0


def test_actual_cost_passthrough_on_api():
    assert actual_cost(0.4260, mode="api") == 0.4260


def test_subprocess_env_strips_keys_by_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-test")
    env = _build_subprocess_env(use_api=False)
    assert "ANTHROPIC_API_KEY" not in env
    assert "ANTHROPIC_AUTH_TOKEN" not in env


def test_subprocess_env_preserves_keys_when_use_api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    env = _build_subprocess_env(use_api=True)
    assert env.get("ANTHROPIC_API_KEY") == "sk-test"
