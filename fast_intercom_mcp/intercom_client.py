"""Intercom API client with intelligent sync capabilities."""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Callable, Tuple
import logging

import httpx

from .models import Conversation, Message, ConversationFilters, SyncStats


logger = logging.getLogger(__name__)


class IntercomClient:
    """Intercom API client with smart sync and rate limiting."""
    
    def __init__(self, access_token: str, timeout: int = 300):
        self.access_token = access_token
        self.timeout = timeout
        self.base_url = "https://api.intercom.io"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._app_id = None
        
        # Rate limiting: Intercom allows ~83 requests per 10 seconds
        self._request_times = []
        self._max_requests_per_window = 80  # Be conservative 
        self._window_seconds = 10
    
    async def get_app_id(self) -> Optional[str]:
        """Get the Intercom app ID for generating conversation URLs."""
        if self._app_id:
            return self._app_id
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/me", headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("app") and data["app"].get("id_code"):
                        self._app_id = str(data["app"]["id_code"])
                        logger.info(f"Retrieved app ID: {self._app_id}")
                        return self._app_id
        except Exception as e:
            logger.warning(f"Failed to get app ID: {e}")
        
        return None
    
    async def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        now = time.time()
        
        # Remove old requests outside the window
        self._request_times = [t for t in self._request_times if now - t < self._window_seconds]
        
        # If we're at the limit, wait
        if len(self._request_times) >= self._max_requests_per_window:
            sleep_time = self._window_seconds - (now - self._request_times[0]) + 0.1
            if sleep_time > 0:
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
        
        # Record this request
        self._request_times.append(now)
    
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
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                await self._rate_limit()
                
                request_body = {
                    "query": query,
                    "pagination": {"per_page": per_page, "page": page},
                    "sort": {"field": "updated_at", "order": "desc"}
                }
                
                logger.debug(f"Fetching incremental page {page}")
                
                response = await client.post(
                    f"{self.base_url}/conversations/search",
                    headers=self.headers,
                    json=request_body
                )
                response.raise_for_status()
                api_calls += 1
                
                data = response.json()
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
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
    
    async def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Fetch a complete conversation by ID with all messages.
        
        Args:
            conversation_id: The Intercom conversation ID
            
        Returns:
            Complete conversation with all messages, or None if not found
        """
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}",
                    headers=self.headers
                )
                
                if response.status_code == 404:
                    logger.warning(f"Conversation {conversation_id} not found")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                return self._parse_conversation_from_api(data)
                
        except Exception as e:
            logger.error(f"Failed to fetch conversation {conversation_id}: {e}")
            return None
    
    async def get_conversation_messages(
        self, 
        conversation_id: str, 
        per_page: int = 20,
        starting_after: Optional[str] = None
    ) -> Tuple[List[Message], Optional[str]]:
        """Fetch messages for a conversation with pagination.
        
        Args:
            conversation_id: The Intercom conversation ID
            per_page: Number of messages per page (max 50)
            starting_after: Cursor for pagination
            
        Returns:
            Tuple of (messages, next_cursor) where next_cursor is None if no more pages
        """
        await self._rate_limit()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"per_page": min(per_page, 50)}
                if starting_after:
                    params["starting_after"] = starting_after
                
                response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}/conversation_parts",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 404:
                    logger.warning(f"Conversation {conversation_id} not found")
                    return [], None
                
                response.raise_for_status()
                data = response.json()
                
                messages = []
                conversation_parts = data.get("conversation_parts", [])
                
                for part in conversation_parts:
                    message = self._parse_message_from_part(part)
                    if message:
                        messages.append(message)
                
                # Get next cursor for pagination
                pages = data.get("pages", {})
                next_cursor = pages.get("next", {}).get("starting_after") if pages.get("next") else None
                
                return messages, next_cursor
                
        except Exception as e:
            logger.error(f"Failed to fetch messages for conversation {conversation_id}: {e}")
            return [], None
    
    async def fetch_complete_conversation_thread(self, conversation_id: str) -> Optional[Conversation]:
        """Fetch a complete conversation with all messages using pagination.
        
        Args:
            conversation_id: The Intercom conversation ID
            
        Returns:
            Complete conversation with all messages
        """
        # First get conversation metadata
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            return None
        
        # Then fetch all messages using pagination
        all_messages = []
        next_cursor = None
        
        while True:
            messages, next_cursor = await self.get_conversation_messages(
                conversation_id, 
                per_page=50, 
                starting_after=next_cursor
            )
            
            all_messages.extend(messages)
            
            if not next_cursor:
                break
        
        # Update conversation with complete message list
        conversation.messages = sorted(all_messages, key=lambda m: m.created_at)
        return conversation
    
    def _parse_conversation_from_api(self, conv_data: dict) -> Optional[Conversation]:
        """Parse a conversation from Intercom Conversation API response."""
        try:
            # Parse customer email
            customer_email = None
            contacts = conv_data.get("contacts", {})
            if isinstance(contacts, dict) and contacts.get("contacts"):
                contact = contacts["contacts"][0]
                customer_email = contact.get("email")
            
            # Parse tags
            tags = []
            tags_data = conv_data.get("tags", {})
            if isinstance(tags_data, dict) and tags_data.get("tags"):
                for tag in tags_data["tags"]:
                    if isinstance(tag, dict):
                        tags.append(tag.get("name", str(tag)))
                    else:
                        tags.append(str(tag))
            
            # Parse initial conversation parts for messages
            messages = []
            conversation_parts = conv_data.get("conversation_parts", {})
            if isinstance(conversation_parts, dict):
                parts_list = conversation_parts.get("conversation_parts", [])
                for part in parts_list:
                    message = self._parse_message_from_part(part)
                    if message:
                        messages.append(message)
            
            return Conversation(
                id=conv_data["id"],
                created_at=datetime.fromtimestamp(conv_data["created_at"], tz=timezone.utc),
                updated_at=datetime.fromtimestamp(conv_data.get("updated_at", conv_data["created_at"]), tz=timezone.utc),
                messages=messages,
                customer_email=customer_email,
                tags=tags
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse conversation {conv_data.get('id', 'unknown')}: {e}")
            return None
    
    def _parse_message_from_part(self, part: dict) -> Optional[Message]:
        """Parse a message from a conversation part."""
        try:
            if not isinstance(part, dict):
                return None
            
            # Only process actual message parts
            if part.get("part_type") not in ["comment", "note", "message"]:
                return None
            
            if not part.get("body"):
                return None
            
            author_type = (
                "admin" if part.get("author", {}).get("type") == "admin" 
                else "user"
            )
            
            return Message(
                id=str(part.get("id", "unknown")),
                author_type=author_type,
                body=part.get("body", ""),
                created_at=datetime.fromtimestamp(part.get("created_at", 0), tz=timezone.utc),
                part_type=part.get("part_type")
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse message part: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test if the API connection is working."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/me", headers=self.headers)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False