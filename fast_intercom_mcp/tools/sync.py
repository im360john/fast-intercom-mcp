"""Enhanced sync tools for Fast Intercom MCP."""
from datetime import datetime, timedelta
from typing import Optional, Dict
from ..api.client import IntercomAPIClient
from ..db.connection import db_pool
from ..config import Config
import logging
import asyncio

logger = logging.getLogger(__name__)

api_client = IntercomAPIClient(Config.load().intercom_token)

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
            # Handle both possible response structures
            conversations = response.get('conversations', response.get('data', []))
            
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
    # Extract first contact from contacts list
    contacts = conv.get('contacts', {}).get('contacts', [])
    first_contact = contacts[0] if contacts else {}
    
    # Handle tags structure
    tags_list = conv.get('tags', {}).get('tags', []) if isinstance(conv.get('tags'), dict) else []
    tag_names = [tag['name'] for tag in tags_list if isinstance(tag, dict) and 'name' in tag]
    
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
        str(conv['id']),
        datetime.fromtimestamp(conv['created_at']),
        datetime.fromtimestamp(conv['updated_at']),
        first_contact.get('email'),
        first_contact.get('name'),
        first_contact.get('id'),
        str(conv.get('admin_assignee_id')) if conv.get('admin_assignee_id') else None,
        None,  # assignee name not directly available
        conv['state'],
        conv.get('read', False),
        conv.get('priority'),
        datetime.fromtimestamp(conv['snoozed_until']) if conv.get('snoozed_until') else None,
        tag_names,
        conv.get('conversation_rating', {}).get('rating') if conv.get('conversation_rating') else None,
        conv.get('conversation_rating', {}).get('remark') if conv.get('conversation_rating') else None,
        conv.get('source', {}).get('type'),
        str(conv.get('source', {}).get('id')) if conv.get('source', {}).get('id') else None,
        conv.get('source', {}).get('delivered_as'),
        conv.get('source', {}).get('subject'),
        conv.get('source', {}).get('body'),
        conv.get('source', {}).get('author', {}).get('type') if conv.get('source', {}).get('author') else None,
        str(conv.get('source', {}).get('author', {}).get('id')) if conv.get('source', {}).get('author', {}).get('id') else None,
        conv.get('source', {}).get('author', {}).get('name') if conv.get('source', {}).get('author') else None,
        conv.get('source', {}).get('author', {}).get('email') if conv.get('source', {}).get('author') else None,
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
        str(article['id']),
        article['title'],
        article.get('description'),
        article.get('body'),
        str(article.get('author_id')) if article.get('author_id') else None,
        article['state'],
        datetime.fromtimestamp(article['created_at']),
        datetime.fromtimestamp(article['updated_at']),
        str(article.get('parent_id')) if article.get('parent_id') else None,
        article.get('parent_type'),
        article.get('statistics', {}).get('views', 0),
        article.get('statistics', {}).get('reactions', 0),
        article.get('statistics', {}).get('happy_reactions_percentage', 0.0)
    )

def register_tools(mcp):
    """Register tools with the MCP server"""
    mcp.tool()(sync_conversations)
    mcp.tool()(sync_articles)
    mcp.tool()(get_sync_status)
