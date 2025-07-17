"""Article tools for Fast Intercom MCP."""
from typing import Optional, Dict
from ..api.client import IntercomAPIClient
from ..utils.context_window import context_manager
from ..config import Config
import logging

logger = logging.getLogger(__name__)

api_client = IntercomAPIClient(Config.load().intercom_token)

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
        
        # Handle nested response structure
        data = response.get('data', {})
        if isinstance(data, dict) and 'articles' in data:
            articles = data['articles']
        else:
            articles = data if isinstance(data, list) else []
        
        total_count = response.get('total_count', 0)
        
        # Process articles for response
        processed_articles = []
        config = Config.load()
        
        for article in articles:
            processed = {
                'id': article['id'],
                'title': article['title'],
                'description': article.get('description', ''),
                'state': article.get('state', 'published'),
                'updated_at': article.get('updated_at'),
                'author_id': article.get('author_id'),
                'statistics': article.get('statistics', {
                    'views': 0,
                    'happy_reactions_percentage': 0
                })
            }
            
            if include_preview and 'body' in article:
                # Strip HTML and truncate
                import re
                text = re.sub('<[^<]+?>', '', article['body'])
                processed['body_preview'] = text[:config.max_article_preview_length] + '...' if len(text) > config.max_article_preview_length else text
            
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

def register_tools(mcp):
    """Register tools with the MCP server"""
    mcp.tool()(search_articles)
    mcp.tool()(get_article)
    mcp.tool()(list_articles)
