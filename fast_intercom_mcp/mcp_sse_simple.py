"""Simple SSE implementation for LibreChat MCP integration."""
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse

from .tools import conversations, articles, sync, tickets

logger = logging.getLogger(__name__)

router = APIRouter()

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Available MCP tools configuration
AVAILABLE_TOOLS = [
    {
        "name": "search_conversations",
        "description": "Search and retrieve Intercom conversations with full-text search, filtering by timeframe, customer email, or conversation state",
        "inputSchema": {
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
    },
    {
        "name": "get_conversation_details", 
        "description": "Get detailed information about a specific conversation, including all parts and messages",
        "inputSchema": {
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
    },
    {
        "name": "search_articles",
        "description": "Search Intercom knowledge base articles with full-text search",
        "inputSchema": {
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
    },
    {
        "name": "get_article",
        "description": "Get detailed content of a specific article",
        "inputSchema": {
            "type": "object", 
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "The Intercom article ID"
                }
            },
            "required": ["article_id"]
        }
    },
    {
        "name": "sync_conversations",
        "description": "Sync recent conversations from Intercom API to local database",
        "inputSchema": {
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
    },
    {
        "name": "sync_articles", 
        "description": "Sync articles from Intercom API to local database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Force resync even if recently synced", 
                    "default": False
                }
            }
        }
    },
    {
        "name": "get_sync_status",
        "description": "Get the status of recent sync operations",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_tickets",
        "description": "Search Intercom tickets with various filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search in ticket content"},
                "customer_email": {"type": "string", "description": "Filter by customer email"},
                "ticket_state": {"type": "string", "description": "Filter by state: submitted, in_progress, waiting_on_customer, on_hold, resolved"},
                "ticket_type_id": {"type": "string", "description": "Filter by ticket type ID"},
                "limit": {"type": "integer", "description": "Maximum tickets to return", "default": 20}
            }
        }
    },
    {
        "name": "get_ticket_details",
        "description": "Get detailed information about a specific ticket",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "The Intercom ticket ID"}
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "create_ticket_reply",
        "description": "Create a reply on an existing ticket",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "The Intercom ticket ID"},
                "message": {"type": "string", "description": "Reply message content"},
                "reply_type": {"type": "string", "description": "Type of reply: comment or note", "default": "comment"}
            },
            "required": ["ticket_id", "message"]
        }
    }
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
                    "tools": AVAILABLE_TOOLS
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
            elif tool_name == "search_tickets":
                result = await tickets.search_tickets(**arguments)
            elif tool_name == "get_ticket_details":
                result = await tickets.get_ticket_details(**arguments)
            elif tool_name == "create_ticket_reply":
                result = await tickets.create_ticket_reply(**arguments)
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
                            "text": json.dumps(result, indent=2, cls=DateTimeEncoder)
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

@router.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    """SSE endpoint that provides the messages endpoint URL"""
    import uuid
    session_id = str(uuid.uuid4()).replace('-', '')
    
    async def event_generator():
        # Send the endpoint URL exactly like Zapier does
        yield f"event: endpoint\ndata: /mcp/messages?session_id={session_id}\n\n"
        
        # Send periodic pings
        import time
        while True:
            await asyncio.sleep(5)  # Send pings every 5 seconds
            yield f"\n: ping - {datetime.now().isoformat()}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )

@router.post("/mcp/messages")
async def mcp_messages_endpoint(request: Request, session_id: str = Query(...)):
    """Handle MCP messages for a specific session"""
    try:
        body = await request.body()
        request_data = json.loads(body.decode()) if body else {}
        response = await handle_mcp_request(request_data)
        
        return response
    except Exception as e:
        logger.error(f"Messages endpoint error: {e}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

# Keep the original /mcp endpoint for backwards compatibility
@router.get("/mcp")
async def mcp_redirect(request: Request):
    """Redirect to the proper SSE endpoint"""
    import uuid
    session_id = str(uuid.uuid4()).replace('-', '')
    
    async def event_generator():
        # Send the endpoint URL exactly like Zapier does
        yield f"event: endpoint\ndata: /mcp/messages?session_id={session_id}\n\n"
        
        # Send periodic pings
        while True:
            await asyncio.sleep(5)  # Send pings every 5 seconds
            yield f"\n: ping - {datetime.now().isoformat()}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )

@router.post("/mcp") 
async def mcp_post_endpoint(request: Request):
    """Handle POST requests for MCP protocol"""
    try:
        body = await request.body()
        request_data = json.loads(body.decode()) if body else {}
        response = await handle_mcp_request(request_data)
        
        # Return SSE formatted response
        async def generator():
            yield f"data: {json.dumps(response, cls=DateTimeEncoder)}\n\n"
        
        return StreamingResponse(
            generator(),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"POST error: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        
        async def error_generator():
            yield f"data: {json.dumps(error_response, cls=DateTimeEncoder)}\n\n"
        
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream"
        )