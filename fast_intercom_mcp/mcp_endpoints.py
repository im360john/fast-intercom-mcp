"""Add MCP tools as FastAPI endpoints for testing."""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from .tools import conversations, articles, sync, tickets
from .db.connection import db_pool
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP Tools"])

@router.post("/conversations/search")
async def api_search_conversations(
    request_body: Dict[str, Any]
) -> Dict[str, Any]:
    """Search conversations via REST API"""
    try:
        query = request_body.get("query")
        timeframe = request_body.get("timeframe")
        customer_email = request_body.get("customer_email")
        state = request_body.get("state")
        limit = request_body.get("limit", 20)
        
        result = await conversations.search_conversations(
            query=query,
            timeframe=timeframe,
            customer_email=customer_email,
            state=state,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error in conversation search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}")
async def api_get_conversation(conversation_id: str, include_parts: bool = True) -> Dict[str, Any]:
    """Get conversation details via REST API"""
    try:
        result = await conversations.get_conversation_details(
            conversation_id=conversation_id,
            include_parts=include_parts
        )
        return result
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/articles/search")
async def api_search_articles(
    request_body: Dict[str, Any]
) -> Dict[str, Any]:
    """Search articles via REST API"""
    try:
        query = request_body.get("query")
        limit = request_body.get("limit", 10)
        include_preview = request_body.get("include_preview", False)
        
        result = await articles.search_articles(
            query=query,
            limit=limit,
            include_preview=include_preview
        )
        return result
    except Exception as e:
        logger.error(f"Error in article search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/articles/{article_id}")
async def api_get_article(article_id: str) -> Dict[str, Any]:
    """Get article details via REST API"""
    try:
        result = await articles.get_article(article_id)
        return result
    except Exception as e:
        logger.error(f"Error getting article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/conversations")
async def api_sync_conversations(days: int = 7, force: bool = False) -> Dict[str, Any]:
    """Sync conversations via REST API"""
    try:
        result = await sync.sync_conversations(days=days, force=force)
        return result
    except Exception as e:
        logger.error(f"Error syncing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/articles")
async def api_sync_articles(force: bool = False) -> Dict[str, Any]:
    """Sync articles via REST API"""
    try:
        result = await sync.sync_articles(force=force)
        return result
    except Exception as e:
        logger.error(f"Error syncing articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync/status")
async def api_get_sync_status() -> Dict[str, Any]:
    """Get sync status via REST API"""
    try:
        result = await sync.get_sync_status()
        return result
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database/stats")
async def api_database_stats() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        async with db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    (SELECT COUNT(*) FROM conversations) as conversations_total,
                    (SELECT COUNT(*) FROM conversations WHERE customer_email IS NOT NULL) as conversations_with_email,
                    (SELECT COUNT(*) FROM conversations WHERE state = 'open') as conversations_open,
                    (SELECT COUNT(*) FROM articles) as articles_total,
                    (SELECT COUNT(*) FROM articles WHERE state = 'published') as articles_published
            """)
            
            return {
                "database_stats": {
                    "conversations": {
                        "total": stats['conversations_total'],
                        "with_email": stats['conversations_with_email'],
                        "open": stats['conversations_open']
                    },
                    "articles": {
                        "total": stats['articles_total'],
                        "published": stats['articles_published']
                    }
                }
            }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))