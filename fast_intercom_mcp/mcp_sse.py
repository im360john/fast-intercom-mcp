"""MCP Server-Sent Events endpoint for LibreChat integration."""
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest, 
    ListToolsResult,
    Tool,
    InitializeRequest,
    InitializeResult,
    JSONRPCMessage,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError
)

from .tools import conversations, articles, sync, tickets

logger = logging.getLogger(__name__)

router = APIRouter()

# Available MCP tools
AVAILABLE_TOOLS = [
    Tool(
        name="search_conversations",
        description="Search and retrieve Intercom conversations with full-text search, filtering by timeframe, customer email, or conversation state",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for conversation content"
                },
                "timeframe": {
                    "type": "string", 
                    "description": "Time period: last_24h, last_7d, last_30d, last_90d"
                },
                "customer_email": {
                    "type": "string",
                    "description": "Filter by specific customer email"
                },
                "state": {
                    "type": "string",
                    "description": "Filter by conversation state: open, closed, snoozed"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 20
                }
            }
        }
    ),
    Tool(
        name="get_conversation_details", 
        description="Get detailed information about a specific conversation, including all parts and messages",
        inputSchema={
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The Intercom conversation ID"
                },
                "include_parts": {
                    "type": "boolean", 
                    "description": "Include conversation parts/messages",
                    "default": True
                }
            },
            "required": ["conversation_id"]
        }
    ),
    Tool(
        name="search_articles",
        description="Search Intercom knowledge base articles with full-text search",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for article content"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10
                },
                "include_preview": {
                    "type": "boolean",
                    "description": "Include article content preview",
                    "default": False
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_article",
        description="Get detailed content of a specific article",
        inputSchema={
            "type": "object", 
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "The Intercom article ID"
                }
            },
            "required": ["article_id"]
        }
    ),
    Tool(
        name="sync_conversations",
        description="Sync recent conversations from Intercom API to local database",
        inputSchema={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days back to sync",
                    "default": 7
                },
                "force": {
                    "type": "boolean",
                    "description": "Force resync even if recently synced",
                    "default": False
                }
            }
        }
    ),
    Tool(
        name="sync_articles", 
        description="Sync articles from Intercom API to local database",
        inputSchema={
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Force resync even if recently synced", 
                    "default": False
                }
            }
        }
    ),
    Tool(
        name="get_sync_status",
        description="Get the status of recent sync operations",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    )
]

async def handle_mcp_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol requests"""
    try:
        method = request_data.get("method")
        params = request_data.get("params", {})
        request_id = request_data.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "logging": {}
                    },
                    "serverInfo": {
                        "name": "fast-intercom-mcp",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0", 
                "id": request_id,
                "result": {
                    "tools": [tool.model_dump() for tool in AVAILABLE_TOOLS]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "search_conversations":
                result = await conversations.search_conversations(**arguments)
            elif tool_name == "get_conversation_details":
                result = await conversations.get_conversation_details(**arguments)
            elif tool_name == "search_articles":
                result = await articles.search_articles(**arguments)
            elif tool_name == "get_article":
                result = await articles.get_article(**arguments)
            elif tool_name == "sync_conversations":
                result = await sync.sync_conversations(**arguments)
            elif tool_name == "sync_articles":
                result = await sync.sync_articles(**arguments)
            elif tool_name == "get_sync_status":
                result = await sync.get_sync_status(**arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

@router.post("/mcp")
async def mcp_streamable_endpoint(request: Request):
    """MCP streamable HTTP transport endpoint for LibreChat integration"""
    
    async def event_generator():
        try:
            # Read the request body
            body = await request.body()
            if body:
                request_data = json.loads(body.decode())
                response = await handle_mcp_request(request_data)
                yield f"data: {json.dumps(response)}\n\n"
            else:
                # Send capabilities on connection
                yield f"data: {json.dumps({'capabilities': 'available'})}\n\n"
                
        except Exception as e:
            logger.error(f"SSE error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"SSE error: {str(e)}"
                }
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    )