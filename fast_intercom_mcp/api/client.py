"""Rate-limited Intercom API client."""
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