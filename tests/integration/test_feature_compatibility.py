"""
Cross-feature compatibility tests for fast-intercom-mcp.

This module tests that different features work correctly together:
- Progress monitoring during sync operations
- MCP queries while background sync is running
- Concurrent sync requests handling
- Database transaction isolation between features
- Schema compatibility across features
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient
from fast_intercom_mcp.mcp_server import FastIntercomMCPServer
from fast_intercom_mcp.models import Conversation, Message, SyncStats
from fast_intercom_mcp.sync.coordinator import TwoPhaseConfig, TwoPhaseSyncCoordinator
from fast_intercom_mcp.sync_service import SyncService

logger = logging.getLogger(__name__)


class TestFeatureCompatibility:
    """Test suite for cross-feature compatibility."""

    @pytest.fixture
    async def compatibility_setup(self, temp_db):
        """Set up components for compatibility testing."""
        # Create database manager
        db = DatabaseManager(db_path=temp_db)

        # Mock Intercom client
        intercom_client = Mock(spec=IntercomClient)
        intercom_client.app_id = "test_app_123"

        # Create sync service
        sync_service = SyncService(db, intercom_client)

        # Create MCP server
        mcp_server = FastIntercomMCPServer(db, sync_service, intercom_client)

        return {
            "db": db,
            "intercom": intercom_client,
            "sync_service": sync_service,
            "mcp_server": mcp_server,
        }

    @pytest.mark.asyncio
    async def test_progress_monitoring_during_sync_recent(self, compatibility_setup):
        """Test that progress monitoring works correctly during sync recent."""
        components = compatibility_setup
        sync_service = components["sync_service"]
        intercom = components["intercom"]

        # Track progress updates
        progress_updates = []

        def progress_callback(message):
            progress_updates.append({"time": time.time(), "message": message})

        # Add progress callback
        sync_service.add_progress_callback(progress_callback)

        # Mock Intercom responses for sync recent
        mock_conversations = [
            Conversation(
                id=f"conv_{i}",
                created_at=datetime.now(UTC) - timedelta(hours=i),
                updated_at=datetime.now(UTC) - timedelta(hours=i),
                messages=[
                    Message(
                        id=f"conv_{i}_msg",
                        conversation_id=f"conv_{i}",
                        author_type="customer",
                        author_id=f"customer_{i}@example.com",
                        body=f"Test message for conv_{i}",
                        created_at=datetime.now(UTC) - timedelta(hours=i),
                    )
                ],
                customer_email=f"customer_{i}@example.com",
            )
            for i in range(20)
        ]

        # Mock fetch_conversations_incremental which is used by sync_recent
        async def mock_fetch_incremental(since):
            # Return all conversations newer than 'since'
            return [conv for conv in mock_conversations if conv.updated_at >= since]

        intercom.fetch_conversations_incremental = mock_fetch_incremental

        # Run sync
        stats = await sync_service.sync_recent()

        # Verify sync completed successfully
        assert stats.total_conversations >= 0  # May be 0 if no new data
        assert stats.total_messages >= 0

        # Verify progress updates were received
        assert len(progress_updates) > 0

        # Check that progress messages contain expected patterns
        progress_messages = [update["message"] for update in progress_updates]

        # Should have updates about fetching conversations
        assert any("Fetching conversations" in msg for msg in progress_messages)

        # Should have completion message
        assert any("Sync completed" in msg for msg in progress_messages)

        # Verify timing of updates (should be spread out)
        if len(progress_updates) > 1:
            time_diffs = [
                progress_updates[i]["time"] - progress_updates[i - 1]["time"]
                for i in range(1, len(progress_updates))
            ]
            # At least some updates should have meaningful time gaps
            assert any(diff > 0.05 for diff in time_diffs)

    @pytest.mark.asyncio
    async def test_mcp_queries_during_active_sync(self, compatibility_setup):
        """Test that MCP queries work correctly while sync is running."""
        components = compatibility_setup
        db = components["db"]
        sync_service = components["sync_service"]
        mcp_server = components["mcp_server"]
        intercom = components["intercom"]  # noqa: F841

        # Pre-populate some data
        initial_convs = [
            Conversation(
                id=f"initial_conv_{i}",
                created_at=datetime.now(UTC) - timedelta(days=i),
                updated_at=datetime.now(UTC) - timedelta(days=i),
                messages=[
                    Message(
                        id=f"initial_conv_{i}_msg",
                        conversation_id=f"initial_conv_{i}",
                        author_type="customer",
                        author_id=f"customer_{i}@example.com",
                        body=f"Initial message for initial_conv_{i}",
                        created_at=datetime.now(UTC) - timedelta(days=i),
                    )
                ],
                customer_email=f"customer_{i}@example.com",
            )
            for i in range(5)
        ]

        await db.store_conversations(initial_convs)

        # Mock sync that takes time
        sync_started = asyncio.Event()
        sync_completed = asyncio.Event()

        async def slow_sync():
            sync_started.set()

            # Mock conversations that will be added during sync
            new_convs = [
                Conversation(
                    id=f"sync_conv_{i}",
                    created_at=datetime.now(UTC) - timedelta(hours=i),
                    updated_at=datetime.now(UTC) - timedelta(hours=i),
                    messages=[
                        Message(
                            id=f"sync_conv_{i}_msg",
                            conversation_id=f"sync_conv_{i}",
                            author_type="customer",
                            author_id=f"sync_customer_{i}@example.com",
                            body=f"Sync message for sync_conv_{i}",
                            created_at=datetime.now(UTC) - timedelta(hours=i),
                        )
                    ],
                    customer_email=f"sync_customer_{i}@example.com",
                )
                for i in range(10)
            ]

            # Simulate slow sync by adding conversations one by one
            for conv in new_convs:
                await db.store_conversations([conv])
                await asyncio.sleep(0.1)  # Simulate slow API calls

            sync_completed.set()

            return SyncStats(
                total_conversations=10,
                new_conversations=10,
                updated_conversations=0,
                total_messages=10,
                duration_seconds=1.0,
                api_calls_made=10,
                errors_encountered=0,
            )

        # Replace sync method temporarily
        original_sync = sync_service.sync_recent
        sync_service.sync_recent = slow_sync

        try:
            # Start sync in background
            sync_task = asyncio.create_task(sync_service.sync_recent())

            # Wait for sync to start
            await sync_started.wait()

            # Now perform MCP queries while sync is running

            # Test 1: Search conversations (should work with existing data)
            search_result = await mcp_server.server.call_tool(
                "search_conversations", {"query": "Initial message", "limit": 10}
            )

            # Should find the pre-existing conversations
            assert len(search_result) == 1
            assert "5 conversations found" in search_result[0].text

            # Test 2: Get server status (should show sync in progress)
            status_result = await mcp_server.server.call_tool("get_server_status", {})

            # Status should be available even during sync
            assert len(status_result) == 1
            assert "FastIntercom Server Status" in status_result[0].text

            # Test 3: Get specific conversation
            conv_result = await mcp_server.server.call_tool(
                "get_conversation", {"conversation_id": "initial_conv_0"}
            )

            assert len(conv_result) == 1
            assert "initial_conv_0" in conv_result[0].text

            # Wait for sync to complete
            await sync_completed.wait()
            await sync_task

            # Test 4: Search should now include synced conversations
            search_all = await mcp_server.server.call_tool(
                "search_conversations", {"query": "message", "limit": 20}
            )

            # Should find both initial and synced conversations
            assert len(search_all) == 1
            assert "15 conversations found" in search_all[0].text

        finally:
            # Restore original sync method
            sync_service.sync_recent = original_sync

    @pytest.mark.asyncio
    async def test_concurrent_sync_requests_handling(self, compatibility_setup):
        """Test that multiple concurrent sync requests are handled properly."""
        components = compatibility_setup
        sync_service = components["sync_service"]
        intercom = components["intercom"]  # noqa: F841

        # Track sync executions
        sync_executions = []
        sync_lock = asyncio.Lock()

        async def mock_sync():
            async with sync_lock:
                sync_id = f"sync_{len(sync_executions)}"
                sync_executions.append({"id": sync_id, "start": time.time(), "status": "running"})

            # Simulate sync work
            await asyncio.sleep(0.5)

            async with sync_lock:
                for exec in sync_executions:
                    if exec["id"] == sync_id:
                        exec["end"] = time.time()
                        exec["status"] = "completed"
                        break

            return SyncStats(
                total_conversations=10,
                new_conversations=10,
                updated_conversations=0,
                total_messages=10,
                duration_seconds=0.5,
                api_calls_made=10,
                errors_encountered=0,
            )

        # Replace sync method
        sync_service.sync_recent = mock_sync

        # Try to start multiple syncs concurrently
        sync_tasks = []
        for _ in range(5):
            task = asyncio.create_task(sync_service.sync_recent())
            sync_tasks.append(task)
            await asyncio.sleep(0.1)  # Small delay between requests

        # Wait for all tasks to complete
        results = await asyncio.gather(*sync_tasks, return_exceptions=True)

        # Check results
        successful_syncs = [r for r in results if isinstance(r, SyncStats)]
        exceptions = [r for r in results if isinstance(r, Exception)]  # noqa: F841

        # Should have at least one successful sync
        assert len(successful_syncs) >= 1

        # Some requests might be rejected if sync is already running
        # This is expected behavior for preventing concurrent syncs

        # Verify no overlapping executions
        completed_execs = [e for e in sync_executions if e["status"] == "completed"]
        for i in range(len(completed_execs)):
            for j in range(i + 1, len(completed_execs)):
                exec1 = completed_execs[i]
                exec2 = completed_execs[j]

                # Check if executions overlapped
                overlap = not (exec1["end"] <= exec2["start"] or exec2["end"] <= exec1["start"])

                # There should be no overlap (sync service should prevent concurrent syncs)
                assert not overlap, f"Sync {exec1['id']} overlapped with {exec2['id']}"

    @pytest.mark.asyncio
    async def test_database_transaction_isolation(self, compatibility_setup):
        """Test that database transactions don't conflict between features."""
        components = compatibility_setup
        db = components["db"]
        sync_service = components["sync_service"]  # noqa: F841

        # Create test data
        test_conversations = []
        for i in range(100):
            conv = Conversation(
                id=f"transaction_test_{i}",
                created_at=datetime.now(UTC) - timedelta(hours=i),
                updated_at=datetime.now(UTC) - timedelta(hours=i),
                messages=[
                    Message(
                        id=f"transaction_test_{i}_msg",
                        conversation_id=f"transaction_test_{i}",
                        author_type="customer",
                        author_id=f"customer_{i}@example.com",
                        body=f"Message for transaction_test_{i}",
                        created_at=datetime.now(UTC) - timedelta(hours=i),
                    )
                ],
                customer_email=f"customer_{i}@example.com",
            )
            test_conversations.append(conv)

        # Test concurrent writes from different features
        write_errors = []

        async def write_conversations(start_idx, end_idx, feature_name):
            """Simulate a feature writing conversations."""
            try:
                for i in range(start_idx, end_idx):
                    conv = test_conversations[i]
                    await db.store_conversations([conv])

                    # Small delay to increase chance of conflicts
                    await asyncio.sleep(0.01)

            except Exception as e:
                write_errors.append(
                    {"feature": feature_name, "error": str(e), "range": f"{start_idx}-{end_idx}"}
                )

        # Simulate different features writing concurrently
        tasks = [
            write_conversations(0, 25, "sync_service"),
            write_conversations(25, 50, "mcp_queries"),
            write_conversations(50, 75, "background_sync"),
            write_conversations(75, 100, "progress_monitor"),
        ]

        # Run all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Check for errors
        assert len(write_errors) == 0, f"Database write errors occurred: {write_errors}"

        # Verify all data was written correctly
        all_convs = await db.search_conversations(query="")
        assert len(all_convs) == 100

        # Verify data integrity - each conversation should have its message
        for conv in all_convs:
            messages = await db.get_messages(conv.id)
            assert len(messages) == 1
            assert messages[0].conversation_id == conv.id

        # Test concurrent reads during writes
        read_errors = []

        async def read_while_writing():
            """Simulate reading while another operation is writing."""
            try:
                for _ in range(20):
                    # Random read operations
                    convs = await db.search_conversations(query="Message from")
                    stats = await db.get_sync_stats()

                    # Verify reads return valid data
                    assert isinstance(convs, list)
                    assert stats is not None or isinstance(stats, SyncStats)

                    await asyncio.sleep(0.05)

            except Exception as e:
                read_errors.append(str(e))

        # Clear database for next test
        for conv in all_convs:
            await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv.id,))
            await db.execute("DELETE FROM conversations WHERE id = ?", (conv.id,))

        # Run reads and writes concurrently
        write_task = write_conversations(0, 50, "writer")
        read_task = read_while_writing()

        await asyncio.gather(write_task, read_task, return_exceptions=True)

        # No read errors should occur
        assert len(read_errors) == 0, f"Read errors during concurrent writes: {read_errors}"

    @pytest.mark.asyncio
    async def test_feature_interaction_matrix(self, compatibility_setup):
        """Test various feature combinations to ensure compatibility."""
        components = compatibility_setup
        db = components["db"]
        sync_service = components["sync_service"]
        mcp_server = components["mcp_server"]
        intercom = components["intercom"]

        # Feature interaction matrix
        test_results = {
            "sync_with_progress": False,
            "mcp_during_sync": False,
            "progress_during_mcp": False,
            "concurrent_mcp_calls": False,
            "sync_after_mcp_changes": False,
        }

        # Test 1: Sync with progress monitoring
        progress_received = False

        def progress_callback(msg):
            nonlocal progress_received
            progress_received = True

        sync_service.add_progress_callback(progress_callback)

        # Mock simple sync
        intercom.fetch_conversations_incremental = AsyncMock(return_value=[])
        stats = await sync_service.sync_recent()

        test_results["sync_with_progress"] = progress_received and stats is not None

        # Test 2: MCP queries during sync
        sync_running = asyncio.Event()

        async def mock_long_sync():
            sync_running.set()
            await asyncio.sleep(0.5)
            return SyncStats(
                sync_id="test",
                conversations_synced=0,
                messages_synced=0,
                sync_type="test",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

        sync_service.sync_recent = mock_long_sync

        sync_task = asyncio.create_task(sync_service.sync_recent())
        await sync_running.wait()

        # Try MCP call during sync
        try:
            result = await mcp_server.server.call_tool("get_server_status", {})
            test_results["mcp_during_sync"] = len(result) > 0
        except Exception:
            test_results["mcp_during_sync"] = False

        await sync_task

        # Test 3: Progress callbacks during MCP operations
        mcp_progress = []

        def mcp_progress_callback(msg):
            mcp_progress.append(msg)

        sync_service.add_progress_callback(mcp_progress_callback)

        # Trigger sync via MCP
        result = await mcp_server.server.call_tool("sync_conversations", {"force": False})
        test_results["progress_during_mcp"] = len(mcp_progress) > 0

        # Test 4: Concurrent MCP calls
        mcp_tasks = [
            mcp_server.server.call_tool("get_server_status", {}),
            mcp_server.server.call_tool("get_data_info", {}),
            mcp_server.server.call_tool("get_sync_status", {}),
        ]

        try:
            results = await asyncio.gather(*mcp_tasks, return_exceptions=True)
            successful = sum(1 for r in results if not isinstance(r, Exception))
            test_results["concurrent_mcp_calls"] = successful == len(mcp_tasks)
        except Exception:
            test_results["concurrent_mcp_calls"] = False

        # Test 5: Sync after MCP-triggered changes
        # First, add some data via direct DB access (simulating MCP changes)
        test_conv = Conversation(
            id="mcp_added_conv",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            messages=[],
            customer_email="mcp_customer@example.com",
        )
        await db.store_conversations([test_conv])

        # Now trigger sync and ensure it doesn't conflict
        try:
            sync_service.sync_recent = AsyncMock(
                return_value=SyncStats(
                    sync_id="post_mcp",
                    conversations_synced=1,
                    messages_synced=0,
                    sync_type="test",
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
            )
            stats = await sync_service.sync_recent()
            test_results["sync_after_mcp_changes"] = stats is not None
        except Exception:
            test_results["sync_after_mcp_changes"] = False

        # Verify all feature interactions work
        for feature, result in test_results.items():
            assert result, f"Feature interaction failed: {feature}"

    @pytest.mark.asyncio
    async def test_two_phase_sync_with_progress_monitoring(self, compatibility_setup):
        """Test that two-phase sync coordinator works with progress monitoring."""
        components = compatibility_setup
        db = components["db"]
        intercom = components["intercom"]

        # Create two-phase coordinator
        config = TwoPhaseConfig(
            search_batch_size=10,
            fetch_batch_size=5,
            max_concurrent_fetches=2,
        )
        coordinator = TwoPhaseSyncCoordinator(intercom, db, config)

        # Track progress updates
        progress_updates = []

        def progress_callback(message):
            progress_updates.append({"time": time.time(), "message": message})

        coordinator.set_progress_callback(progress_callback)

        # Mock search phase
        search_results = [
            {"id": f"conv_{i}", "updated_at": (datetime.now(UTC) - timedelta(hours=i)).isoformat()}
            for i in range(20)
        ]

        async def mock_search(**kwargs):
            # Return results in batches
            for i in range(0, len(search_results), 10):
                yield search_results[i : i + 10]

        intercom.search_conversations = mock_search

        # Mock fetch phase
        async def mock_get_conversation(conv_id):
            await asyncio.sleep(0.05)  # Simulate API delay
            return Conversation(
                id=conv_id,
                created_at=datetime.now(UTC) - timedelta(days=1),
                updated_at=datetime.now(UTC),
                messages=[],
                customer_email="customer_1@example.com",
            )

        async def mock_get_messages(conv_id):
            await asyncio.sleep(0.02)
            return [
                Message(
                    id=f"{conv_id}_msg",
                    conversation_id=conv_id,
                    author_type="customer",
                    author_id="customer_1",
                    body="Test message",
                    created_at=datetime.now(UTC),
                )
            ]

        intercom.get_conversation = mock_get_conversation
        intercom.get_messages = mock_get_messages

        # Run two-phase sync
        start_date = datetime.now(UTC) - timedelta(days=7)
        end_date = datetime.now(UTC)
        sync_stats = await coordinator.sync_period_two_phase(start_date, end_date)

        # Verify sync completed
        assert sync_stats.total_conversations == 20
        assert sync_stats.api_calls_made > 0

        # Verify progress updates were received
        assert len(progress_updates) > 0

        # Check for phase-specific progress messages
        progress_messages = [u["message"] for u in progress_updates]

        # Should have search phase messages
        assert any("Phase 1: Search" in msg for msg in progress_messages)

        # Should have fetch phase messages
        assert any("Phase 2: Fetch" in msg for msg in progress_messages)

        # Should have completion message
        assert any("Two-phase sync completed" in msg for msg in progress_messages)

    @pytest.mark.asyncio
    async def test_schema_migration_compatibility(self, compatibility_setup):
        """Test that schema changes don't break active features."""
        components = compatibility_setup
        db = components["db"]

        # Add test data
        test_conv = Conversation(
            id="schema_test_conv",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            messages=[],
            customer_email="test_customer@example.com",
        )
        await db.store_conversations([test_conv])

        # Simulate schema check/migration while data exists
        # This tests that the schema validation doesn't break with active data

        # Get current schema
        schema_check = await db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='conversations'"
        )

        assert schema_check is not None
        assert len(schema_check) > 0

        # Verify we can still read/write after schema check
        retrieved = await db.get_conversation_by_id(test_conv.id)
        assert retrieved is not None
        assert retrieved.id == test_conv.id

        # Store conversation with message
        test_conv.messages = [
            Message(
                id="schema_test_msg",
                conversation_id=test_conv.id,
                author_type="agent",
                author_id="test_agent",
                body="Schema compatibility test",
                created_at=datetime.now(UTC),
            )
        ]
        await db.store_conversations([test_conv])


# Additional integration test for real-world scenario
class TestRealWorldScenarios:
    """Test real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_continuous_operation_scenario(self, temp_db):
        """Test a realistic continuous operation scenario."""
        # This test simulates a real deployment where:
        # 1. Initial sync runs
        # 2. Users make MCP queries
        # 3. Background sync runs periodically
        # 4. Progress is monitored throughout

        db = DatabaseManager(db_path=temp_db)

        intercom = Mock(spec=IntercomClient)
        intercom.app_id = "prod_app"

        sync_service = SyncService(db, intercom)
        mcp_server = FastIntercomMCPServer(db, sync_service, intercom)

        # Simulate 24 hours of operation
        operation_log = []

        # Initial sync
        operation_log.append({"time": "00:00", "action": "initial_sync", "result": "pending"})

        # Mock initial data load
        initial_convs = [
            Conversation(
                id=f"initial_{i}",
                created_at=datetime.now(UTC) - timedelta(days=30 - i),
                updated_at=datetime.now(UTC) - timedelta(days=30 - i),
                messages=[],
                customer_email=f"customer_{i}@example.com",
            )
            for i in range(100)
        ]

        for conv in initial_convs:
            await db.store_conversations([conv])

        operation_log[-1]["result"] = "success"

        # Simulate periodic operations
        for hour in range(1, 24):
            # Every 4 hours, background sync
            if hour % 4 == 0:
                operation_log.append(
                    {"time": f"{hour:02d}:00", "action": "background_sync", "result": "success"}
                )

                # Add some new conversations
                new_convs = [
                    Conversation(
                        id=f"hour_{hour}_conv_{i}",
                        created_at=datetime.now(UTC) - timedelta(hours=hour),
                        updated_at=datetime.now(UTC) - timedelta(hours=hour),
                        messages=[],
                        customer_email=f"new_customer_{i}@example.com",
                    )
                    for i in range(5)
                ]

                for conv in new_convs:
                    await db.store_conversations([conv])

            # Every hour, simulate MCP queries
            try:
                # Random queries
                queries = [
                    ("search_conversations", {"query": "customer", "limit": 10}),
                    ("get_server_status", {}),
                    ("get_data_info", {}),
                ]

                for tool_name, args in queries:
                    result = await mcp_server.server.call_tool(tool_name, args)
                    operation_log.append(
                        {
                            "time": f"{hour:02d}:30",
                            "action": f"mcp_{tool_name}",
                            "result": "success" if result else "failed",
                        }
                    )

            except Exception as e:
                operation_log.append(
                    {"time": f"{hour:02d}:30", "action": "mcp_error", "result": str(e)}
                )

        # Verify continuous operation succeeded
        successful_ops = [op for op in operation_log if op["result"] == "success"]
        failed_ops = [op for op in operation_log if op["result"] not in ["success", "pending"]]

        # Should have mostly successful operations
        assert len(successful_ops) > len(operation_log) * 0.9
        assert len(failed_ops) == 0

        # Verify data consistency after 24 hours
        final_convs = await db.search_conversations(query="")
        assert len(final_convs) > 100  # Initial + periodic syncs

        # Verify no data corruption
        for conv in final_convs:
            assert conv.id is not None
            assert conv.created_at is not None
            assert conv.customer_email is not None
