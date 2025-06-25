"""Intercom API client with intelligent sync capabilities and performance optimization."""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Callable
import logging

import httpx

from .models import Conversation, Message, ConversationFilters, SyncStats
from .transport.rate_limiter import AdaptiveRateLimiter, RateLimitConfig
from .transport.optimization import APIOptimizer, OptimizationConfig


logger = logging.getLogger(__name__)


class IntercomClient:
    """Enhanced Intercom API client with performance optimization and intelligent rate limiting."""
    
    def __init__(self, access_token: str, rate_limit_config: RateLimitConfig = None, 
                 optimization_config: OptimizationConfig = None):
        self.access_token = access_token
        self.base_url = "https://api.intercom.io"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._app_id = None
        
        # Enhanced rate limiting and optimization
        self.rate_limiter = AdaptiveRateLimiter(rate_limit_config or RateLimitConfig())
        self.optimizer = APIOptimizer(optimization_config or OptimizationConfig())
        
        # Legacy rate limiting (for backward compatibility)
        self._request_times = []
        self._max_requests_per_window = 80  # Be conservative 
        self._window_seconds = 10
        
        # Performance monitoring
        self._performance_callbacks: List[Callable] = []
    
    def add_performance_callback(self, callback: Callable):
        """Add a callback for performance monitoring."""
        self._performance_callbacks.append(callback)
        self.rate_limiter.add_performance_callback(callback)
    
    async def get_app_id(self) -> Optional[str]:
        """Get the Intercom app ID for generating conversation URLs."""
        if self._app_id:
            return self._app_id
            
        try:
            # Use optimized request with caching
            cache_key = "app_id"
            data = await self._make_optimized_request(
                "GET", f"{self.base_url}/me", 
                cache_key=cache_key, cache_ttl=3600,  # Cache for 1 hour
                priority="high"
            )
            
            if data.get("app") and data["app"].get("id_code"):
                self._app_id = str(data["app"]["id_code"])
                logger.info(f"Retrieved app ID: {self._app_id}")
                return self._app_id
        except Exception as e:
            logger.warning(f"Failed to get app ID: {e}")
        
        return None
    
    async def _make_optimized_request(self, method: str, url: str, 
                                    data: Any = None, cache_key: str = None,
                                    cache_ttl: int = None, priority: str = "normal") -> Any:
        """Make an optimized API request with rate limiting and caching."""
        # Apply intelligent rate limiting
        delay = await self.rate_limiter.acquire(priority)
        
        try:
            # Use optimized request
            result = await self.optimizer.make_request(
                method=method,
                url=url,
                headers=self.headers,
                data=data,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
                priority=priority
            )
            
            # Report successful request for adaptive learning
            self.rate_limiter.report_successful_request()
            
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit hit
                retry_after = e.response.headers.get('Retry-After')
                retry_seconds = float(retry_after) if retry_after else None
                self.rate_limiter.report_rate_limit_hit(retry_seconds)
                
                # Re-raise to let caller handle
                raise
            else:
                raise
    
    async def _rate_limit(self):
        """Legacy rate limiting method for backward compatibility."""
        # Use the new adaptive rate limiter
        await self.rate_limiter.acquire("normal")
    
    async def fetch_conversations_incremental(
        self,
        since_timestamp: datetime,
        until_timestamp: Optional[datetime] = None,
        progress_callback: Optional[Callable] = None
    ) -> SyncStats:
        """Fetch conversations that have been updated since the given timestamp.
        
        Args:
            since_timestamp: Only fetch conversations updated after this time
            until_timestamp: Only fetch conversations updated before this time (optional)
            progress_callback: Optional callback for progress updates
            
        Returns:
            SyncStats with information about what was synced
        """
        start_time = time.time()
        conversations = []
        api_calls = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build search filters
            search_filters = [
                {
                    "field": "updated_at",
                    "operator": ">",
                    "value": int(since_timestamp.timestamp())
                }
            ]
            
            if until_timestamp:
                search_filters.append({
                    "field": "updated_at", 
                    "operator": "<",
                    "value": int(until_timestamp.timestamp())
                })
            
            # Build query
            if len(search_filters) == 1:
                query = search_filters[0]
            else:
                query = {"operator": "AND", "value": search_filters}
            
            # Paginate through results
            page = 1
            per_page = 150  # Max for search API
            total_found = 0
            
            while True:
                request_body = {
                    "query": query,
                    "pagination": {"per_page": per_page, "page": page},
                    "sort": {"field": "updated_at", "order": "desc"}
                }
                
                logger.debug(f"Fetching incremental page {page}")
                
                # Use optimized request with caching for search results
                cache_key = f"search_incremental_{hash(str(request_body))}"
                data = await self._make_optimized_request(
                    "POST",
                    f"{self.base_url}/conversations/search",
                    data=request_body,
                    cache_key=cache_key,
                    cache_ttl=60,  # Cache search results for 1 minute
                    priority="high"
                )
                api_calls += 1
                page_conversations = data.get("conversations", [])
                
                if not page_conversations:
                    break
                
                # Parse conversations
                for conv_data in page_conversations:
                    conversation = self._parse_conversation_from_search(conv_data)
                    if conversation:
                        conversations.append(conversation)
                
                total_found = data.get("total_count", len(page_conversations))
                
                if progress_callback:
                    await progress_callback(
                        f"Syncing: {len(conversations)}/{total_found} conversations"
                    )
                
                # Check if we got all results
                if len(page_conversations) < per_page:
                    break
                    
                page += 1
        
        duration = time.time() - start_time
        
        # Count new vs updated (simplified - in real implementation, 
        # this would check against database)
        stats = SyncStats(
            total_conversations=len(conversations),
            new_conversations=len(conversations),  # Simplified
            updated_conversations=0,  # Simplified
            total_messages=sum(len(conv.messages) for conv in conversations),
            duration_seconds=duration,
            api_calls_made=api_calls
        )
        
        logger.info(f"Incremental sync completed: {stats.total_conversations} conversations in {duration:.1f}s")
        return stats
    
    async def fetch_conversations_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        progress_callback: Optional[Callable] = None
    ) -> List[Conversation]:
        """Fetch all conversations created within a specific time period.
        
        Args:
            start_date: Start of time period
            end_date: End of time period
            progress_callback: Optional progress callback
            
        Returns:
            List of conversations in the period
        """
        conversations = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use updated_at to capture both new conversations AND existing conversations with new messages
            search_filters = [
                {
                    "field": "updated_at",
                    "operator": ">",
                    "value": int(start_date.timestamp())
                },
                {
                    "field": "updated_at",
                    "operator": "<", 
                    "value": int(end_date.timestamp())
                }
            ]
            
            query = {"operator": "AND", "value": search_filters}
            
            page = 1
            per_page = 150
            
            while True:
                await self._rate_limit()
                
                request_body = {
                    "query": query,
                    "pagination": {"per_page": per_page, "page": page},
                    "sort": {"field": "created_at", "order": "desc"}
                }
                
                response = await client.post(
                    f"{self.base_url}/conversations/search",
                    headers=self.headers,
                    json=request_body
                )
                response.raise_for_status()
                
                data = response.json()
                page_conversations = data.get("conversations", [])
                
                if not page_conversations:
                    break
                
                for conv_data in page_conversations:
                    conversation = self._parse_conversation_from_search(conv_data)
                    if conversation:
                        conversations.append(conversation)
                
                if progress_callback:
                    total_found = data.get("total_count", len(conversations))
                    await progress_callback(
                        f"Fetching: {len(conversations)}/{total_found} conversations"
                    )
                
                if len(page_conversations) < per_page:
                    break
                    
                page += 1
        
        logger.info(f"Fetched {len(conversations)} conversations for period {start_date} to {end_date}")
        return conversations
    
    def _parse_conversation_from_search(self, conv_data: dict) -> Optional[Conversation]:
        """Parse a conversation from Intercom Search API response."""
        try:
            # Parse messages from conversation_parts
            messages = []
            has_customer_message = False
            
            conversation_parts = conv_data.get("conversation_parts", {})
            if isinstance(conversation_parts, dict):
                parts_list = conversation_parts.get("conversation_parts", [])
            else:
                parts_list = []
            
            for part in parts_list:
                if not isinstance(part, dict):
                    continue
                    
                if part.get("part_type") in ["comment", "note", "message"]:
                    if not part.get("body"):
                        continue
                    
                    author_type = (
                        "admin" if part.get("author", {}).get("type") == "admin" 
                        else "user"
                    )
                    
                    if author_type == "user":
                        has_customer_message = True
                    
                    message = Message(
                        id=str(part.get("id", "unknown")),
                        author_type=author_type,
                        body=part.get("body", ""),
                        created_at=datetime.fromtimestamp(part.get("created_at", 0), tz=timezone.utc),
                        part_type=part.get("part_type")
                    )
                    messages.append(message)
            
            # Add initial message from source
            if conv_data.get("source", {}).get("body"):
                initial_message = Message(
                    id=conv_data["id"] + "_initial",
                    author_type="user",
                    body=conv_data["source"]["body"],
                    created_at=datetime.fromtimestamp(conv_data["created_at"], tz=timezone.utc),
                    part_type="initial"
                )
                messages.insert(0, initial_message)
                has_customer_message = True
            
            # Skip admin-only conversations
            if not has_customer_message:
                return None
            
            # Get customer email
            customer_email = None
            source = conv_data.get("source", {})
            if isinstance(source, dict):
                author = source.get("author", {})
                if isinstance(author, dict):
                    customer_email = author.get("email")
            
            # Parse tags
            tags = []
            tags_data = conv_data.get("tags", {})
            if isinstance(tags_data, dict):
                tags_list = tags_data.get("tags", [])
                for tag in tags_list:
                    if isinstance(tag, dict):
                        tags.append(tag.get("name", str(tag)))
                    else:
                        tags.append(str(tag))
            
            # Get updated_at - use created_at as fallback
            updated_at = conv_data.get("updated_at", conv_data.get("created_at", 0))
            
            return Conversation(
                id=conv_data["id"],
                created_at=datetime.fromtimestamp(conv_data["created_at"], tz=timezone.utc),
                updated_at=datetime.fromtimestamp(updated_at, tz=timezone.utc),
                messages=messages,
                customer_email=customer_email,
                tags=tags
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse conversation {conv_data.get('id', 'unknown')}: {e}")
            return None
    
    async def fetch_individual_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Fetch a complete conversation thread with all messages.
        
        Args:
            conversation_id: The Intercom conversation ID
            
        Returns:
            Complete conversation with all messages, or None if not found
        """
        try:
            # Use optimized request with caching
            cache_key = f"conversation_{conversation_id}"
            conv_data = await self._make_optimized_request(
                "GET",
                f"{self.base_url}/conversations/{conversation_id}",
                cache_key=cache_key,
                cache_ttl=300,  # Cache individual conversations for 5 minutes
                priority="high"
            )
            
            return self._parse_individual_conversation(conv_data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Conversation {conversation_id} not found")
                return None
            logger.error(f"Failed to fetch conversation {conversation_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch conversation {conversation_id}: {e}")
            return None
    
    async def fetch_individual_conversations(self, conversation_ids: List[str], 
                                           progress_callback: Optional[Callable] = None) -> List[Conversation]:
        """Fetch multiple complete conversation threads.
        
        Args:
            conversation_ids: List of conversation IDs to fetch
            progress_callback: Optional progress callback
            
        Returns:
            List of complete conversations
        """
        conversations = []
        
        for i, conv_id in enumerate(conversation_ids):
            conversation = await self.fetch_individual_conversation(conv_id)
            if conversation:
                conversations.append(conversation)
            
            if progress_callback:
                await progress_callback(
                    f"Fetching complete threads: {i+1}/{len(conversation_ids)}"
                )
        
        logger.info(f"Fetched {len(conversations)} complete conversation threads")
        return conversations
    
    def _parse_individual_conversation(self, conv_data: dict) -> Optional[Conversation]:
        """Parse a conversation from individual conversation API response."""
        try:
            # Parse messages from conversation_parts
            messages = []
            has_customer_message = False
            
            # Get conversation parts (messages)
            conversation_parts = conv_data.get("conversation_parts", {})
            if isinstance(conversation_parts, dict):
                parts_list = conversation_parts.get("conversation_parts", [])
            else:
                parts_list = conversation_parts or []
            
            for part in parts_list:
                if not isinstance(part, dict):
                    continue
                    
                if part.get("part_type") in ["comment", "note", "message"]:
                    if not part.get("body"):
                        continue
                    
                    author_type = (
                        "admin" if part.get("author", {}).get("type") == "admin" 
                        else "user"
                    )
                    
                    if author_type == "user":
                        has_customer_message = True
                    
                    message = Message(
                        id=str(part.get("id", "unknown")),
                        author_type=author_type,
                        body=part.get("body", ""),
                        created_at=datetime.fromtimestamp(part.get("created_at", 0), tz=timezone.utc),
                        part_type=part.get("part_type")
                    )
                    messages.append(message)
            
            # Add initial message from source if exists
            source = conv_data.get("source", {})
            if isinstance(source, dict) and source.get("body"):
                initial_message = Message(
                    id=conv_data["id"] + "_initial",
                    author_type="user",
                    body=source["body"],
                    created_at=datetime.fromtimestamp(conv_data["created_at"], tz=timezone.utc),
                    part_type="initial"
                )
                messages.insert(0, initial_message)
                has_customer_message = True
            
            # Skip admin-only conversations
            if not has_customer_message:
                return None
            
            # Sort messages by creation time to ensure proper ordering
            messages.sort(key=lambda msg: msg.created_at)
            
            # Deduplicate messages by ID
            seen_ids = set()
            deduplicated_messages = []
            for msg in messages:
                if msg.id not in seen_ids:
                    deduplicated_messages.append(msg)
                    seen_ids.add(msg.id)
            
            # Get customer email
            customer_email = None
            if isinstance(source, dict):
                author = source.get("author", {})
                if isinstance(author, dict):
                    customer_email = author.get("email")
            
            # Parse tags
            tags = []
            tags_data = conv_data.get("tags", {})
            if isinstance(tags_data, dict):
                tags_list = tags_data.get("tags", [])
                for tag in tags_list:
                    if isinstance(tag, dict):
                        tags.append(tag.get("name", str(tag)))
                    else:
                        tags.append(str(tag))
            
            # Get updated_at - use created_at as fallback
            updated_at = conv_data.get("updated_at", conv_data.get("created_at", 0))
            
            return Conversation(
                id=conv_data["id"],
                created_at=datetime.fromtimestamp(conv_data["created_at"], tz=timezone.utc),
                updated_at=datetime.fromtimestamp(updated_at, tz=timezone.utc),
                messages=deduplicated_messages,
                customer_email=customer_email,
                tags=tags
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse individual conversation {conv_data.get('id', 'unknown')}: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test if the API connection is working."""
        try:
            # Use optimized request for connection test
            await self._make_optimized_request(
                "GET", f"{self.base_url}/me", 
                priority="high"
            )
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        rate_limit_stats = self.rate_limiter.get_stats()
        optimization_stats = self.optimizer.get_performance_stats()
        
        return {
            'rate_limiting': rate_limit_stats,
            'optimization': optimization_stats,
            'api_client': {
                'base_url': self.base_url,
                'app_id': self._app_id,
                'optimization_enabled': True,
                'adaptive_rate_limiting': True
            }
        }
    
    def get_recommendations(self) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []
        
        rate_limit_stats = self.rate_limiter.get_stats()
        optimization_stats = self.optimizer.get_performance_stats()
        
        # Add rate limiting recommendations
        if 'recommendations' in rate_limit_stats:
            recommendations.extend(rate_limit_stats['recommendations'])
        
        # Add optimization recommendations
        if 'recommendations' in optimization_stats:
            recommendations.extend(optimization_stats['recommendations'])
        
        # Add client-specific recommendations
        current_efficiency = rate_limit_stats.get('performance', {}).get('efficiency_percentage', 100)
        if current_efficiency < 70:
            recommendations.append("API efficiency is low - consider reducing concurrent requests")
        
        cache_hit_ratio = optimization_stats.get('performance', {}).get('cache_hit_ratio', 0)
        if cache_hit_ratio < 0.2:
            recommendations.append("Low cache usage - verify cache keys and TTL settings")
        
        return recommendations
    
    async def close(self):
        """Clean up client resources."""
        await self.optimizer.close()