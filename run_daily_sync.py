"""Run daily sync for Render Cron Jobs."""
import asyncio
import sys
from datetime import datetime, timedelta
from fast_intercom_mcp.db.connection import db_pool
from fast_intercom_mcp.api.client import IntercomAPIClient
from fast_intercom_mcp.config import Config

# Import the sync with contacts logic
from sync_with_contacts import sync_conversations_with_contacts
from fast_intercom_mcp.tools.sync import sync_articles

async def run_daily_sync():
    """Run the daily sync process."""
    print(f"🚀 Starting daily sync at {datetime.now()}")
    print("=" * 60)
    
    try:
        # Initialize database
        await db_pool.initialize()
        
        # Sync conversations with contact details
        print("\n📬 Syncing conversations...")
        await sync_conversations_with_contacts()
        
        # Sync articles
        print("\n📄 Syncing articles...")
        result = await sync_articles(force=True)
        print(f"Article sync result: {result}")
        
        # Get final statistics
        async with db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    (SELECT COUNT(*) FROM conversations) as conv_count,
                    (SELECT COUNT(*) FROM conversations WHERE customer_email IS NOT NULL) as conv_with_email,
                    (SELECT COUNT(*) FROM articles) as article_count,
                    (SELECT COUNT(*) FROM articles WHERE state = 'published') as published_articles
            """)
            
            print("\n📊 Final Statistics:")
            print(f"  - Total conversations: {stats['conv_count']}")
            print(f"  - Conversations with email: {stats['conv_with_email']} ({stats['conv_with_email']/stats['conv_count']*100:.1f}%)")
            print(f"  - Total articles: {stats['article_count']}")
            print(f"  - Published articles: {stats['published_articles']}")
        
        print(f"\n✅ Daily sync completed successfully at {datetime.now()}")
        return 0
        
    except Exception as e:
        print(f"\n❌ Daily sync failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await db_pool.close()

if __name__ == "__main__":
    exit_code = asyncio.run(run_daily_sync())
    sys.exit(exit_code)