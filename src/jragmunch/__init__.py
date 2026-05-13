"""jragmunch: agentic Q&A CLI over the jMunch MCP suite."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("jragmunch")
except PackageNotFoundError:
    __version__ = "unknown"
