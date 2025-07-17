"""Utilities package for Fast Intercom MCP."""
from .context_window import context_manager, ContextWindowManager, TruncationResult

__all__ = ["context_manager", "ContextWindowManager", "TruncationResult"]