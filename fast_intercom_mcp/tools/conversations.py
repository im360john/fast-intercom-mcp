"""Enhanced conversation tools for Fast Intercom MCP."""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from ..api.client import IntercomAPIClient
from ..db.connection import db_pool
from ..utils.context_window import context_manager
from ..config import Config
import logging

logger = logging.getLogger(__name__)

async def search_conversations(
    query: Optional[str] = None,
    timeframe: Optional[str] = None,
    customer_email: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 20
) -> Dict:
    """
    Search conversations with automatic response truncation.
    
    Args:
        query: Text to search in conversation messages
        timeframe: Natural language timeframe (e.g., 'last 7 days', 'this month')
        customer_email: Filter by specific customer email
        state: Filter by conversation state (open, closed, snoozed)
        limit: Maximum conversations to return (default: 20)
    """
    try:
        # First try local database search
        async with db_pool.acquire() as conn:
            sql_parts = ["SELECT * FROM conversations WHERE 1=1"]
            params = []
            param_count = 0
            
            if query:
                param_count += 1
                sql_parts.append(f"AND search_vector @@ plainto_tsquery('english', ${param_count})")
                params.append(query)
            
            if customer_email:
                param_count += 1
                sql_parts.append(f"AND customer_email = ${param_count}")
                params.append(customer_email)
            
            if state:
                param_count += 1
                sql_parts.append(f"AND state = ${param_count}")
                params.append(state)
            
            if timeframe:
                cutoff_date = parse_timeframe(timeframe)
                param_count += 1
                sql_parts.append(f"AND updated_at >= ${param_count}")
                params.append(cutoff_date)
            
            sql_parts.append("ORDER BY updated_at DESC")
            sql_parts.append(f"LIMIT {limit * 2}")  # Fetch extra for truncation
            
            sql = " ".join(sql_parts)
            rows = await conn.fetch(sql, *params)
            
        conversations = [dict(row) for row in rows]
        
        # Apply context window truncation
        truncation_result = context_manager.truncate_list_response(
            conversations,
            max_items=limit,
            preview_fields=['id', 'customer_email', 'customer_name', 'state', 
                          'updated_at', 'source_subject', 'assignee_name']
        )
        
        return context_manager.create_truncated_response(truncation_result, "conversations")
        
    except Exception as e:
        logger.error(f"Error searching conversations: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error searching conversations. Please try again or use different search criteria.'
        }

async def get_conversation_details(conversation_id: str, include_parts: bool = True) -> Dict:
    """
    Get detailed information about a specific conversation.
    
    Args:
        conversation_id: The Intercom conversation ID
        include_parts: Whether to include conversation parts (messages)
    """
    try:
        # Initialize API client
        config = Config.load()
        api_client = IntercomAPIClient(config.intercom_token)
        
        # Always fetch fresh from API for details
        conversation = await api_client.get_conversation(conversation_id)
        
        if include_parts and 'conversation_parts' in conversation:
            parts = conversation['conversation_parts'].get('conversation_parts', [])
            
            # Limit conversation parts for context window
            if len(parts) > config.max_conversation_messages:
                conversation['conversation_parts']['conversation_parts'] = parts[:config.max_conversation_messages]
                conversation['_truncated_parts'] = True
                conversation['_total_parts'] = len(parts)
        
        # Estimate tokens and warn if large
        tokens = context_manager.estimate_tokens(conversation)
        if tokens > 10000:
            conversation['_warning'] = f"Large conversation ({tokens} estimated tokens)"
        
        return conversation
        
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': f'Could not retrieve conversation {conversation_id}. Please verify the ID.'
        }
    finally:
        if 'api_client' in locals():
            await api_client.close()

def parse_timeframe(timeframe: str) -> datetime:
    """Parse natural language timeframe to datetime"""
    now = datetime.now()
    timeframe_lower = timeframe.lower()
    
    if 'today' in timeframe_lower:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif 'yesterday' in timeframe_lower:
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif 'week' in timeframe_lower:
        days = 7
        if 'last' in timeframe_lower:
            return now - timedelta(days=days)
        return now - timedelta(days=days)
    elif 'month' in timeframe_lower:
        days = 30
        if 'last' in timeframe_lower:
            return now - timedelta(days=days)
        return now - timedelta(days=days)
    elif 'days' in timeframe_lower:
        # Extract number of days
        import re
        match = re.search(r'(\d+)\s*days?', timeframe_lower)
        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)
    
    # Default to last 7 days
    return now - timedelta(days=7)

def register_tools(mcp):
    """Register conversation tools with the MCP server"""
    mcp.tool()(search_conversations)
    mcp.tool()(get_conversation_details)