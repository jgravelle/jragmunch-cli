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
    assert "--strict-mcp-config" in argv  # ensures user's global MCPs don't merge in
    assert "--add-dir" in argv and str(tmp_path) in argv
    assert "--model" in argv and "claude-opus-4-7" in argv
    assert "--permission-mode" in argv and "bypassPermissions" in argv


def test_allowlist_covers_both_jcodemunch_name_variants():
    from jragmunch.runner import DEFAULT_ALLOWED_TOOLS

    assert "mcp__jcodemunch__*" in DEFAULT_ALLOWED_TOOLS
    assert "mcp__jcodemunch-mcp__*" in DEFAULT_ALLOWED_TOOLS


def test_format_command_quotes_spaces():
    spec = RunSpec(prompt="hello world")
    out = format_command(spec)
    assert '"hello world"' in out


# ---------------------------------------------------------------------------
# v0.4.6: CLAUDE_CONFIG_DIR propagation (issue #1)
# ---------------------------------------------------------------------------

class TestSubprocessEnvConfigDir:
    """``_build_subprocess_env`` is the single chokepoint that decides what
    environment the spawned ``claude -p`` sees. Two requirements:
      1. Inherited ``CLAUDE_CONFIG_DIR`` from the parent shell must reach
         the subprocess (multi-profile users export it before invoking
         jragmunch).
      2. Explicit ``--config-dir`` overrides whatever was inherited.
    """

    def test_inherited_config_dir_is_propagated(self, monkeypatch):
        from jragmunch.runner import _build_subprocess_env

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/home/u/.claude.work")
        env = _build_subprocess_env(use_api=False, config_dir=None)
        assert env.get("CLAUDE_CONFIG_DIR") == "/home/u/.claude.work"

    def test_no_config_dir_when_unset(self, monkeypatch):
        from jragmunch.runner import _build_subprocess_env

        monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
        env = _build_subprocess_env(use_api=False, config_dir=None)
        assert "CLAUDE_CONFIG_DIR" not in env

    def test_explicit_override_wins_over_inherited(self, monkeypatch):
        from jragmunch.runner import _build_subprocess_env

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/home/u/.claude.work")
        env = _build_subprocess_env(
            use_api=False, config_dir=Path("/home/u/.claude.personal"),
        )
        assert env["CLAUDE_CONFIG_DIR"] == str(Path("/home/u/.claude.personal"))

    def test_explicit_override_works_without_inherited(self, monkeypatch):
        from jragmunch.runner import _build_subprocess_env

        monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
        env = _build_subprocess_env(
            use_api=False, config_dir=Path("/tmp/.claude.alt"),
        )
        assert env["CLAUDE_CONFIG_DIR"] == str(Path("/tmp/.claude.alt"))

    def test_api_key_strip_does_not_remove_config_dir(self, monkeypatch):
        """Regression guard: --use-api default-OFF strips the API key but
        must not accidentally strip CLAUDE_CONFIG_DIR."""
        from jragmunch.runner import _build_subprocess_env

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/somewhere")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        env = _build_subprocess_env(use_api=False, config_dir=None)
        assert "ANTHROPIC_API_KEY" not in env
        assert env["CLAUDE_CONFIG_DIR"] == "/somewhere"
