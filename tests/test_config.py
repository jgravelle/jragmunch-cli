from pathlib import Path

from jragmunch.config import Config, _merge


def test_merge_overrides_defaults():
    cfg = Config()
    cfg = _merge(
        cfg,
        {
            "defaults": {
                "model": "claude-sonnet-4-6",
                "parallel": 8,
                "with_docs": True,
                "allowed_tools": ["mcp__jcodemunch__*", "Bash"],
            }
        },
    )
    assert cfg.model == "claude-sonnet-4-6"
    assert cfg.parallel == 8
    assert cfg.with_docs is True
    assert "Bash" in cfg.allowed_tools


def test_merge_verbs_section():
    cfg = Config()
    cfg = _merge(cfg, {"verbs": {"review": {"severity_threshold": "med"}}})
    assert cfg.verbs["review"]["severity_threshold"] == "med"
