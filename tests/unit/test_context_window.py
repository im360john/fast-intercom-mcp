"""Unit tests for context window management."""
import pytest
from fast_intercom_mcp.utils.context_window import ContextWindowManager, TruncationResult


def test_token_estimation():
    """Test token estimation functionality."""
    manager = ContextWindowManager(max_tokens=1000)
    
    # Test simple text
    tokens = manager.estimate_tokens("Hello world")
    assert tokens > 0
    
    # Test JSON data
    data = {"key": "value" * 100}
    tokens = manager.estimate_tokens(data)
    assert tokens > 100


def test_list_truncation():
    """Test list truncation based on token limits."""
    manager = ContextWindowManager(max_tokens=1000)
    
    # Create large list
    items = [{"id": i, "data": "x" * 100} for i in range(100)]
    
    result = manager.truncate_list_response(items, max_items=10)
    
    assert result.truncated == True
    assert result.returned_count == 10
    assert result.original_count == 100
    assert result.estimated_tokens > 0


def test_truncated_response_format():
    """Test the format of truncated responses."""
    manager = ContextWindowManager()
    
    # Create truncation result
    result = TruncationResult(
        data=[{"id": 1}],
        truncated=True,
        original_count=100,
        returned_count=1,
        estimated_tokens=50
    )
    
    response = manager.create_truncated_response(result, "test_entity")
    
    assert 'data' in response
    assert 'meta' in response
    assert 'assistant_instruction' in response
    assert response['meta']['truncated'] == True
    assert response['meta']['total_items'] == 100
    assert response['meta']['returned_items'] == 1


def test_preview_fields():
    """Test preview field functionality."""
    manager = ContextWindowManager()
    
    items = [
        {"id": 1, "name": "Test", "description": "Long description", "internal": "secret"},
        {"id": 2, "name": "Test2", "description": "Another description", "internal": "secret2"}
    ]
    
    result = manager.truncate_list_response(
        items, 
        max_items=10,
        preview_fields=['id', 'name']
    )
    
    # Check that only preview fields are included
    for item in result.data:
        assert 'id' in item
        assert 'name' in item
        assert 'description' not in item
        assert 'internal' not in item


def test_refinement_suggestions():
    """Test that appropriate refinement suggestions are provided."""
    manager = ContextWindowManager()
    
    # Test conversation suggestions
    suggestions = manager._get_refinement_suggestions("conversations")
    assert any("customer email" in s for s in suggestions)
    
    # Test article suggestions
    suggestions = manager._get_refinement_suggestions("articles")
    assert any("article title" in s for s in suggestions)
    
    # Test ticket suggestions
    suggestions = manager._get_refinement_suggestions("tickets")
    assert any("ticket state" in s for s in suggestions)