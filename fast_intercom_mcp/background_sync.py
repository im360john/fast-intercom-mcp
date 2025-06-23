"""Background sync service that runs inside the MCP server process."""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class BackgroundSyncService:
    """Background sync service that runs inside the MCP server process."""
    
    def __init__(self, db_manager, intercom_client, sync_interval_minutes: int = 15):
        self.db = db_manager
        self.intercom_client = intercom_client
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.running = False
        self.sync_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background sync service."""
        if self.running:
            return
        
        self.running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
        logger.info(f"Background sync started with {self.sync_interval.total_seconds()/60} minute interval")
    
    async def stop(self):
        """Stop the background sync service."""
        self.running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Background sync stopped")
    
    async def _sync_loop(self):
        """Main sync loop - runs continuously."""
        # Initial sync on startup
        await self._perform_sync()
        
        while self.running:
            try:
                await asyncio.sleep(self.sync_interval.total_seconds())
                if self.running:  # Check again after sleep
                    await self._perform_sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                # Continue running, retry in next interval
    
    async def _perform_sync(self):
        """Perform a single sync operation with metadata tracking."""
        start_time = datetime.now()
        
        # Default to syncing last 7 days
        end_date = start_time
        start_date = end_date - timedelta(days=7)
        
        # Start sync - write metadata
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sync_metadata 
                (sync_started_at, sync_status, sync_type, coverage_start_date, coverage_end_date)
                VALUES (?, 'in_progress', 'background', ?, ?)
            """, [start_time.isoformat(), start_date.date().isoformat(), end_date.date().isoformat()])
            sync_id = cursor.lastrowid
            conn.commit()
        
        try:
            logger.info(f"Starting background sync for {start_date.date()} to {end_date.date()}")
            
            # Use existing sync service method
            from .sync_service import SyncService
            sync_service = SyncService(self.db, self.intercom_client)
            stats = await sync_service.sync_period(start_date, end_date, is_background=True)
            
            total_convos = stats.total_conversations
            total_msgs = stats.total_messages
            
            # Update metadata on success
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("""
                    UPDATE sync_metadata 
                    SET sync_completed_at = ?,
                        sync_status = 'completed',
                        total_conversations = ?,
                        total_messages = ?
                    WHERE id = ?
                """, [datetime.now().isoformat(), total_convos, total_msgs, sync_id])
                conn.commit()
            
            logger.info(f"Background sync completed: {total_convos} conversations, {total_msgs} messages")
            
        except Exception as e:
            logger.error(f"Background sync failed: {e}")
            
            # Update metadata on failure
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("""
                    UPDATE sync_metadata 
                    SET sync_completed_at = ?,
                        sync_status = 'failed',
                        error_message = ?
                    WHERE id = ?
                """, [datetime.now().isoformat(), str(e), sync_id])
                conn.commit()
    
    async def force_sync(self) -> bool:
        """Force an immediate sync (callable from MCP tools)."""
        try:
            await self._perform_sync()
            return True
        except Exception as e:
            logger.error(f"Force sync failed: {e}")
            return False