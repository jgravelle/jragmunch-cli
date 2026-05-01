from pathlib import Path

from jragmunch.runner import RunSpec, build_argv, format_command


def test_build_argv_basic():
    spec = RunSpec(prompt="hello")
    argv = build_argv(spec)
    assert "-p" in argv and "hello" in argv
    assert "--output-format" in argv and "stream-json" in argv
    assert "--allowedTools" in argv


def test_build_argv_inline_mcp_and_dirs(tmp_path: Path):
    spec = RunSpec(
        prompt="x",
        mcp_config_inline='{"mcpServers":{}}',
        add_dirs=[tmp_path],
        model="claude-opus-4-7",
        permission_mode="bypassPermissions",
    )
    argv = build_argv(spec)
    assert "--mcp-config" in argv
    assert '{"mcpServers":{}}' in argv
    assert "--add-dir" in argv and str(tmp_path) in argv
    assert "--model" in argv and "claude-opus-4-7" in argv
    assert "--permission-mode" in argv and "bypassPermissions" in argv


def test_format_command_quotes_spaces():
    spec = RunSpec(prompt="hello world")
    out = format_command(spec)
    assert '"hello world"' in out
