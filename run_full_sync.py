"""Run a full sync of conversations and articles."""
import asyncio
from datetime import datetime
from fast_intercom_mcp.db.connection import db_pool
from fast_intercom_mcp.tools.sync import sync_conversations, sync_articles, get_sync_status

async def run_full_sync():
    """Run a comprehensive sync of all data."""
    print(f"🔄 Starting Full Sync at {datetime.now()}")
    print("=" * 60)
    
    # Initialize database pool
    await db_pool.initialize()
    
    try:
        # Get initial status
        print("\n📊 Initial Database Status:")
        status = await get_sync_status()
        print(f"  - Conversations: {status['database_counts']['conversations']}")
        print(f"  - Articles: {status['database_counts']['articles']}")
        
        # Sync conversations from last 30 days
        print("\n1️⃣ Syncing Conversations (Last 30 Days)...")
        print("-" * 40)
        conv_result = await sync_conversations(days=30, force=True)
        
        if 'error' in conv_result:
            print(f"❌ Conversation sync failed: {conv_result['error']}")
        else:
            print(f"✅ Conversation sync completed!")
            print(f"   - Status: {conv_result['status']}")
            print(f"   - Conversations synced: {conv_result['conversations_synced']}")
            print(f"   - Duration: {conv_result['sync_duration_days']} days")
        
        # Sync all articles
        print("\n2️⃣ Syncing All Articles...")
        print("-" * 40)
        article_result = await sync_articles(force=True)
        
        if 'error' in article_result:
            print(f"❌ Article sync failed: {article_result['error']}")
        else:
            print(f"✅ Article sync completed!")
            print(f"   - Status: {article_result['status']}")
            print(f"   - Articles synced: {article_result['articles_synced']}")
        
        # Get final status
        print("\n📊 Final Database Status:")
        final_status = await get_sync_status()
        print(f"  - Conversations: {final_status['database_counts']['conversations']}")
        print(f"  - Articles: {final_status['database_counts']['articles']}")
        
        # Show sync metadata
        print("\n📅 Sync Metadata:")
        for entity_type, info in final_status['sync_statuses'].items():
            print(f"\n{entity_type.title()}:")
            print(f"  - Status: {info['status']}")
            print(f"  - Last sync: {info['last_sync']}")
            print(f"  - Items synced: {info['items_synced']}")
            
        print("\n" + "=" * 60)
        print(f"✅ Full sync completed at {datetime.now()}")
        
    finally:
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(run_full_sync())