"""Config loader for jragmunch.

Resolution order (later overrides earlier):
  1. Built-in defaults
  2. ~/.jragmunch/config.toml
  3. <repo>/.jragmunch.toml
  4. CLI flags (handled by callers; this module only loads files)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


GLOBAL_CONFIG_PATH = Path.home() / ".jragmunch" / "config.toml"
PROJECT_CONFIG_NAME = ".jragmunch.toml"


@dataclass
class Config:
    model: str | None = None
    allowed_tools: list[str] = field(
        default_factory=lambda: ["mcp__jcodemunch__*", "Read", "Glob", "Grep"]
    )
    parallel: int = 4
    output: str = "text"
    mcp_config_path: Path | None = None
    with_docs: bool = False
    with_data: bool = False
    verbs: dict[str, dict] = field(default_factory=dict)


def _load_toml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _merge(base: Config, data: dict) -> Config:
    defaults = data.get("defaults", {})
    if "model" in defaults:
        base.model = defaults["model"]
    if "allowed_tools" in defaults:
        base.allowed_tools = list(defaults["allowed_tools"])
    if "parallel" in defaults:
        base.parallel = int(defaults["parallel"])
    if "output" in defaults:
        base.output = str(defaults["output"])
    if "with_docs" in defaults:
        base.with_docs = bool(defaults["with_docs"])
    if "with_data" in defaults:
        base.with_data = bool(defaults["with_data"])
    mcp = data.get("mcp", {})
    if "config_path" in mcp:
        base.mcp_config_path = Path(mcp["config_path"]).expanduser()
    verbs = data.get("verbs", {})
    if isinstance(verbs, dict):
        base.verbs.update(verbs)
    return base


def load(repo: Path | None = None) -> Config:
    cfg = Config()
    cfg = _merge(cfg, _load_toml(GLOBAL_CONFIG_PATH))
    if repo is not None:
        cfg = _merge(cfg, _load_toml(repo / PROJECT_CONFIG_NAME))
    return cfg
