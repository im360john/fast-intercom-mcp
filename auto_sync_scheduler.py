"""Auto-sync scheduler for daily syncs at 9pm PST."""
import asyncio
import logging
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo
from fast_intercom_mcp.db.connection import db_pool
from fast_intercom_mcp.tools.sync import sync_conversations, sync_articles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_daily_sync():
    """Run the daily sync of conversations and articles."""
    logger.info(f"Starting daily sync at {datetime.now()}")
    
    await db_pool.initialize()
    
    try:
        # Sync last 7 days of conversations
        logger.info("Syncing conversations...")
        conv_result = await sync_conversations(days=7, force=True)
        logger.info(f"Conversation sync result: {conv_result}")
        
        # Sync all articles
        logger.info("Syncing articles...")
        article_result = await sync_articles(force=True)
        logger.info(f"Article sync result: {article_result}")
        
        logger.info("Daily sync completed successfully")
        
    except Exception as e:
        logger.error(f"Daily sync failed: {e}")
    finally:
        await db_pool.close()

async def calculate_next_run_time():
    """Calculate the next 9 PM PST."""
    pst = ZoneInfo('America/Los_Angeles')
    now = datetime.now(pst)
    
    # Set target time to 9 PM PST
    target_time = time(21, 0, 0)  # 9 PM
    
    # Get today's 9 PM PST
    next_run = now.replace(hour=target_time.hour, minute=target_time.minute, second=0, microsecond=0)
    
    # If it's already past 9 PM today, schedule for tomorrow
    if now >= next_run:
        next_run += timedelta(days=1)
    
    return next_run

async def schedule_daily_sync():
    """Schedule daily sync at 9 PM PST."""
    while True:
        try:
            # Calculate time until next 9 PM PST
            next_run = await calculate_next_run_time()
            wait_seconds = (next_run - datetime.now(ZoneInfo('America/Los_Angeles'))).total_seconds()
            
            logger.info(f"Next sync scheduled for: {next_run}")
            logger.info(f"Waiting {wait_seconds/3600:.1f} hours...")
            
            # Wait until the scheduled time
            await asyncio.sleep(wait_seconds)
            
            # Run the sync
            await run_daily_sync()
            
            # Wait a bit before calculating next run to avoid double-runs
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            # Wait 5 minutes before retrying
            await asyncio.sleep(300)

def main():
    """Main entry point for the scheduler."""
    logger.info("Starting Fast-Intercom-MCP Auto-Sync Scheduler")
    logger.info("Daily sync scheduled for 9 PM PST")
    
    try:
        asyncio.run(schedule_daily_sync())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler crashed: {e}")

if __name__ == "__main__":
    main()