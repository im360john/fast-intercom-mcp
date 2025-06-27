"""Test configuration and fixtures for fast-intercom-mcp."""

import asyncio
import os
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient
from fast_intercom_mcp.mcp_server import FastIntercomMCPServer
from fast_intercom_mcp.models import Conversation, Message, SyncStats
from fast_intercom_mcp.sync.service import EnhancedSyncService
from fast_intercom_mcp.sync_service import SyncService


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_db():
    """Provide a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        yield db_path
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def mock_database_manager():
    """Create a mock database manager with common default behavior."""
    mock_db = Mock(spec=DatabaseManager)
    mock_db.db_path = ":memory:"
    mock_db.get_sync_status.return_value = {
        'database_size_mb': 1.5,
        'total_conversations': 100,
        'total_messages': 500,
        'last_sync': '2023-01-01T12:00:00',
        'database_path': ':memory:',
        'recent_syncs': []
    }
    mock_db.search_conversations.return_value = []
    mock_db.get_data_freshness_for_timeframe.return_value = 0
    mock_db.record_request_pattern = Mock()
    return mock_db


@pytest.fixture
def mock_sync_service():
    """Create a mock sync service with common default behavior."""
    mock_sync = Mock(spec=SyncService)
    mock_sync.get_status.return_value = {
        'active': True,
        'current_operation': None
    }
    mock_sync.sync_if_needed = AsyncMock(return_value={
        'sync_state': 'fresh',
        'message': 'Data is up to date',
        'data_complete': True
    })
    mock_sync.sync_recent = AsyncMock()
    mock_sync.sync_period = AsyncMock()
    return mock_sync


@pytest.fixture
def mock_intercom_client(test_conversations):
    """Create a mock Intercom client."""
    client = Mock(spec=IntercomClient)
    client.access_token = "test_token"
    
    # Use AsyncMock for proper assertion support
    client.fetch_conversations_for_period = AsyncMock(return_value=test_conversations)
    client.fetch_conversations_incremental = AsyncMock(return_value=SyncStats(
        total_conversations=1,
        new_conversations=1,
        updated_conversations=0,
        total_messages=2,
        duration_seconds=1.0,
        api_calls_made=1
    ))
    client.fetch_complete_conversation_thread = AsyncMock()
    client.fetch_individual_conversations = AsyncMock(return_value=test_conversations)
    client.get_app_id = AsyncMock(return_value="test_app_123")
    client.test_connection = AsyncMock(return_value=True)
    return client


@pytest.fixture
def test_server(mock_database_manager, mock_sync_service, mock_intercom_client):
    """Create a test server instance with mocked dependencies."""
    return FastIntercomMCPServer(
        database_manager=mock_database_manager,
        sync_service=mock_sync_service,
        intercom_client=mock_intercom_client
    )


@pytest.fixture
def database_manager(temp_db):
    """Provide a real database manager for integration tests."""
    return DatabaseManager(db_path=temp_db)


@pytest.fixture
def test_conversations():
    """Provide test conversation data for sync verification."""
    now = datetime.now(UTC)
    
    conversations = [
        # Conversation 1: Simple with customer/admin interaction
        Conversation(
            id="test_conv_1",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1),
            customer_email="user1@example.com",
            tags=["support", "high-priority"],
            messages=[
                Message(
                    id="msg_1",
                    author_type="user",
                    body="I need help with my account",
                    created_at=now - timedelta(hours=2),
                    part_type="comment"
                ),
                Message(
                    id="msg_2",
                    author_type="admin",
                    body="I'd be happy to help you with that",
                    created_at=now - timedelta(hours=2, minutes=5),
                    part_type="comment"
                ),
                Message(
                    id="msg_3",
                    author_type="user",
                    body="Thank you for the quick response",
                    created_at=now - timedelta(hours=1),
                    part_type="comment"
                )
            ]
        ),
        # Conversation 2: Billing inquiry
        Conversation(
            id="test_conv_2",
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=3),
            customer_email="user2@example.com",
            tags=["billing"],
            messages=[
                Message(
                    id="msg_4",
                    author_type="user",
                    body="Question about my invoice",
                    created_at=now - timedelta(hours=3),
                    part_type="comment"
                ),
                Message(
                    id="msg_5",
                    author_type="admin",
                    body="Let me look into that for you",
                    created_at=now - timedelta(hours=3, minutes=2),
                    part_type="comment"
                )
            ]
        ),
        # Conversation 3: Long thread with many messages
        Conversation(
            id="test_conv_3_long",
            created_at=now - timedelta(hours=4),
            updated_at=now - timedelta(minutes=30),
            customer_email="user3@example.com",
            tags=["feature-request"],
            messages=[
                Message(
                    id=f"msg_{i}",
                    author_type="user" if i % 2 == 0 else "admin",
                    body=f"Message {i} content",
                    created_at=now - timedelta(hours=4, minutes=i*5),
                    part_type="comment"
                )
                for i in range(25)  # Long conversation with 25 messages
            ]
        ),
        # Conversation 4: Recent conversation
        Conversation(
            id="conv_4",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(minutes=30),
            customer_email="user4@example.com",
            tags=["new"],
            messages=[
                Message(
                    id="msg_4_1",
                    author_type="user",
                    body="Just started using your service",
                    created_at=now - timedelta(hours=2),
                    part_type="comment"
                )
            ]
        ),
        # Conversation 5: Empty conversation (edge case)
        Conversation(
            id="conv_5",
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
            customer_email="user5@example.com",
            tags=[],
            messages=[]
        )
    ]
    
    return conversations


@pytest.fixture
def sync_service(database_manager, mock_intercom_client):
    """Provide a SyncService instance for testing."""
    return SyncService(database_manager, mock_intercom_client)


@pytest.fixture
def enhanced_sync_service(database_manager, mock_intercom_client):
    """Provide an EnhancedSyncService instance for testing."""
    return EnhancedSyncService(database_manager, mock_intercom_client)


@pytest.fixture
def test_sync_stats():
    """Provide test sync statistics."""
    return SyncStats(
        total_conversations=3,
        new_conversations=2,
        updated_conversations=1,
        total_messages=30,
        duration_seconds=5.5,
        api_calls_made=3
    )


@pytest.fixture
def mock_sync_stats():
    """Provide mock sync statistics (alternative name for compatibility)."""
    return SyncStats(
        total_conversations=10,
        new_conversations=5,
        updated_conversations=3,
        total_messages=25,
        api_calls=8,
        duration_seconds=2.5
    )


@pytest.fixture
def mock_progress_callback():
    """Provide a mock progress callback for testing."""
    return Mock()


# Test configuration
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit test marker to all tests by default
        if not any(marker.name in ['integration', 'slow'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)