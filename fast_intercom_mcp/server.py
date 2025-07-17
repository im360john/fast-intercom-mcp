"""FastMCP server implementation with Streamable HTTP transport."""
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from .db.connection import db_pool
from .config import Config
import logging

# Import all tools to register them
from . import tools

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
    json_response=True,  # Disable SSE for simpler responses
    lifespan=lifespan
)

# Server configuration
def run_server():
    """Run the server with streamable HTTP transport."""
    config = Config.load()
    mcp.run(
        transport="streamable-http",
        host=config.http_host,
        port=config.http_port,
        path=config.http_path
    )

if __name__ == "__main__":
    run_server()