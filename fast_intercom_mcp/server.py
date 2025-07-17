"""FastMCP server with all tools registered."""
from .app import mcp, app

# Import all tools to register them with the mcp instance
from .tools import conversations
from .tools import articles
from .tools import tickets
from .tools import sync

# Register all tool functions
conversations.register_tools(mcp)
articles.register_tools(mcp)
tickets.register_tools(mcp)
sync.register_tools(mcp)

# Export the app for uvicorn
__all__ = ['app', 'mcp']