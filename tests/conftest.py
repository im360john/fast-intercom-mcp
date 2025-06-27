"""Shared test configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.mcp_server import FastIntercomMCPServer
from fast_intercom_mcp.sync_service import SyncService


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


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
def mock_intercom_client():
    """Create a mock Intercom client."""
    return Mock()


@pytest.fixture
def test_server(mock_database_manager, mock_sync_service, mock_intercom_client):
    """Create a test server instance with mocked dependencies."""
    return FastIntercomMCPServer(
        database_manager=mock_database_manager,
        sync_service=mock_sync_service,
        intercom_client=mock_intercom_client
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
