"""FastIntercom MCP Server - High-performance local Intercom conversation access."""

__version__ = "0.2.0"
__author__ = "evolsb"
__description__ = "High-performance MCP server for Intercom conversation analytics"

from .config import Config
from .database import DatabaseManager
from .intercom_client import IntercomClient
from .mcp_server import FastIntercomMCPServer
from .models import Conversation, ConversationFilters, Message, SyncStateException
from .sync_service import SyncManager, SyncService

__all__ = [
    "DatabaseManager",
    "IntercomClient",
    "FastIntercomMCPServer",
    "SyncService",
    "SyncManager",
    "Config",
    "Conversation",
    "Message",
    "ConversationFilters",
    "SyncStateException",
]
