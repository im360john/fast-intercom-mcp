"""Simple FastAPI application for deployment."""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .db.connection import db_pool
from .config import Config
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    try:
        await db_pool.initialize()
        logger.info("FastIntercom MCP server started")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
    
    yield
    
    # Shutdown
    try:
        await db_pool.close()
        logger.info("FastIntercom MCP server stopped")
    except Exception as e:
        logger.error(f"Shutdown failed: {e}")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Fast Intercom MCP",
    description="Enhanced Intercom MCP with PostgreSQL and full-text search",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "fast-intercom-mcp",
        "status": "running",
        "message": "FastMCP server is operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Quick database connectivity check
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "fast-intercom-mcp",
        "database": db_status
    }

# Add MCP tools as API endpoints
from .mcp_endpoints import router as mcp_router
app.include_router(mcp_router)

# Add MCP SSE endpoint for LibreChat integration
try:
    from .mcp_sse_bidirectional import router as sse_router
    app.include_router(sse_router)
except ImportError:
    # Fallback to simple implementation
    from .mcp_sse_simple import router as sse_router
    app.include_router(sse_router)