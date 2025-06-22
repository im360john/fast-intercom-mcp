"""MCP server implementation for FastIntercom."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .database import DatabaseManager
from .models import ConversationFilters, MCPRequest, MCPResponse
from .sync_service import SyncService


logger = logging.getLogger(__name__)


class FastIntercomMCPServer:
    """MCP server for Intercom conversation access."""
    
    def __init__(self, database_manager: DatabaseManager, sync_service: SyncService):
        self.db = database_manager
        self.sync_service = sync_service
        self.server = Server("fastintercom")
        self._setup_tools()
    
    def _setup_tools(self):
        """Register MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available MCP tools."""
            return [
                Tool(
                    name="search_conversations",
                    description="Search Intercom conversations with flexible filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Text to search for in conversation messages"
                            },
                            "timeframe": {
                                "type": "string", 
                                "description": "Time period like 'last 7 days', 'this month', 'last week'"
                            },
                            "customer_email": {
                                "type": "string",
                                "description": "Filter by specific customer email address"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of conversations to return (default: 50)",
                                "default": 50
                            }
                        }
                    }
                ),
                Tool(
                    name="get_conversation",
                    description="Get full details of a specific conversation by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "conversation_id": {
                                "type": "string",
                                "description": "The Intercom conversation ID"
                            }
                        },
                        "required": ["conversation_id"]
                    }
                ),
                Tool(
                    name="get_server_status",
                    description="Get FastIntercom server status and statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="sync_conversations",
                    description="Trigger manual sync of recent conversations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "force": {
                                "type": "boolean",
                                "description": "Force full sync even if recent data exists",
                                "default": False
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle MCP tool calls."""
            try:
                if name == "search_conversations":
                    return await self._search_conversations(arguments)
                elif name == "get_conversation":
                    return await self._get_conversation(arguments)
                elif name == "get_server_status":
                    return await self._get_server_status(arguments)
                elif name == "sync_conversations":
                    return await self._sync_conversations(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                logger.error(f"Tool call error for {name}: {e}")
                return [TextContent(
                    type="text", 
                    text=f"Error executing {name}: {str(e)}"
                )]
    
    async def _search_conversations(self, args: Dict[str, Any]) -> List[TextContent]:
        """Search conversations with filters."""
        query = args.get("query")
        timeframe = args.get("timeframe")
        customer_email = args.get("customer_email")
        limit = args.get("limit", 50)
        
        # Parse timeframe into dates
        start_date, end_date = self._parse_timeframe(timeframe)
        
        # Calculate data freshness and trigger smart sync
        data_freshness_seconds = 0
        sync_triggered = False
        
        if start_date and end_date:
            # Check how fresh our data is for this timeframe
            data_freshness_seconds = self.db.get_data_freshness_for_timeframe(start_date, end_date)
            
            # Trigger background sync for next request if data is stale (>5 minutes)
            if data_freshness_seconds > 300:  # 5 minutes
                # Start background sync task (non-blocking)
                asyncio.create_task(self._smart_background_sync(start_date, end_date))
                sync_triggered = True
            
            # Record this request pattern for future analysis
            self.db.record_request_pattern(start_date, end_date, data_freshness_seconds, sync_triggered)
        
        # Search in database (using current data, even if potentially stale)
        conversations = self.db.search_conversations(
            query=query,
            start_date=start_date,
            end_date=end_date,
            customer_email=customer_email,
            limit=limit
        )
        
        if not conversations:
            return [TextContent(
                type="text",
                text="No conversations found matching the criteria."
            )]
        
        # Format results
        result_text = f"Found {len(conversations)} conversations:\n\n"
        
        for conv in conversations:
            customer_messages = conv.get_customer_messages()
            admin_messages = conv.get_admin_messages()
            
            result_text += f"**Conversation {conv.id}**\n"
            result_text += f"- Customer: {conv.customer_email or 'Unknown'}\n"
            result_text += f"- Created: {conv.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            result_text += f"- Messages: {len(customer_messages)} from customer, {len(admin_messages)} from support\n"
            
            if conv.tags:
                result_text += f"- Tags: {', '.join(conv.tags)}\n"
            
            # Show first customer message preview
            if customer_messages:
                preview = customer_messages[0].body[:200]
                if len(customer_messages[0].body) > 200:
                    preview += "..."
                result_text += f"- Preview: {preview}\n"
            
            # Add Intercom URL if available
            app_id = await self._get_app_id()
            if app_id:
                result_text += f"- [View in Intercom]({conv.get_url(app_id)})\n"
            
            result_text += "\n"
        
        return [TextContent(type="text", text=result_text)]
    
    async def _get_conversation(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get full conversation details."""
        conversation_id = args.get("conversation_id")
        
        if not conversation_id:
            return [TextContent(
                type="text",
                text="Error: conversation_id is required"
            )]
        
        # Search for the specific conversation
        conversations = self.db.search_conversations(limit=1)
        conversation = None
        
        for conv in conversations:
            if conv.id == conversation_id:
                conversation = conv
                break
        
        if not conversation:
            return [TextContent(
                type="text",
                text=f"Conversation {conversation_id} not found in local database."
            )]
        
        # Format full conversation
        result_text = f"# Conversation {conversation.id}\n\n"
        result_text += f"**Customer:** {conversation.customer_email or 'Unknown'}\n"
        result_text += f"**Created:** {conversation.created_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        result_text += f"**Last Updated:** {conversation.updated_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
        if conversation.tags:
            result_text += f"**Tags:** {', '.join(conversation.tags)}\n"
        
        app_id = await self._get_app_id()
        if app_id:
            result_text += f"**[View in Intercom]({conversation.get_url(app_id)})**\n"
        
        result_text += "\n## Messages\n\n"
        
        for i, message in enumerate(conversation.messages, 1):
            author = "👤 Customer" if message.author_type == "user" else "🎧 Support"
            timestamp = message.created_at.strftime('%m/%d %H:%M')
            
            result_text += f"### {i}. {author} ({timestamp})\n\n"
            result_text += f"{message.body}\n\n"
        
        return [TextContent(type="text", text=result_text)]
    
    async def _get_server_status(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get server status and statistics."""
        status = self.db.get_sync_status()
        sync_status = self.sync_service.get_status()
        
        result_text = "# FastIntercom Server Status\n\n"
        result_text += f"📊 **Storage:** {status['database_size_mb']} MB\n"
        result_text += f"💬 **Conversations:** {status['total_conversations']:,}\n" 
        result_text += f"✉️ **Messages:** {status['total_messages']:,}\n"
        
        if status['last_sync']:
            last_sync = datetime.fromisoformat(status['last_sync'])
            minutes_ago = int((datetime.now() - last_sync).total_seconds() / 60)
            result_text += f"🕒 **Last Sync:** {minutes_ago} minutes ago\n"
        else:
            result_text += f"🕒 **Last Sync:** Never\n"
        
        result_text += f"🔄 **Background Sync:** {'Active' if sync_status['active'] else 'Inactive'}\n"
        
        if sync_status.get('current_operation'):
            result_text += f"⚡ **Current Operation:** {sync_status['current_operation']}\n"
        
        result_text += f"\n📁 **Database:** `{status['database_path']}`\n"
        
        # Recent sync activity
        if status['recent_syncs']:
            result_text += "\n## Recent Sync Activity\n\n"
            for sync in status['recent_syncs'][:3]:
                sync_time = datetime.fromisoformat(sync['last_synced'])
                result_text += f"- {sync_time.strftime('%m/%d %H:%M')}: "
                result_text += f"{sync['conversation_count']} conversations "
                result_text += f"({sync.get('new_conversations', 0)} new)\n"
        
        return [TextContent(type="text", text=result_text)]
    
    async def _sync_conversations(self, args: Dict[str, Any]) -> List[TextContent]:
        """Trigger manual sync."""
        force = args.get("force", False)
        
        result_text = "🔄 Starting manual sync...\n\n"
        
        try:
            if force:
                # Force sync last 7 days
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                stats = await self.sync_service.sync_period(start_date, end_date)
            else:
                # Incremental sync
                stats = await self.sync_service.sync_recent()
            
            result_text += f"✅ **Sync completed successfully!**\n\n"
            result_text += f"📊 **Results:**\n"
            result_text += f"- Total conversations: {stats.total_conversations}\n"
            result_text += f"- New conversations: {stats.new_conversations}\n"  
            result_text += f"- Updated conversations: {stats.updated_conversations}\n"
            result_text += f"- Total messages: {stats.total_messages}\n"
            result_text += f"- Duration: {stats.duration_seconds:.1f} seconds\n"
            result_text += f"- API calls: {stats.api_calls_made}\n"
            
            if stats.errors_encountered > 0:
                result_text += f"- ⚠️ Errors: {stats.errors_encountered}\n"
        
        except Exception as e:
            result_text += f"❌ **Sync failed:** {str(e)}\n"
        
        return [TextContent(type="text", text=result_text)]
    
    def _parse_timeframe(self, timeframe: Optional[str]) -> tuple[Optional[datetime], Optional[datetime]]:
        """Parse natural language timeframe into start/end dates."""
        if not timeframe:
            return None, None
        
        timeframe = timeframe.lower().strip()
        now = datetime.now()
        
        if "last 24 hours" in timeframe or "today" in timeframe:
            return now - timedelta(days=1), now
        elif "last 7 days" in timeframe or "this week" in timeframe:
            return now - timedelta(days=7), now
        elif "last 30 days" in timeframe or "this month" in timeframe:
            return now - timedelta(days=30), now
        elif "last week" in timeframe:
            # Previous week (Monday to Sunday)
            days_since_monday = now.weekday()
            last_monday = now - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            return last_monday, last_sunday
        elif "yesterday" in timeframe:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end
        
        # Default to last 7 days if we can't parse
        return now - timedelta(days=7), now
    
    async def _smart_background_sync(self, start_date: datetime, end_date: datetime):
        """Perform intelligent background sync for a specific timeframe.
        
        This runs in the background and doesn't block the current request.
        The synced data will be available for the next request.
        """
        try:
            logger.info(f"Starting smart background sync for {start_date} to {end_date}")
            
            # Use incremental sync if the timeframe is recent (last 24 hours)
            now = datetime.now()
            if (now - end_date).total_seconds() < 86400:  # 24 hours
                # Incremental sync for recent data
                await self.sync_service.sync_incremental(start_date)
            else:
                # Full period sync for older data
                await self.sync_service.sync_period(start_date, end_date, is_background=True)
            
            logger.info(f"Smart background sync completed for {start_date} to {end_date}")
            
        except Exception as e:
            logger.warning(f"Smart background sync failed for {start_date} to {end_date}: {e}")
    
    async def _get_app_id(self) -> Optional[str]:
        """Get Intercom app ID for URL generation."""
        # This would normally come from the sync service or be cached
        return getattr(self.sync_service, 'app_id', None)
    
    async def run(self):
        """Run the MCP server."""
        logger.info("Starting FastIntercom MCP server...")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )