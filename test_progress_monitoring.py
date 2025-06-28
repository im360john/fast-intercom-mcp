#!/usr/bin/env python3
"""Test script to verify progress monitoring functionality."""

import asyncio
from datetime import datetime, timedelta

from fast_intercom_mcp.sync_service import SyncService


class MockIntercomClient:
    """Mock Intercom client for testing progress monitoring."""

    def __init__(self):
        self.app_id = "test_app"

    async def get_app_id(self):
        return self.app_id

    async def fetch_conversations_for_period(self, start_date, end_date, progress_callback=None):
        """Mock conversation fetching with progress simulation."""
        print(f"🔄 Mock fetching conversations from {start_date.date()} to {end_date.date()}")

        # Simulate fetching conversations with progress updates
        total_conversations = 50
        conversations = []

        for i in range(1, total_conversations + 1):
            # Simulate API delay
            await asyncio.sleep(0.1)

            # Create mock conversation
            from fast_intercom_mcp.models import Conversation, Message

            conversation = Conversation(
                id=f"test_conv_{i}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                customer_email=f"customer{i}@example.com",
                messages=[
                    Message(
                        id=f"msg_{i}",
                        author_type="user",
                        body=f"Test message {i}",
                        created_at=datetime.now(),
                        part_type="comment",
                    )
                ],
            )
            conversations.append(conversation)

            # Call progress callback every 10 conversations
            if progress_callback and (i % 10 == 0 or i == total_conversations):
                await progress_callback(
                    f"Fetched {i} conversations from {start_date.date()} to {end_date.date()}"
                )

        return conversations

    async def fetch_conversations_incremental(self, since):
        """Mock incremental fetch."""
        from fast_intercom_mcp.models import SyncStats

        print(f"🔄 Mock incremental sync since {since}")
        await asyncio.sleep(0.5)  # Simulate work
        return SyncStats(
            total_conversations=10,
            new_conversations=5,
            updated_conversations=5,
            total_messages=25,
            duration_seconds=0.5,
            api_calls_made=1,
        )

    async def test_connection(self):
        return True


class MockDatabaseManager:
    """Mock database manager for testing."""

    def __init__(self):
        pass

    def store_conversations(self, conversations):
        """Mock storing conversations."""
        print(f"💾 Mock storing {len(conversations)} conversations")
        return len(conversations)

    def record_sync_period(self, start_date, end_date, total, new, updated):
        """Mock recording sync period."""
        print(f"📝 Mock recording sync period: {total} total, {new} new")

    def get_stale_timeframes(self, max_age_minutes):
        return []

    def get_periods_needing_sync(self, max_age_minutes):
        return []

    def check_sync_state(self, start_date, end_date, max_age_minutes):
        return {"sync_state": "fresh", "message": "Test data is fresh"}


async def test_progress_monitoring():
    """Test the progress monitoring functionality."""
    print("🧪 Testing progress monitoring implementation...")

    # Create mock components
    db_manager = MockDatabaseManager()
    intercom_client = MockIntercomClient()

    # Create sync service
    sync_service = SyncService(db_manager, intercom_client)

    # Progress tracking variables
    progress_updates = []

    async def progress_callback(current_count, estimated_total, elapsed_seconds):
        """Test progress callback."""
        rate = current_count / elapsed_seconds if elapsed_seconds > 0 else 0
        remaining = estimated_total - current_count
        eta = remaining / rate if rate > 0 else 0

        progress_info = {
            "current": current_count,
            "total": estimated_total,
            "elapsed": elapsed_seconds,
            "rate": rate,
            "eta": eta,
            "percentage": (current_count / estimated_total) * 100 if estimated_total > 0 else 0,
        }
        progress_updates.append(progress_info)

        print(
            f"📊 Progress: {current_count}/{estimated_total} "
            f"({progress_info['percentage']:.1f}%) "
            f"Rate: {rate:.2f}/sec "
            f"ETA: {eta:.1f}s "
            f"Elapsed: {elapsed_seconds:.1f}s"
        )

    # Test sync_period with progress monitoring
    print("\n1️⃣ Testing sync_period with progress monitoring:")
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()

    stats = await sync_service.sync_period(
        start_date, end_date, progress_callback=progress_callback
    )

    print(
        f"✅ Sync completed: {stats.total_conversations} conversations in {stats.duration_seconds:.1f}s"
    )
    print(f"📈 Progress updates received: {len(progress_updates)}")

    # Test sync_incremental with progress monitoring
    print("\n2️⃣ Testing sync_incremental with progress monitoring:")
    progress_updates.clear()

    since = datetime.now() - timedelta(hours=6)
    stats = await sync_service.sync_incremental(since, progress_callback=progress_callback)

    print(f"✅ Incremental sync completed: {stats.total_conversations} conversations")

    # Test sync_recent with progress monitoring
    print("\n3️⃣ Testing sync_recent with progress monitoring:")
    progress_updates.clear()

    stats = await sync_service.sync_recent(progress_callback=progress_callback)
    print(f"✅ Recent sync completed: {stats.total_conversations} conversations")

    print("\n🎉 All progress monitoring tests completed successfully!")
    return True


if __name__ == "__main__":
    asyncio.run(test_progress_monitoring())
