"""FastIntercom MCP Server - High-performance local Intercom conversation access."""

__version__ = "0.1.0"
__author__ = "evolsb"
__description__ = "High-performance MCP server for Intercom conversation analytics"

from .database import DatabaseManager
from .intercom_client import IntercomClient
from .mcp_server import FastIntercomMCPServer
from .sync_service import SyncService, SyncManager
from .config import Config
from .models import Conversation, Message, ConversationFilters

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
]