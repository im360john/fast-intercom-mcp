"""Test API endpoints only."""
import asyncio
import httpx

async def test_api_endpoints(base_url: str):
    """Test the API endpoints via HTTP"""
    print(f"🌐 Testing API Endpoints: {base_url}")
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
                if results.get('data'):
                    print(f"First result customer: {results['data'][0].get('customer_email', 'No email')}")
            else:
                print(f"Conversation search failed: {response.status_code} - {response.text}")
            
            # Test 5: Search articles - FIXED parameter format
            print("\n5️⃣ Testing article search endpoint...")
            response = await client.post(f"{base_url}/mcp/articles/search", 
                                       json={"query": "integration", "limit": 3})
            if response.status_code == 200:
                results = response.json()
                print(f"Article search: {len(results.get('data', []))} results")
                if results.get('data'):
                    print(f"First article: {results['data'][0].get('title', 'No title')}")
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
    """Run API tests"""
    print("🚀 Testing Deployed MCP API Endpoints")
    await test_api_endpoints("https://fast-intercom-mcp.onrender.com")

if __name__ == "__main__":
    asyncio.run(main())