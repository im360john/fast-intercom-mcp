"""HTTP transport implementation for FastIntercom MCP server."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import secrets
import base64

from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

from mcp.types import JSONRPCRequest

from .database import DatabaseManager
from .sync_service import SyncService
from .mcp_server import FastIntercomMCPServer


logger = logging.getLogger(__name__)


class MCPHTTPRequest(BaseModel):
    """HTTP request wrapper for MCP JSON-RPC."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPHTTPResponse(BaseModel):
    """HTTP response wrapper for MCP JSON-RPC."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class AuthManager:
    """Simple authentication manager for HTTP MCP."""
    
    def __init__(self, api_key: Optional[str] = None):
        # Generate a random API key if none provided
        self.api_key = api_key or self._generate_api_key()
        logger.info(f"HTTP MCP server authentication key: {self.api_key}")
    
    def _generate_api_key(self) -> str:
        """Generate a secure random API key."""
        random_bytes = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(random_bytes).decode('ascii')
    
    def verify_key(self, provided_key: str) -> bool:
        """Verify the provided API key."""
        return secrets.compare_digest(self.api_key, provided_key)


class FastIntercomHTTPServer:
    """HTTP-based MCP server for FastIntercom."""
    
    def __init__(
        self, 
        database_manager: DatabaseManager, 
        sync_service: SyncService,
        intercom_client=None,
        api_key: Optional[str] = None,
        host: str = "0.0.0.0",
        port: int = 8000
    ):
        self.db = database_manager
        self.sync_service = sync_service
        self.host = host
        self.port = port
        
        # Initialize core MCP server
        self.mcp_server = FastIntercomMCPServer(database_manager, sync_service, intercom_client)
        
        # Authentication
        self.auth = AuthManager(api_key)
        
        # FastAPI app
        self.app = FastAPI(
            title="FastIntercom MCP Server",
            description="HTTP-based Model Context Protocol server for Intercom conversations",
            version="1.0.0"
        )
        
        # Security
        self.security = HTTPBearer()
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
    
    def _verify_auth(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        """Verify authentication credentials."""
        if not self.auth.verify_key(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return credentials
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def root():
            """Root endpoint with server info."""
            return {
                "name": "FastIntercom MCP Server",
                "version": "1.0.0",
                "transport": "http",
                "capabilities": {
                    "tools": True,
                    "resources": False,
                    "prompts": False
                },
                "authentication": "bearer_token"
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                # Quick database connectivity check
                status = self.db.get_sync_status()
                return {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "database": "connected",
                    "conversations": status.get("total_conversations", 0)
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Service unhealthy: {str(e)}"
                )
        
        @self.app.post("/mcp")
        async def mcp_endpoint(
            request: MCPHTTPRequest,
            auth: HTTPAuthorizationCredentials = Depends(self._verify_auth)
        ):
            """Main MCP JSON-RPC endpoint."""
            try:
                # Convert HTTP request to MCP JSON-RPC format
                jsonrpc_request = JSONRPCRequest(
                    jsonrpc="2.0",
                    method=request.method,
                    params=request.params or {},
                    id=request.id
                )
                
                # Process the request through the MCP server
                response = await self._process_mcp_request(jsonrpc_request)
                
                # Convert MCP response back to HTTP format
                return MCPHTTPResponse(
                    jsonrpc="2.0",
                    result=response.get("result"),
                    error=response.get("error"),
                    id=request.id
                )
                
            except Exception as e:
                logger.error(f"MCP request processing error: {e}")
                return MCPHTTPResponse(
                    jsonrpc="2.0",
                    error={
                        "code": -32603,
                        "message": "Internal error",
                        "data": str(e)
                    },
                    id=request.id
                )
        
        @self.app.get("/tools")
        async def list_tools(auth: HTTPAuthorizationCredentials = Depends(self._verify_auth)):
            """List available MCP tools."""
            try:
                # Get tools from the MCP server
                tools = await self.mcp_server._list_tools()
                return {
                    "tools": [tool.model_dump() for tool in tools]
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list tools: {str(e)}"
                )
        
        @self.app.post("/tools/{tool_name}")
        async def call_tool(
            tool_name: str,
            arguments: Dict[str, Any],
            auth: HTTPAuthorizationCredentials = Depends(self._verify_auth)
        ):
            """Call a specific MCP tool."""
            try:
                # Call the tool through the MCP server
                result = await self.mcp_server._call_tool(tool_name, arguments)
                
                # Convert TextContent results to simple format
                formatted_result = []
                for item in result:
                    if hasattr(item, 'text'):
                        formatted_result.append(item.text)
                    else:
                        formatted_result.append(str(item))
                
                return {
                    "tool": tool_name,
                    "result": formatted_result,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Tool execution failed: {str(e)}"
                )
    
    async def _process_mcp_request(self, request: JSONRPCRequest) -> Dict[str, Any]:
        """Process an MCP JSON-RPC request."""
        try:
            method = request.method
            params = request.params or {}
            
            if method == "initialize":
                return {
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "fastintercom",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                tools = await self.mcp_server._list_tools()
                return {
                    "result": {
                        "tools": [tool.model_dump() for tool in tools]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    return {
                        "error": {
                            "code": -32602,
                            "message": "Invalid params: tool name required"
                        }
                    }
                
                result = await self.mcp_server._call_tool(tool_name, arguments)
                
                # Convert TextContent to dict format
                content = []
                for item in result:
                    if hasattr(item, 'text'):
                        content.append({
                            "type": "text",
                            "text": item.text
                        })
                    else:
                        content.append({
                            "type": "text", 
                            "text": str(item)
                        })
                
                return {
                    "result": {
                        "content": content
                    }
                }
            
            else:
                return {
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            logger.error(f"MCP request processing error: {e}")
            return {
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": str(e)
                }
            }
    
    async def start(self):
        """Start the HTTP server."""
        logger.info(f"Starting FastIntercom HTTP MCP server on {self.host}:{self.port}")
        logger.info(f"API Key: {self.auth.api_key}")
        
        # Start background sync
        await self.mcp_server.start_background_sync()
        
        # Create uvicorn config
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True
        )
        
        # Start the server
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop the HTTP server."""
        logger.info("Stopping FastIntercom HTTP MCP server")
        await self.mcp_server.stop_background_sync()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for clients."""
        return {
            "transport": "http",
            "url": f"http://{self.host}:{self.port}/mcp",
            "authentication": {
                "type": "bearer",
                "token": self.auth.api_key
            },
            "endpoints": {
                "health": f"http://{self.host}:{self.port}/health",
                "tools": f"http://{self.host}:{self.port}/tools",
                "mcp": f"http://{self.host}:{self.port}/mcp"
            }
        }