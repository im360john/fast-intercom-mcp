"""Test MCP functionality via API endpoints."""
import asyncio
import httpx
from fast_intercom_mcp.tools import conversations, articles, sync

async def test_local_tools():
    """Test the tools directly (not via HTTP)"""
    print("🧪 Testing MCP Tools Locally")
    print("=" * 50)
    
    try:
        # Test 1: Get sync status
        print("\n1️⃣ Testing sync status...")
        status = await sync.get_sync_status()
        print(f"Sync status: {status}")
        
        # Test 2: Search conversations 
        print("\n2️⃣ Testing conversation search...")
        conv_result = await conversations.search_conversations(query="API", limit=3)
        print(f"Conversation search results: {len(conv_result.get('data', []))} conversations found")
        
        # Test 3: Search articles
        print("\n3️⃣ Testing article search...")
        article_result = await articles.search_articles(query="integration", limit=3)
        print(f"Article search results: {len(article_result.get('data', []))} articles found")
        
        print("\n✅ All local tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Local test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_endpoints(base_url: str):
    """Test the API endpoints via HTTP"""
    print(f"\n🌐 Testing API Endpoints: {base_url}")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Health check
            print("\n1️⃣ Testing health endpoint...")
            response = await client.get(f"{base_url}/health")
            print(f"Health check: {response.status_code} - {response.json()}")
            
            # Test 2: Database stats
            print("\n2️⃣ Testing database stats...")
            response = await client.get(f"{base_url}/mcp/database/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"Database stats: {stats}")
            else:
                print(f"Database stats failed: {response.status_code}")
            
            # Test 3: Sync status
            print("\n3️⃣ Testing sync status endpoint...")
            response = await client.get(f"{base_url}/mcp/sync/status")
            if response.status_code == 200:
                sync_status = response.json()
                print(f"Sync status: {sync_status}")
            else:
                print(f"Sync status failed: {response.status_code}")
            
            # Test 4: Search conversations
            print("\n4️⃣ Testing conversation search endpoint...")
            response = await client.post(f"{base_url}/mcp/conversations/search", 
                                       json={"query": "API", "limit": 3})
            if response.status_code == 200:
                results = response.json()
                print(f"Conversation search: {len(results.get('data', []))} results")
            else:
                print(f"Conversation search failed: {response.status_code} - {response.text}")
            
            # Test 5: Search articles
            print("\n5️⃣ Testing article search endpoint...")
            response = await client.post(f"{base_url}/mcp/articles/search", 
                                       json={"query": "integration", "limit": 3})
            if response.status_code == 200:
                results = response.json()
                print(f"Article search: {len(results.get('data', []))} results")
            else:
                print(f"Article search failed: {response.status_code} - {response.text}")
            
            print("\n✅ All API tests completed!")
            return True
            
        except Exception as e:
            print(f"❌ API test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Run all tests"""
    print("🚀 Starting MCP Functionality Tests")
    
    # Test local tools first
    local_success = await test_local_tools()
    
    if local_success:
        # Test deployed API
        await test_api_endpoints("https://fast-intercom-mcp.onrender.com")
    else:
        print("❌ Skipping API tests due to local test failures")

if __name__ == "__main__":
    asyncio.run(main())