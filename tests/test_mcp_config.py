import json

from jragmunch.mcp_config import as_inline_json, build_config


def test_default_config_includes_jcodemunch():
    cfg = build_config()
    assert "jcodemunch" in cfg["mcpServers"]
    assert "command" in cfg["mcpServers"]["jcodemunch"]


def test_inline_json_is_valid():
    s = as_inline_json()
    parsed = json.loads(s)
    assert "mcpServers" in parsed
