"""FastAPI server with tools available as API endpoints."""
from .app import app

# For now, we just export the FastAPI app
# Later we can add the MCP tools as API endpoints

# Export the app for uvicorn
__all__ = ['app']