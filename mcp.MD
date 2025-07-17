Fast-Intercom-MCP Enhancement Implementation Guide
Overview
This guide provides detailed implementation instructions for enhancing the fast-intercom-mcp server with Streamable HTTP transport, Articles sync/search, Tickets integration, and response truncation for AI agents with limited context windows.
Table of Contents

Prerequisites
Phase 1: Database Migration from SQLite to PostgreSQL
Phase 2: Streamable HTTP Transport Implementation
Phase 3: Context Window Management
Phase 4: Intercom API Client
Phase 5: MCP Tools Implementation
Phase 6: Deployment Configuration
Phase 7: Testing
Phase 8: Documentation
Implementation Notes

Prerequisites

Fork https://github.com/evolsb/fast-intercom-mcp
Python 3.9+
PostgreSQL 14+
Intercom API access token with appropriate permissions

Phase 1: Database Migration from SQLite to PostgreSQL
1.1 Update Dependencies
toml# pyproject.toml
[project]
dependencies = [
    "mcp[cli]>=1.8.0",  # Ensure latest version with Streamable HTTP support
    "fastmcp>=2.0.0",   # If using FastMCP 2.0
    "asyncpg>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.13.0",
    "tiktoken>=0.5.0",  # For token counting
    "httpx>=0.25.0",
    # ... existing dependencies
]
1.2 Database Schema
sql-- migrations/001_initial_schema.sql

-- Conversations table (migrated from SQLite)
CREATE TABLE conversations (
    id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    customer_email VARCHAR,
    customer_name VARCHAR,
    customer_id VARCHAR,
    assignee_id VARCHAR,
    assignee_name VARCHAR,
    state VARCHAR NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    priority VARCHAR,
    snoozed_until TIMESTAMP,
    tags TEXT[],
    conversation_rating_value INTEGER,
    conversation_rating_remark TEXT,
    source_type VARCHAR,
    source_id VARCHAR,
    source_delivered_as VARCHAR,
    source_subject TEXT,
    source_body TEXT,
    source_author_type VARCHAR,
    source_author_id VARCHAR,
    source_author_name VARCHAR,
    source_author_email VARCHAR,
    statistics_first_contact_reply_at TIMESTAMP,
    statistics_first_admin_reply_at TIMESTAMP,
    statistics_last_contact_reply_at TIMESTAMP,
    statistics_last_admin_reply_at TIMESTAMP,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(customer_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(customer_email, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(source_subject, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(source_body, '')), 'C')
    ) STORED
);

CREATE INDEX conversations_search_idx ON conversations USING GIN (search_vector);
CREATE INDEX conversations_updated_at_idx ON conversations(updated_at DESC);
CREATE INDEX conversations_customer_email_idx ON conversations(customer_email);

-- Articles table
CREATE TABLE articles (
    id VARCHAR PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    body TEXT,
    author_id VARCHAR,
    state VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    parent_id VARCHAR,
    parent_type VARCHAR,
    statistics_views INTEGER DEFAULT 0,
    statistics_reactions INTEGER DEFAULT 0,
    statistics_happy_reactions_percentage FLOAT,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(body, '')), 'C')
    ) STORED
);

CREATE INDEX articles_search_idx ON articles USING GIN (search_vector);
CREATE INDEX articles_updated_at_idx ON articles(updated_at DESC);
CREATE INDEX articles_state_idx ON articles(state);

-- Sync metadata table
CREATE TABLE sync_metadata (
    entity_type VARCHAR PRIMARY KEY,
    last_sync_at TIMESTAMP,
    sync_status VARCHAR,
    items_synced INTEGER,
    error_message TEXT
);
1.3 Database Connection Manager
python# fast_intercom_mcp/db/connection.py
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncIterator
import os

class DatabasePool:
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv("DATABASE_URL")
        
    async def initialize(self):
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=10,
            max_size=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        async with self.pool.acquire() as connection:
            yield connection

# Global instance
db_pool = DatabasePool()
Phase 2: Streamable HTTP Transport Implementation
2.1 Server Configuration
python# fast_intercom_mcp/server.py
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager
from .db.connection import db_pool
from .config import Config

@asynccontextmanager
async def lifespan(server: FastMCP):
    """Manage server lifecycle"""
    # Initialize database pool
    await db_pool.initialize()
    
    # Initialize any other resources
    yield
    
    # Cleanup
    await db_pool.close()

# Create server instance with stateless HTTP
mcp = FastMCP(
    "fast-intercom-mcp",
    stateless_http=True,
    json_response=True,  # Disable SSE for simpler responses
    lifespan=lifespan
)

# Server configuration
def run_server():
    mcp.run(
        transport="streamable-http",
        host=Config.HTTP_HOST,
        port=Config.HTTP_PORT,
        path=Config.HTTP_PATH
    )
2.2 Configuration Management
python# fast_intercom_mcp/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Streamable HTTP settings
    HTTP_HOST: str = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT: int = int(os.getenv("HTTP_PORT", "8000"))
    HTTP_PATH: str = os.getenv("HTTP_PATH", "/mcp")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost/intercom_mcp")
    
    # Intercom API
    INTERCOM_ACCESS_TOKEN: str = os.getenv("INTERCOM_ACCESS_TOKEN")
    INTERCOM_API_VERSION: str = "2.13"
    INTERCOM_API_BASE_URL: str = "https://api.intercom.io"
    
    # Context window management
    MAX_RESPONSE_TOKENS: int = int(os.getenv("MAX_RESPONSE_TOKENS", "40000"))
    MAX_ITEMS_PER_SEARCH: int = int(os.getenv("MAX_ITEMS_PER_SEARCH", "20"))
    MAX_ARTICLE_PREVIEW_LENGTH: int = 500
    MAX_CONVERSATION_MESSAGES: int = 10
    
    # Rate limiting
    RATE_LIMIT_CALLS: int = 900  # Conservative under 1000/min limit
    RATE_LIMIT_WINDOW: int = 60  # seconds
Phase 3: Context Window Management
3.1 Token Counter and Response Truncator
python# fast_intercom_mcp/utils/context_window.py
import tiktoken
import json
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class TruncationResult:
    data: Any
    truncated: bool
    original_count: int
    returned_count: int
    estimated_tokens: int

class ContextWindowManager:
    def __init__(self, max_tokens: int = 40000):
        self.max_tokens = max_tokens
        self.encoder = tiktoken.get_encoding("cl100k_base")
        
    def estimate_tokens(self, data: Any) -> int:
        """Estimate tokens for any JSON-serializable data"""
        text = json.dumps(data, default=str)
        return len(self.encoder.encode(text))
    
    def truncate_list_response(
        self, 
        items: List[Dict], 
        max_items: int,
        preview_fields: List[str] = None
    ) -> TruncationResult:
        """Truncate list responses intelligently"""
        original_count = len(items)
        
        # Start with max items
        truncated_items = items[:max_items]
        
        # If preview fields specified, create preview versions
        if preview_fields:
            preview_items = []
            for item in truncated_items:
                preview_item = {k: v for k, v in item.items() if k in preview_fields}
                preview_items.append(preview_item)
            truncated_items = preview_items
        
        # Check token count and further truncate if needed
        current_tokens = self.estimate_tokens(truncated_items)
        
        while current_tokens > self.max_tokens and len(truncated_items) > 1:
            truncated_items = truncated_items[:-1]
            current_tokens = self.estimate_tokens(truncated_items)
        
        return TruncationResult(
            data=truncated_items,
            truncated=len(truncated_items) < original_count,
            original_count=original_count,
            returned_count=len(truncated_items),
            estimated_tokens=current_tokens
        )
    
    def create_truncated_response(self, result: TruncationResult, entity_type: str) -> Dict:
        """Create standardized truncated response with AI instructions"""
        response = {
            'data': result.data,
            'meta': {
                'total_items': result.original_count,
                'returned_items': result.returned_count,
                'truncated': result.truncated,
                'estimated_tokens': result.estimated_tokens
            }
        }
        
        if result.truncated:
            suggestions = self._get_refinement_suggestions(entity_type)
            response['assistant_instruction'] = (
                f"⚠️ Response truncated for context window optimization.\n"
                f"Found {result.original_count} {entity_type} but returned only {result.returned_count}.\n"
                f"To get better results, please:\n" + 
                "\n".join(f"• {s}" for s in suggestions)
            )
        
        return response
    
    def _get_refinement_suggestions(self, entity_type: str) -> List[str]:
        """Get entity-specific refinement suggestions"""
        base_suggestions = [
            "Use more specific search terms",
            "Add a timeframe (e.g., 'last 7 days', 'this month')",
            "Search by specific ID if known"
        ]
        
        if entity_type == "conversations":
            base_suggestions.extend([
                "Filter by customer email",
                "Filter by conversation state (open, closed, snoozed)"
            ])
        elif entity_type == "articles":
            base_suggestions.extend([
                "Search by article title keywords",
                "Use get_article with a specific ID for full content"
            ])
        elif entity_type == "tickets":
            base_suggestions.extend([
                "Filter by ticket state",
                "Filter by ticket type",
                "Search by customer email"
            ])
        
        return base_suggestions

# Global instance
context_manager = ContextWindowManager()
Phase 4: Intercom API Client
4.1 Rate-Limited API Client
python# fast_intercom_mcp/api/client.py
import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = datetime.now()
            # Remove old calls outside window
            self.calls = [c for c in self.calls if now - c < timedelta(seconds=self.window_seconds)]
            
            if len(self.calls) >= self.max_calls:
                sleep_time = (self.calls[0] + timedelta(seconds=self.window_seconds) - now).total_seconds()
                await asyncio.sleep(sleep_time)
                return await self.acquire()
            
            self.calls.append(now)

class IntercomAPIClient:
    def __init__(self, access_token: str, api_version: str = "2.13"):
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = "https://api.intercom.io"
        self.rate_limiter = RateLimiter(max_calls=900, window_seconds=60)
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Intercom-Version": api_version
            },
            timeout=30.0
        )
    
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make rate-limited request to Intercom API"""
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Intercom API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 429:
                return {
                    'error': 'rate_limit',
                    'message': 'Intercom API rate limit exceeded. Please try again later.'
                }
            raise
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    # Conversation methods
    async def search_conversations(self, query: Dict) -> Dict:
        return await self.make_request("POST", "/conversations/search", json_data=query)
    
    async def get_conversation(self, conversation_id: str) -> Dict:
        return await self.make_request("GET", f"/conversations/{conversation_id}")
    
    # Article methods
    async def list_articles(self, page: int = 1, per_page: int = 50) -> Dict:
        return await self.make_request("GET", "/articles", params={"page": page, "per_page": per_page})
    
    async def search_articles(self, query: str, page: int = 1) -> Dict:
        return await self.make_request("GET", "/articles/search", params={"q": query, "page": page})
    
    async def get_article(self, article_id: str) -> Dict:
        return await self.make_request("GET", f"/articles/{article_id}")
    
    # Ticket methods
    async def search_tickets(self, query: Dict) -> Dict:
        return await self.make_request("POST", "/tickets/search", json_data=query)
    
    async def get_ticket(self, ticket_id: str) -> Dict:
        return await self.make_request("GET", f"/tickets/{ticket_id}")
    
    async def list_ticket_types(self) -> Dict:
        return await self.make_request("GET", "/ticket_types")
    
    async def list_ticket_states(self) -> Dict:
        return await self.make_request("GET", "/ticket_states")
    
    async def close(self):
        await self.client.aclose()
Phase 5: MCP Tools Implementation
5.1 Conversation Tools (Enhanced)
python# fast_intercom_mcp/tools/conversations.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from ..server import mcp
from ..api.client import IntercomAPIClient
from ..db.connection import db_pool
from ..utils.context_window import context_manager
from ..config import Config
import logging

logger = logging.getLogger(__name__)

# Initialize API client
api_client = IntercomAPIClient(Config.INTERCOM_ACCESS_TOKEN)

@mcp.tool()
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

@mcp.tool()
async def get_conversation_details(conversation_id: str, include_parts: bool = True) -> Dict:
    """
    Get detailed information about a specific conversation.
    
    Args:
        conversation_id: The Intercom conversation ID
        include_parts: Whether to include conversation parts (messages)
    """
    try:
        # Always fetch fresh from API for details
        conversation = await api_client.get_conversation(conversation_id)
        
        if include_parts and 'conversation_parts' in conversation:
            parts = conversation['conversation_parts'].get('conversation_parts', [])
            
            # Limit conversation parts for context window
            if len(parts) > Config.MAX_CONVERSATION_MESSAGES:
                conversation['conversation_parts']['conversation_parts'] = parts[:Config.MAX_CONVERSATION_MESSAGES]
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
5.2 Article Tools
python# fast_intercom_mcp/tools/articles.py
from typing import Optional, Dict
from ..server import mcp
from ..api.client import IntercomAPIClient
from ..utils.context_window import context_manager
from ..config import Config
import logging

logger = logging.getLogger(__name__)

api_client = IntercomAPIClient(Config.INTERCOM_ACCESS_TOKEN)

@mcp.tool()
async def search_articles(
    query: str,
    limit: int = 10,
    include_preview: bool = False
) -> Dict:
    """
    Search for help center articles. Returns titles and descriptions only.
    Use get_article for full content.
    
    Args:
        query: Search query for articles
        limit: Maximum number of articles to return (default: 10)
        include_preview: Include a preview of article body (first 500 chars)
    """
    try:
        # Use Intercom's search endpoint
        response = await api_client.search_articles(query)
        
        articles = response.get('data', [])
        total_count = response.get('total_count', 0)
        
        # Process articles for response
        processed_articles = []
        for article in articles:
            processed = {
                'id': article['id'],
                'title': article['title'],
                'description': article.get('description', ''),
                'state': article.get('state', 'published'),
                'updated_at': article.get('updated_at'),
                'author_id': article.get('author_id'),
                'statistics': {
                    'views': article.get('statistics', {}).get('views', 0),
                    'happy_reactions_percentage': article.get('statistics', {}).get('happy_reactions_percentage', 0)
                }
            }
            
            if include_preview and 'body' in article:
                # Strip HTML and truncate
                import re
                text = re.sub('<[^<]+?>', '', article['body'])
                processed['body_preview'] = text[:Config.MAX_ARTICLE_PREVIEW_LENGTH] + '...' if len(text) > Config.MAX_ARTICLE_PREVIEW_LENGTH else text
            
            processed_articles.append(processed)
        
        # Apply truncation
        truncation_result = context_manager.truncate_list_response(
            processed_articles,
            max_items=limit,
            preview_fields=['id', 'title', 'description', 'state', 'updated_at']
        )
        
        response = context_manager.create_truncated_response(truncation_result, "articles")
        
        # Add search-specific metadata
        response['meta']['search_query'] = query
        response['meta']['total_found'] = total_count
        
        return response
        
    except Exception as e:
        logger.error(f"Error searching articles: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error searching articles. Please try a different search query.'
        }

@mcp.tool()
async def get_article(article_id: str) -> Dict:
    """
    Get full content of a specific article.
    
    Args:
        article_id: The Intercom article ID
    """
    try:
        article = await api_client.get_article(article_id)
        
        # Check if article body is very large
        if 'body' in article:
            body_length = len(article['body'])
            if body_length > 50000:  # Very large article
                article['_warning'] = f"Large article body ({body_length} characters)"
                # Optionally truncate extremely large articles
                if body_length > 100000:
                    article['body'] = article['body'][:100000] + "\n\n[Article truncated due to size]"
        
        return article
        
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': f'Could not retrieve article {article_id}. Please verify the ID.'
        }

@mcp.tool()
async def list_articles(
    limit: int = 20,
    state: Optional[str] = "published"
) -> Dict:
    """
    List articles with pagination support.
    
    Args:
        limit: Maximum number of articles to return
        state: Filter by article state (published, draft)
    """
    try:
        response = await api_client.list_articles(per_page=min(limit * 2, 100))
        
        articles = response.get('data', [])
        
        # Filter by state if specified
        if state:
            articles = [a for a in articles if a.get('state') == state]
        
        # Process for response
        processed_articles = []
        for article in articles:
            processed = {
                'id': article['id'],
                'title': article['title'],
                'description': article.get('description', ''),
                'state': article.get('state', 'published'),
                'updated_at': article.get('updated_at'),
                'parent_id': article.get('parent_id'),
                'parent_type': article.get('parent_type')
            }
            processed_articles.append(processed)
        
        # Apply truncation
        truncation_result = context_manager.truncate_list_response(
            processed_articles,
            max_items=limit,
            preview_fields=['id', 'title', 'state', 'updated_at']
        )
        
        return context_manager.create_truncated_response(truncation_result, "articles")
        
    except Exception as e:
        logger.error(f"Error listing articles: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error listing articles. Please try again.'
        }
5.3 Ticket Tools
python# fast_intercom_mcp/tools/tickets.py
from typing import Optional, Dict, List
from ..server import mcp
from ..api.client import IntercomAPIClient
from ..utils.context_window import context_manager
from ..config import Config
import logging

logger = logging.getLogger(__name__)

api_client = IntercomAPIClient(Config.INTERCOM_ACCESS_TOKEN)

@mcp.tool()
async def search_tickets(
    query: Optional[str] = None,
    customer_email: Optional[str] = None,
    ticket_state: Optional[str] = None,
    ticket_type_id: Optional[str] = None,
    limit: int = 20
) -> Dict:
    """
    Search tickets without local storage. Queries Intercom API directly.
    
    Args:
        query: Text to search in ticket content
        customer_email: Filter by customer email
        ticket_state: Filter by state (submitted, in_progress, waiting_on_customer, on_hold, resolved)
        ticket_type_id: Filter by ticket type ID
        limit: Maximum tickets to return
    """
    try:
        # Build search query for Intercom API
        search_query = {
            "query": {}
        }
        
        # Add filters based on parameters
        filters = []
        
        if customer_email:
            filters.append({
                "field": "contact.email",
                "operator": "=",
                "value": customer_email
            })
        
        if ticket_state:
            filters.append({
                "field": "state",
                "operator": "=",
                "value": ticket_state
            })
        
        if ticket_type_id:
            filters.append({
                "field": "ticket_type_id",
                "operator": "=",
                "value": ticket_type_id
            })
        
        if filters:
            search_query["query"]["filter"] = {
                "type": "AND",
                "filters": filters
            }
        
        # Execute search
        response = await api_client.search_tickets(search_query)
        
        tickets = response.get('data', [])
        total_count = response.get('total_count', 0)
        
        # Process tickets for response
        processed_tickets = []
        for ticket in tickets:
            processed = {
                'id': ticket['id'],
                'ticket_id': ticket.get('ticket_id'),
                'category': ticket.get('category'),
                'ticket_state': ticket.get('ticket_state', {}).get('name'),
                'ticket_type': ticket.get('ticket_type', {}).get('name'),
                'created_at': ticket.get('created_at'),
                'updated_at': ticket.get('updated_at'),
                'is_open': ticket.get('open'),
                'assigned_to': None,
                'contacts': []
            }
            
            # Extract assignee info
            if 'admin_assignee_id' in ticket and ticket['admin_assignee_id']:
                processed['assigned_to'] = {
                    'type': 'admin',
                    'id': ticket['admin_assignee_id']
                }
            elif 'team_assignee_id' in ticket and ticket['team_assignee_id']:
                processed['assigned_to'] = {
                    'type': 'team',
                    'id': ticket['team_assignee_id']
                }
            
            # Extract contact info
            for contact in ticket.get('contacts', {}).get('contacts', []):
                processed['contacts'].append({
                    'id': contact.get('id'),
                    'email': contact.get('email')
                })
            
            # Add ticket attributes preview
            if 'ticket_attributes' in ticket:
                attrs = ticket['ticket_attributes']
                processed['title'] = attrs.get('_default_title_', 'No title')
                processed['description_preview'] = (attrs.get('_default_description_', '')[:200] + '...' 
                                                   if len(attrs.get('_default_description_', '')) > 200 
                                                   else attrs.get('_default_description_', ''))
            
            processed_tickets.append(processed)
        
        # Apply truncation
        truncation_result = context_manager.truncate_list_response(
            processed_tickets,
            max_items=limit,
            preview_fields=['id', 'ticket_id', 'title', 'ticket_state', 'created_at', 'contacts']
        )
        
        response = context_manager.create_truncated_response(truncation_result, "tickets")
        response['meta']['total_found'] = total_count
        
        if query:
            response['meta']['search_query'] = query
        
        return response
        
    except Exception as e:
        logger.error(f"Error searching tickets: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error searching tickets. Please try different search criteria.'
        }

@mcp.tool()
async def get_ticket(ticket_id: str, include_parts: bool = True) -> Dict:
    """
    Get detailed information about a specific ticket.
    
    Args:
        ticket_id: The Intercom ticket ID
        include_parts: Whether to include ticket parts (comments/notes)
    """
    try:
        ticket = await api_client.get_ticket(ticket_id)
        
        # Process ticket parts if included
        if include_parts and 'ticket_parts' in ticket:
            parts = ticket['ticket_parts'].get('ticket_parts', [])
            
            # Limit parts for context window
            if len(parts) > Config.MAX_CONVERSATION_MESSAGES:
                ticket['ticket_parts']['ticket_parts'] = parts[:Config.MAX_CONVERSATION_MESSAGES]
                ticket['_truncated_parts'] = True
                ticket['_total_parts'] = len(parts)
        
        return ticket
        
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': f'Could not retrieve ticket {ticket_id}. Please verify the ID.'
        }

@mcp.tool()
async def list_ticket_types() -> Dict:
    """
    List all available ticket types.
    """
    try:
        response = await api_client.list_ticket_types()
        
        ticket_types = response.get('data', [])
        
        # Simplify response
        processed_types = []
        for tt in ticket_types:
            processed = {
                'id': tt['id'],
                'name': tt['name'],
                'description': tt.get('description', ''),
                'icon': tt.get('icon', ''),
                'category': tt.get('category'),
                'is_internal': tt.get('is_internal', False),
                'archived': tt.get('archived', False)
            }
            processed_types.append(processed)
        
        return {
            'ticket_types': processed_types,
            'total': len(processed_types)
        }
        
    except Exception as e:
        logger.error(f"Error listing ticket types: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error listing ticket types. Please try again.'
        }

@mcp.tool()
async def list_ticket_states() -> Dict:
    """
    List all available ticket states.
    """
    try:
        response = await api_client.list_ticket_states()
        
        states = response.get('data', [])
        
        # Simplify response
        processed_states = []
        for state in states:
            processed = {
                'id': state['id'],
                'name': state['name'],
                'state': state.get('state'),
                'description': state.get('description', ''),
                'archived': state.get('archived', False)
            }
            processed_states.append(processed)
        
        return {
            'ticket_states': processed_states,
            'total': len(processed_states)
        }
        
    except Exception as e:
        logger.error(f"Error listing ticket states: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error listing ticket states. Please try again.'
        }
5.4 Sync Tools (Enhanced)
python# fast_intercom_mcp/tools/sync.py
from datetime import datetime, timedelta
from typing import Optional
from ..server import mcp
from ..api.client import IntercomAPIClient
from ..db.connection import db_pool
from ..config import Config
import logging
import asyncio

logger = logging.getLogger(__name__)

api_client = IntercomAPIClient(Config.INTERCOM_ACCESS_TOKEN)

@mcp.tool()
async def sync_conversations(
    days: int = 7,
    force: bool = False
) -> Dict:
    """
    Sync conversations from Intercom to local database.
    
    Args:
        days: Number of days to sync (default: 7)
        force: Force full sync even if recent sync exists
    """
    try:
        async with db_pool.acquire() as conn:
            # Check last sync
            if not force:
                last_sync = await conn.fetchval(
                    "SELECT last_sync_at FROM sync_metadata WHERE entity_type = 'conversations'"
                )
                if last_sync and (datetime.now() - last_sync).total_seconds() < 300:  # 5 minutes
                    return {
                        'status': 'skipped',
                        'message': 'Recent sync exists. Use force=true to override.',
                        'last_sync': last_sync.isoformat()
                    }
            
            # Start sync
            await conn.execute(
                "INSERT INTO sync_metadata (entity_type, sync_status, last_sync_at) "
                "VALUES ('conversations', 'in_progress', $1) "
                "ON CONFLICT (entity_type) DO UPDATE SET sync_status = 'in_progress', last_sync_at = $1",
                datetime.now()
            )
        
        # Calculate date range
        updated_since = datetime.now() - timedelta(days=days)
        
        # Sync conversations
        total_synced = 0
        page = 1
        
        while True:
            search_query = {
                "query": {
                    "field": "updated_at",
                    "operator": ">",
                    "value": int(updated_since.timestamp())
                },
                "pagination": {
                    "per_page": 100,
                    "page": page
                }
            }
            
            response = await api_client.search_conversations(search_query)
            conversations = response.get('data', [])
            
            if not conversations:
                break
            
            # Batch insert conversations
            async with db_pool.acquire() as conn:
                for conv in conversations:
                    await upsert_conversation(conn, conv)
            
            total_synced += len(conversations)
            page += 1
            
            # Respect rate limits
            await asyncio.sleep(0.1)
        
        # Update sync metadata
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sync_metadata SET sync_status = 'completed', items_synced = $1, error_message = NULL "
                "WHERE entity_type = 'conversations'",
                total_synced
            )
        
        return {
            'status': 'completed',
            'conversations_synced': total_synced,
            'sync_duration_days': days
        }
        
    except Exception as e:
        logger.error(f"Error syncing conversations: {str(e)}")
        
        # Update sync metadata with error
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sync_metadata SET sync_status = 'failed', error_message = $1 "
                "WHERE entity_type = 'conversations'",
                str(e)
            )
        
        return {
            'error': str(e),
            'assistant_instruction': 'Sync failed. Please check the error and try again.'
        }

@mcp.tool()
async def sync_articles(force: bool = False) -> Dict:
    """
    Sync all articles from Intercom to local database.
    
    Args:
        force: Force full sync even if recent sync exists
    """
    try:
        async with db_pool.acquire() as conn:
            # Check last sync
            if not force:
                last_sync = await conn.fetchval(
                    "SELECT last_sync_at FROM sync_metadata WHERE entity_type = 'articles'"
                )
                if last_sync and (datetime.now() - last_sync).total_seconds() < 3600:  # 1 hour
                    return {
                        'status': 'skipped',
                        'message': 'Recent sync exists. Use force=true to override.',
                        'last_sync': last_sync.isoformat()
                    }
            
            # Start sync
            await conn.execute(
                "INSERT INTO sync_metadata (entity_type, sync_status, last_sync_at) "
                "VALUES ('articles', 'in_progress', $1) "
                "ON CONFLICT (entity_type) DO UPDATE SET sync_status = 'in_progress', last_sync_at = $1",
                datetime.now()
            )
        
        # Sync all articles
        total_synced = 0
        page = 1
        
        while True:
            response = await api_client.list_articles(page=page, per_page=100)
            articles = response.get('data', [])
            
            if not articles:
                break
            
            # Batch insert articles
            async with db_pool.acquire() as conn:
                for article in articles:
                    await upsert_article(conn, article)
            
            total_synced += len(articles)
            page += 1
            
            # Respect rate limits
            await asyncio.sleep(0.1)
        
        # Update sync metadata
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sync_metadata SET sync_status = 'completed', items_synced = $1, error_message = NULL "
                "WHERE entity_type = 'articles'",
                total_synced
            )
        
        return {
            'status': 'completed',
            'articles_synced': total_synced
        }
        
    except Exception as e:
        logger.error(f"Error syncing articles: {str(e)}")
        
        # Update sync metadata with error
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sync_metadata SET sync_status = 'failed', error_message = $1 "
                "WHERE entity_type = 'articles'",
                str(e)
            )
        
        return {
            'error': str(e),
            'assistant_instruction': 'Sync failed. Please check the error and try again.'
        }

@mcp.tool()
async def get_sync_status() -> Dict:
    """
    Get the current sync status for all entity types.
    """
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM sync_metadata ORDER BY entity_type")
        
        statuses = {}
        for row in rows:
            statuses[row['entity_type']] = {
                'last_sync': row['last_sync_at'].isoformat() if row['last_sync_at'] else None,
                'status': row['sync_status'],
                'items_synced': row['items_synced'],
                'error': row['error_message']
            }
        
        # Get counts from database
        async with db_pool.acquire() as conn:
            conv_count = await conn.fetchval("SELECT COUNT(*) FROM conversations")
            article_count = await conn.fetchval("SELECT COUNT(*) FROM articles")
        
        return {
            'sync_statuses': statuses,
            'database_counts': {
                'conversations': conv_count,
                'articles': article_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        return {
            'error': str(e),
            'assistant_instruction': 'Error getting sync status. Please try again.'
        }

# Helper functions
async def upsert_conversation(conn, conv: Dict):
    """Upsert a conversation to the database"""
    await conn.execute("""
        INSERT INTO conversations (
            id, created_at, updated_at, customer_email, customer_name, customer_id,
            assignee_id, assignee_name, state, read, priority, snoozed_until,
            tags, conversation_rating_value, conversation_rating_remark,
            source_type, source_id, source_delivered_as, source_subject, source_body,
            source_author_type, source_author_id, source_author_name, source_author_email,
            statistics_first_contact_reply_at, statistics_first_admin_reply_at,
            statistics_last_contact_reply_at, statistics_last_admin_reply_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                  $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28)
        ON CONFLICT (id) DO UPDATE SET
            updated_at = EXCLUDED.updated_at,
            state = EXCLUDED.state,
            read = EXCLUDED.read,
            assignee_id = EXCLUDED.assignee_id,
            assignee_name = EXCLUDED.assignee_name,
            priority = EXCLUDED.priority,
            snoozed_until = EXCLUDED.snoozed_until,
            tags = EXCLUDED.tags
    """, 
        conv['id'],
        datetime.fromtimestamp(conv['created_at']),
        datetime.fromtimestamp(conv['updated_at']),
        conv.get('customer', {}).get('email'),
        conv.get('customer', {}).get('name'),
        conv.get('customer', {}).get('id'),
        conv.get('assignee', {}).get('id') if conv.get('assignee') else None,
        conv.get('assignee', {}).get('name') if conv.get('assignee') else None,
        conv['state'],
        conv.get('read', False),
        conv.get('priority'),
        datetime.fromtimestamp(conv['snoozed_until']) if conv.get('snoozed_until') else None,
        [tag['name'] for tag in conv.get('tags', {}).get('tags', [])],
        conv.get('conversation_rating', {}).get('rating'),
        conv.get('conversation_rating', {}).get('remark'),
        conv.get('source', {}).get('type'),
        conv.get('source', {}).get('id'),
        conv.get('source', {}).get('delivered_as'),
        conv.get('source', {}).get('subject'),
        conv.get('source', {}).get('body'),
        conv.get('source', {}).get('author', {}).get('type'),
        conv.get('source', {}).get('author', {}).get('id'),
        conv.get('source', {}).get('author', {}).get('name'),
        conv.get('source', {}).get('author', {}).get('email'),
        datetime.fromtimestamp(conv.get('statistics', {}).get('first_contact_reply_at')) if conv.get('statistics', {}).get('first_contact_reply_at') else None,
        datetime.fromtimestamp(conv.get('statistics', {}).get('first_admin_reply_at')) if conv.get('statistics', {}).get('first_admin_reply_at') else None,
        datetime.fromtimestamp(conv.get('statistics', {}).get('last_contact_reply_at')) if conv.get('statistics', {}).get('last_contact_reply_at') else None,
        datetime.fromtimestamp(conv.get('statistics', {}).get('last_admin_reply_at')) if conv.get('statistics', {}).get('last_admin_reply_at') else None
    )

async def upsert_article(conn, article: Dict):
    """Upsert an article to the database"""
    await conn.execute("""
        INSERT INTO articles (
            id, title, description, body, author_id, state,
            created_at, updated_at, parent_id, parent_type,
            statistics_views, statistics_reactions, statistics_happy_reactions_percentage
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            body = EXCLUDED.body,
            state = EXCLUDED.state,
            updated_at = EXCLUDED.updated_at,
            statistics_views = EXCLUDED.statistics_views,
            statistics_reactions = EXCLUDED.statistics_reactions,
            statistics_happy_reactions_percentage = EXCLUDED.statistics_happy_reactions_percentage
    """,
        article['id'],
        article['title'],
        article.get('description'),
        article.get('body'),
        article.get('author_id'),
        article['state'],
        datetime.fromtimestamp(article['created_at']),
        datetime.fromtimestamp(article['updated_at']),
        article.get('parent_id'),
        article.get('parent_type'),
        article.get('statistics', {}).get('views', 0),
        article.get('statistics', {}).get('reactions', 0),
        article.get('statistics', {}).get('happy_reactions_percentage', 0.0)
    )
Phase 6: Deployment Configuration
6.1 Docker Configuration
dockerfile# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY fast_intercom_mcp/ ./fast_intercom_mcp/

# Install Python dependencies
RUN pip install -e .

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "-m", "fast_intercom_mcp.server"]
6.2 Docker Compose
yaml# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: intercom_mcp
      POSTGRES_USER: intercom
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

  mcp-server:
    build: .
    environment:
      DATABASE_URL: postgresql://intercom:${POSTGRES_PASSWORD}@postgres/intercom_mcp
      INTERCOM_ACCESS_TOKEN: ${INTERCOM_ACCESS_TOKEN}
      HTTP_HOST: 0.0.0.0
      HTTP_PORT: 8000
      HTTP_PATH: /mcp
      MAX_RESPONSE_TOKENS: 40000
      MAX_ITEMS_PER_SEARCH: 20
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
6.3 Environment Configuration
bash# .env.example
# Database
DATABASE_URL=postgresql://user:password@localhost/intercom_mcp
POSTGRES_PASSWORD=secure_password

# Intercom API
INTERCOM_ACCESS_TOKEN=your_intercom_access_token

# Server Configuration
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
HTTP_PATH=/mcp

# Context Window Management
MAX_RESPONSE_TOKENS=40000
MAX_ITEMS_PER_SEARCH=20
MAX_ARTICLE_PREVIEW_LENGTH=500
MAX_CONVERSATION_MESSAGES=10

# Logging
LOG_LEVEL=INFO
Phase 7: Testing
7.1 Unit Tests
python# tests/test_context_window.py
import pytest
from fast_intercom_mcp.utils.context_window import ContextWindowManager

def test_token_estimation():
    manager = ContextWindowManager(max_tokens=1000)
    
    # Test simple text
    tokens = manager.estimate_tokens("Hello world")
    assert tokens > 0
    
    # Test JSON data
    data = {"key": "value" * 100}
    tokens = manager.estimate_tokens(data)
    assert tokens > 100

def test_list_truncation():
    manager = ContextWindowManager(max_tokens=1000)
    
    # Create large list
    items = [{"id": i, "data": "x" * 100} for i in range(100)]
    
    result = manager.truncate_list_response(items, max_items=10)
    
    assert result.truncated == True
    assert result.returned_count == 10
    assert result.original_count == 100

def test_truncated_response_format():
    manager = ContextWindowManager()
    
    # Create truncation result
    from fast_intercom_mcp.utils.context_window import TruncationResult
    result = TruncationResult(
        data=[{"id": 1}],
        truncated=True,
        original_count=100,
        returned_count=1,
        estimated_tokens=50
    )
    
    response = manager.create_truncated_response(result, "test_entity")
    
    assert 'data' in response
    assert 'meta' in response
    assert 'assistant_instruction' in response
    assert response['meta']['truncated'] == True
7.2 Integration Tests
python# tests/test_mcp_tools.py
import pytest
from fastapi.testclient import TestClient
from fast_intercom_mcp.server import mcp

@pytest.fixture
def client():
    # Create test client
    app = mcp.streamable_http_app()
    return TestClient(app)

def test_search_conversations_tool(client):
    # Test MCP tool call
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_conversations",
            "arguments": {
                "query": "test",
                "limit": 5
            }
        },
        "id": 1
    }
    
    response = client.post("/mcp", json=request)
    assert response.status_code == 200
    
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert "result" in result

def test_context_window_truncation(client):
    # Test with large limit to trigger truncation
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_articles",
            "arguments": {
                "query": "help",
                "limit": 1000
            }
        },
        "id": 1
    }
    
    response = client.post("/mcp", json=request)
    result = response.json()
    
    # Check for truncation indicators
    data = result["result"]["content"][0]["text"]
    assert "truncated" in data or "assistant_instruction" in data
Phase 8: Documentation
8.1 API Documentation
markdown# Fast-Intercom-MCP API Documentation

## Available Tools

### Conversations

#### search_conversations
Search for conversations with automatic response truncation.

**Parameters:**
- `query` (optional): Text to search in conversation messages
- `timeframe` (optional): Natural language timeframe (e.g., 'last 7 days')
- `customer_email` (optional): Filter by specific customer email
- `state` (optional): Filter by state (open, closed, snoozed)
- `limit` (default: 20): Maximum conversations to return

**Response includes:**
- Truncated list of conversations
- Metadata about total results and truncation
- Assistant instructions if truncated

#### get_conversation_details
Get detailed information about a specific conversation.

**Parameters:**
- `conversation_id`: The Intercom conversation ID
- `include_parts` (default: true): Whether to include conversation parts

### Articles

#### search_articles
Search for help center articles.

**Parameters:**
- `query`: Search query for articles
- `limit` (default: 10): Maximum articles to return
- `include_preview` (default: false): Include article body preview

#### get_article
Get full content of a specific article.

**Parameters:**
- `article_id`: The Intercom article ID

### Tickets

#### search_tickets
Search tickets (direct API calls, no local storage).

**Parameters:**
- `query` (optional): Text to search in ticket content
- `customer_email` (optional): Filter by customer email
- `ticket_state` (optional): Filter by state
- `ticket_type_id` (optional): Filter by ticket type ID
- `limit` (default: 20): Maximum tickets to return

#### get_ticket
Get detailed information about a specific ticket.

**Parameters:**
- `ticket_id`: The Intercom ticket ID
- `include_parts` (default: true): Whether to include ticket parts

## Response Format

All responses follow a consistent format:

```json
{
  "data": [...],
  "meta": {
    "total_items": 100,
    "returned_items": 20,
    "truncated": true,
    "estimated_tokens": 35000
  },
  "assistant_instruction": "Response truncated. Found 100 items but returned only 20..."
}

### 8.2 Deployment Guide
```markdown
# Deployment Guide

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fast-intercom-mcp.git
cd fast-intercom-mcp

Set up environment variables:

bashcp .env.example .env
# Edit .env with your configuration

Run with Docker Compose:

bashdocker-compose up -d

Verify deployment:

bashcurl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
Production Deployment
Using Docker
bashdocker build -t fast-intercom-mcp .
docker run -d \
  --name fast-intercom-mcp \
  -p 8000:8000 \
  --env-file .env \
  fast-intercom-mcp
Using systemd
Create /etc/systemd/system/fast-intercom-mcp.service:
ini[Unit]
Description=Fast Intercom MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=mcpuser
WorkingDirectory=/opt/fast-intercom-mcp
Environment="PATH=/opt/fast-intercom-mcp/venv/bin"
EnvironmentFile=/opt/fast-intercom-mcp/.env
ExecStart=/opt/fast-intercom-mcp/venv/bin/python -m fast_intercom_mcp.server
Restart=always

[Install]
WantedBy=multi-user.target
Nginx Reverse Proxy
nginxserver {
    listen 443 ssl http2;
    server_name mcp.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /mcp {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
Monitoring
Health Check Endpoint
The server exposes a health check at:
POST /mcp
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_sync_status"
  },
  "id": 1
}
Logging
Logs are written to stdout and can be collected using your preferred log aggregation service.
Metrics
Consider adding Prometheus metrics for:

Request count and latency
Token usage per request
Truncation frequency
API rate limit usage


## Implementation Notes

1. **Start with Phase 1-2**: Get the basic infrastructure working with PostgreSQL and Streamable HTTP
2. **Test thoroughly**: Each phase should be tested before moving to the next
3. **Monitor token usage**: The context window management is critical for AI agent performance
4. **Rate limiting**: Be conservative with Intercom API calls to avoid hitting limits
5. **Error handling**: Ensure all errors return helpful instructions for the AI agent
6. **Security**: Consider adding authentication to the Streamable HTTP endpoint
7. **Performance**: Use database indexes and connection pooling for optimal performance
8. **Scalability**: The stateless design allows horizontal scaling behind a load balancer

This implementation guide provides a complete path from forking the repository to having a production-ready MCP server with all requested enhancements.