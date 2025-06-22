"""Data models for FastIntercom MCP server."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import quote


@dataclass
class Message:
    """A message within an Intercom conversation."""
    id: str
    author_type: str  # 'user' | 'admin'
    body: str
    created_at: datetime
    part_type: Optional[str] = None  # 'comment' | 'note' | 'message'


@dataclass
class Conversation:
    """An Intercom conversation with messages."""
    id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message]
    customer_email: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def get_url(self, app_id: str) -> str:
        """Generate clickable Intercom URL for this conversation."""
        base_url = f"https://app.intercom.com/a/inbox/{app_id}/inbox/search/conversation/{self.id}"
        if self.customer_email:
            encoded_email = quote(self.customer_email)
            return f"{base_url}?query={encoded_email}"
        return base_url
    
    def get_customer_messages(self) -> List[Message]:
        """Get only messages from customers (not admins)."""
        return [msg for msg in self.messages if msg.author_type == 'user']
    
    def get_admin_messages(self) -> List[Message]:
        """Get only messages from admins."""
        return [msg for msg in self.messages if msg.author_type == 'admin']


@dataclass
class SyncPeriod:
    """Represents a time period that has been synced from Intercom."""
    start_timestamp: datetime
    end_timestamp: datetime
    last_synced: datetime
    conversation_count: int
    new_conversations: int = 0
    updated_conversations: int = 0


@dataclass
class ConversationFilters:
    """Filters for searching conversations."""
    query: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    customer_email: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 100


@dataclass
class SyncStats:
    """Statistics about a sync operation."""
    total_conversations: int
    new_conversations: int
    updated_conversations: int
    total_messages: int  
    duration_seconds: float
    api_calls_made: int
    errors_encountered: int = 0


@dataclass 
class ServerStatus:
    """Overall server status information."""
    is_running: bool
    database_size_mb: float
    total_conversations: int
    total_messages: int
    last_sync: Optional[datetime]
    background_sync_active: bool
    uptime_seconds: Optional[float] = None
    mcp_requests_served: int = 0
    average_response_time_ms: float = 0.0


@dataclass
class MCPTool:
    """Definition of an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class MCPRequest:
    """An incoming MCP request."""
    tool_name: str
    parameters: Dict[str, Any]
    request_id: Optional[str] = None


@dataclass
class MCPResponse:
    """Response to an MCP request."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    request_id: Optional[str] = None