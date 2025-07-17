"""FastMCP application instance."""
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from .db.connection import db_pool
from .config import Config
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(server: FastMCP):
    """Manage server lifecycle"""
    # Initialize database pool
    await db_pool.initialize()
    
    # Initialize any other resources
    logger.info("FastIntercom MCP server started")
    yield
    
    # Cleanup
    await db_pool.close()
    logger.info("FastIntercom MCP server stopped")

# Create server instance with stateless HTTP
mcp = FastMCP(
    "fast-intercom-mcp",
    stateless_http=True,
    json_response=True,
    lifespan=lifespan
)

# For uvicorn
app = mcp.get_app()