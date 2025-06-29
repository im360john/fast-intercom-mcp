# FastIntercom MCP Testing Guide

## Table of Contents

1. [Quick Start Guide](#quick-start-guide)
2. [Test Types Overview](#test-types-overview)
3. [Environment Setup](#environment-setup)
4. [Running Tests](#running-tests)
5. [Performance Testing](#performance-testing)
6. [Test Data Management](#test-data-management)
7. [Troubleshooting](#troubleshooting)
8. [Contributing Tests](#contributing-tests)
9. [CI/CD Integration](#cicd-integration)
10. [Performance Baselines](#performance-baselines)

## Quick Start Guide

### 🚀 New Developer Quick Start (5 minutes)

```bash
# 1. Install pre-commit hook (one-time setup)
cp scripts/example-pre-commit-hook .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 2. Run quick validation
./scripts/pre_commit_validation.sh --fast

# 3. Run unit tests
pytest tests/ -x --tb=short

# 4. Quick integration test (requires API token)
export INTERCOM_ACCESS_TOKEN=your_token_here
./scripts/run_integration_test.sh --quick

# Done! You're ready to develop
```

### 📋 Essential Test Commands

```bash
# Before committing (auto-fix + validation)
./scripts/pre_commit_validation.sh --fix

# Docker CI parity test (matches GitHub Actions)
./scripts/docker_test_runner.sh --mode fast-check

# Full test suite
pytest tests/ --cov=fast_intercom_mcp --cov-report=html
```

## Test Types Overview

### 1. Unit Tests

**Purpose**: Test individual components in isolation  
**Framework**: pytest with asyncio support  
**Coverage Target**: >80%  
**Execution Time**: <30 seconds  

```bash
# Run all unit tests
pytest tests/

# Run with coverage
pytest tests/ --cov=fast_intercom_mcp --cov-report=html

# Run specific test module
pytest tests/test_sync_service.py -v

# Run tests matching pattern
pytest tests/ -k "test_database"
```

**Test Categories**:
- **Core Tests** (`test_database_init.py`): Database schema, initialization
- **Service Tests** (`test_sync_service.py`): Business logic, sync operations
- **Protocol Tests** (`test_mcp_protocol.py`): MCP communication
- **Health Tests** (`test_server_health.py`): Server status, monitoring

### 2. Integration Tests

**Purpose**: End-to-end testing with real Intercom API  
**Framework**: Custom scripts with comprehensive validation  
**Data Scope**: Configurable (1-90 days)  
**Execution Time**: 2-30 minutes  

```bash
# Standard 7-day integration test
./scripts/run_integration_test.sh

# Quick 1-day test (100 conversations max)
./scripts/run_integration_test.sh --quick

# Extended 30-day test with performance metrics
./scripts/run_integration_test.sh --days 30 --performance-report

# Debug mode with preserved environment
./scripts/run_integration_test.sh --verbose --no-cleanup
```

**Integration Test Flow**:
1. API connection validation
2. Database initialization
3. Data synchronization
4. MCP server startup
5. Tool functionality testing
6. Performance measurement
7. Cleanup and reporting

### 3. Docker Tests

**Purpose**: Validate clean deployment environment  
**Framework**: Docker-based testing scripts  
**Environment**: Ubuntu with Python 3.11  
**Execution Time**: 5-15 minutes  

```bash
# Basic Docker functionality
./scripts/test_docker_install.sh

# Docker with API integration
./scripts/test_docker_install.sh --with-api-test

# Docker CI parity testing
./scripts/docker_test_runner.sh --mode integration --api-test
```

**Docker Test Modes**:
- **fast-check**: Import validation, linting, CLI smoke test (2 min)
- **quick-test**: Limited integration test (10 min)
- **integration**: Full integration test (30 min)
- **performance**: Performance benchmarking (45 min)

### 4. Performance Tests

**Purpose**: Benchmark and track performance metrics  
**Framework**: Custom performance monitoring  
**Metrics**: Sync speed, response time, memory usage  
**Execution Time**: 10-45 minutes  

```bash
# Quick performance test
python3 quick_performance_test.py

# Comprehensive performance test
python3 performance_test.py

# Docker performance benchmarking
./scripts/docker_test_runner.sh --mode performance --performance-report
```

### 5. Pre-commit Validation

**Purpose**: Ensure code quality before commits  
**Framework**: Automated validation script  
**Checks**: Import, linting, formatting, type checking, tests  
**Execution Time**: <30 seconds (fast mode)  

```bash
# Fast validation (recommended for pre-commit)
./scripts/pre_commit_validation.sh --fast

# Full validation with auto-fix
./scripts/pre_commit_validation.sh --fix

# Validation with detailed output
./scripts/pre_commit_validation.sh --verbose
```

## Environment Setup

### Prerequisites

```bash
# System requirements
- Python 3.11+ (3.12 supported)
- SQLite 3.35+
- 2GB+ available disk space
- Network access to Intercom API

# Development tools
- Git
- Docker (optional, for Docker tests)
- Poetry or pip/venv
```

### Python Environment Setup

#### Option 1: Poetry (Recommended)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate environment
poetry shell

# Run tests
poetry run pytest tests/
```

#### Option 2: Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install package
pip install -e .

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx ruff mypy
```

#### Option 3: System Python (Not Recommended)

```bash
# Install with user flag
python3 -m pip install --user -e .

# Install test dependencies
python3 -m pip install --user pytest pytest-asyncio pytest-cov
```

### Environment Verification

```bash
# Verify Python version
python3 --version  # Should be 3.11+

# Verify package installation
python3 -c "import fast_intercom_mcp; print('✅ Package available')"

# Verify CLI installation
fast-intercom-mcp --version

# Check available tools
./scripts/pre_commit_validation.sh --verbose | head -20
```

### API Token Configuration

```bash
# Set Intercom API token
export INTERCOM_ACCESS_TOKEN="your_token_here"

# Verify token validity
curl -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
     https://api.intercom.io/me

# Token must have permissions:
# - conversations:read
# - contacts:read (optional)
# - teams:read (optional)
```

## Running Tests

### Daily Development Workflow

```bash
# Morning setup
git pull origin main
./scripts/pre_commit_validation.sh --fast

# Before commits
./scripts/pre_commit_validation.sh --fix

# After feature implementation
pytest tests/ -x --tb=short
./scripts/run_integration_test.sh --quick
```

### Pre-PR Checklist

```bash
# 1. Full validation
./scripts/pre_commit_validation.sh

# 2. Docker CI parity test
./scripts/docker_test_runner.sh --mode fast-check

# 3. Unit tests with coverage
pytest tests/ --cov=fast_intercom_mcp --cov-report=html

# 4. Integration test
./scripts/run_integration_test.sh

# 5. Check test results
cat test_results.json | jq '.summary'
```

### Release Testing

```bash
# 1. Full Docker performance test
./scripts/docker_test_runner.sh --mode performance --performance-report

# 2. Extended integration test
./scripts/run_integration_test.sh --days 30 --performance-report

# 3. Cross-platform validation
./scripts/test_docker_install.sh --with-api-test

# 4. Security scanning
bandit -r fast_intercom_mcp/
safety check
```

## Performance Testing

### Performance Metrics

#### Target Performance Baselines

| Metric | Target | Acceptable Range | Critical Threshold |
|--------|--------|------------------|-------------------|
| Sync Speed | 10+ conv/sec | 8-50 conv/sec | <5 conv/sec |
| Response Time | <100ms | 50-150ms | >500ms |
| Memory Usage | <100MB | 50-150MB | >300MB |
| Database Size | ~2KB/conv | 1.5-3KB/conv | >5KB/conv |
| Startup Time | <3 seconds | 2-5 seconds | >10 seconds |

### Running Performance Tests

```bash
# Quick performance check (5 minutes)
python3 quick_performance_test.py

# Comprehensive benchmark (30 minutes)
python3 performance_test.py --output perf_results.json

# Docker performance test with monitoring
./scripts/docker_test_runner.sh --mode performance \
  --performance-report --output docker_perf.json

# Monitor performance during development
./scripts/monitor_sync_progress.py &
MONITOR_PID=$!
./scripts/run_integration_test.sh
kill $MONITOR_PID
```

### Performance Analysis

```bash
# View performance results
cat perf_results.json | jq '.performance_metrics'

# Compare performance across runs
python3 scripts/compare_performance.py perf_results_*.json

# Generate performance report
python3 scripts/generate_performance_report.py --last-7-days
```

### Performance Optimization Tips

1. **Database Optimization**
   ```bash
   # Analyze database performance
   sqlite3 ~/.fast-intercom-mcp/data.db "ANALYZE;"
   
   # Check index usage
   sqlite3 ~/.fast-intercom-mcp/data.db "EXPLAIN QUERY PLAN SELECT ..."
   ```

2. **Memory Profiling**
   ```bash
   # Profile memory usage
   python3 -m memory_profiler scripts/profile_memory.py
   
   # Find memory leaks
   python3 scripts/check_memory_leaks.py
   ```

3. **Network Optimization**
   ```bash
   # Monitor API latency
   python3 scripts/measure_api_latency.py
   
   # Test with different batch sizes
   FASTINTERCOM_BATCH_SIZE=50 ./scripts/run_integration_test.sh
   ```

## Test Data Management

### Test Data Generation

```bash
# Generate mock conversation data
python3 scripts/generate_test_data.py --conversations 1000 --output test_data.json

# Import test data into database
python3 scripts/import_test_data.py test_data.json

# Create performance test dataset
python3 scripts/create_performance_dataset.py --size large
```

### Test Data Fixtures

```python
# tests/fixtures/conversations.py
from datetime import datetime, timedelta
import json

def create_test_conversation(conversation_id="test_123"):
    """Create a test conversation fixture"""
    return {
        "id": conversation_id,
        "created_at": int((datetime.now() - timedelta(days=1)).timestamp()),
        "updated_at": int(datetime.now().timestamp()),
        "source": {
            "type": "conversation",
            "delivered_as": "customer_initiated"
        },
        "contacts": {
            "contacts": [{
                "id": "contact_123",
                "email": "test@example.com"
            }]
        },
        "conversation_message": {
            "body": "Test message content"
        }
    }

# Usage in tests
def test_sync_conversation():
    test_data = create_test_conversation()
    # ... test implementation
```

### Test Database Management

```bash
# Create test database
fast-intercom-mcp init --test-mode --db-path ./test_data.db

# Reset test database
rm -f ./test_data.db && fast-intercom-mcp init --test-mode

# Backup test database
cp ~/.fast-intercom-mcp-test/data.db ./test_backup_$(date +%Y%m%d).db

# Analyze test database
sqlite3 ./test_data.db ".stats"
```

## Troubleshooting

### Common Test Failures

#### Import Errors

```bash
# Problem: ImportError: No module named 'fast_intercom_mcp'
# Solution 1: Install in development mode
pip install -e .

# Solution 2: Verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Solution 3: Check environment
./scripts/pre_commit_validation.sh --verbose | grep "Environment:"
```

#### API Connection Issues

```bash
# Problem: 401 Unauthorized
# Debug steps:
echo "Token length: ${#INTERCOM_ACCESS_TOKEN}"
curl -I -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
     https://api.intercom.io/me

# Problem: Rate limiting (429)
# Check rate limit headers:
curl -I -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
     https://api.intercom.io/conversations | grep -i rate
```

#### Database Issues

```bash
# Problem: Database is locked
# Find blocking processes:
lsof ~/.fast-intercom-mcp/data.db
ps aux | grep fast-intercom-mcp

# Force cleanup:
pkill -f fast-intercom-mcp
rm -f ~/.fast-intercom-mcp/data.db-journal

# Problem: Schema mismatch
# Reset database:
fast-intercom-mcp reset --confirm
```

#### Memory Issues

```bash
# Problem: Tests fail with memory errors
# Monitor memory usage:
./scripts/monitor_memory_usage.sh &
pytest tests/
pkill -f monitor_memory

# Reduce test dataset size:
export FASTINTERCOM_TEST_MAX_CONVERSATIONS=100
./scripts/run_integration_test.sh
```

#### Docker Test Issues

```bash
# Problem: Docker build fails
# Clean Docker cache:
docker system prune -f
docker builder prune -f

# Problem: Container won't start
# Debug container:
./scripts/docker_test_runner.sh --mode fast-check \
  --keep-container --verbose

# Access failed container:
docker ps -a | grep fast-intercom
docker logs <container_id>
docker exec -it <container_id> bash
```

### Debug Mode Testing

```bash
# Enable debug logging
export FASTINTERCOM_LOG_LEVEL=DEBUG
export FASTINTERCOM_TEST_LOG_LEVEL=DEBUG

# Run tests with full output
pytest tests/ -vvs --capture=no

# Integration test debug mode
./scripts/run_integration_test.sh --verbose --no-cleanup

# Docker debug mode
./scripts/docker_test_runner.sh --mode fast-check \
  --verbose --keep-container
```

### Performance Debugging

```bash
# Profile slow tests
pytest tests/ --durations=10

# Profile sync performance
python3 -m cProfile -o sync_profile.prof scripts/profile_sync.py
python3 -m pstats sync_profile.prof

# Trace database queries
export FASTINTERCOM_SQL_ECHO=true
./scripts/run_integration_test.sh
```

## Contributing Tests

### Writing New Tests

#### Unit Test Template

```python
# tests/test_new_feature.py
import pytest
from unittest.mock import Mock, patch
from fast_intercom_mcp.new_feature import NewFeature

class TestNewFeature:
    """Test cases for NewFeature functionality"""
    
    @pytest.fixture
    def feature(self):
        """Create NewFeature instance for testing"""
        return NewFeature()
    
    def test_basic_functionality(self, feature):
        """Test basic feature operations"""
        result = feature.do_something("input")
        assert result == "expected_output"
    
    @pytest.mark.asyncio
    async def test_async_operation(self, feature):
        """Test async operations"""
        result = await feature.async_operation()
        assert result.success is True
    
    def test_error_handling(self, feature):
        """Test error conditions"""
        with pytest.raises(ValueError):
            feature.do_something(None)
```

#### Integration Test Template

```python
# tests/integration/test_new_integration.py
import pytest
from fast_intercom_mcp import Config, SyncService

@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_integration_flow():
    """Test complete integration flow"""
    # Setup
    config = Config(intercom_token="test_token")
    service = SyncService(config)
    
    # Execute
    result = await service.sync_conversations(days=1)
    
    # Verify
    assert result.success is True
    assert result.conversations_synced > 0
    assert result.errors == []
```

### Test Best Practices

1. **Test Naming**
   - Use descriptive names: `test_sync_handles_rate_limiting`
   - Group related tests in classes
   - Use consistent prefixes for test types

2. **Test Structure**
   - Arrange-Act-Assert pattern
   - One assertion per test (when possible)
   - Use fixtures for common setup

3. **Test Data**
   - Use factories for test data creation
   - Avoid hardcoded values
   - Clean up test data after tests

4. **Mocking**
   - Mock external dependencies
   - Use `pytest-mock` for cleaner mocking
   - Verify mock calls when appropriate

5. **Performance Tests**
   - Use `pytest-benchmark` for micro-benchmarks
   - Set reasonable timeouts
   - Track performance over time

### Adding Test Coverage

```bash
# Check current coverage
pytest tests/ --cov=fast_intercom_mcp --cov-report=html
open htmlcov/index.html

# Find uncovered code
pytest tests/ --cov=fast_intercom_mcp --cov-report=term-missing

# Generate coverage badge
coverage-badge -o coverage.svg
```

## CI/CD Integration

### GitHub Actions Workflows

#### Fast Check Workflow
```yaml
# Runs on every PR and push to main
# Duration: <2 minutes
# Checks: imports, linting, CLI functionality
```

#### Integration Test Workflow
```yaml
# Manual trigger or scheduled
# Duration: 5-30 minutes
# Full API integration testing
```

### Pre-commit Hooks

```bash
# Install pre-commit framework
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

### Local CI Simulation

```bash
# Simulate GitHub Actions locally
./scripts/docker_test_runner.sh --mode fast-check

# Run all CI checks
./scripts/docker_test_runner.sh --mode integration --api-test
```

## Performance Baselines

### Baseline Tracking

```bash
# Record baseline performance
python3 scripts/record_baseline.py --tag v0.3.0

# Compare against baseline
python3 scripts/compare_to_baseline.py --baseline v0.3.0

# Generate performance trend report
python3 scripts/performance_trends.py --last-30-days
```

### Performance Regression Detection

```bash
# Automated regression detection
python3 scripts/detect_regression.py --threshold 10

# Performance comparison between branches
python3 scripts/compare_branches.py main feature/optimization
```

### Baseline Metrics Storage

```json
// performance_baselines.json
{
  "v0.3.0": {
    "date": "2024-01-15",
    "metrics": {
      "sync_speed": 23.4,
      "response_time_ms": 47,
      "memory_usage_mb": 73,
      "startup_time_s": 2.1
    },
    "environment": {
      "python_version": "3.11.5",
      "sqlite_version": "3.40.0",
      "platform": "darwin"
    }
  }
}
```

## Quick Reference Card

### Essential Commands

```bash
# Daily development
./scripts/pre_commit_validation.sh --fast    # Pre-commit check
pytest tests/ -x --tb=short                  # Quick unit tests
./scripts/run_integration_test.sh --quick    # Quick integration

# Before PR
./scripts/pre_commit_validation.sh --fix     # Auto-fix + validate
./scripts/docker_test_runner.sh --mode fast-check  # CI parity
pytest tests/ --cov=fast_intercom_mcp       # Coverage check

# Performance testing
python3 performance_test.py                  # Local performance
./scripts/docker_test_runner.sh --mode performance  # Docker perf

# Debugging
export FASTINTERCOM_LOG_LEVEL=DEBUG         # Enable debug logs
./scripts/run_integration_test.sh --verbose --no-cleanup  # Debug mode
pytest tests/ -vvs --capture=no             # Verbose test output
```

### Environment Variables

```bash
# Required
export INTERCOM_ACCESS_TOKEN="your_token"

# Optional
export FASTINTERCOM_LOG_LEVEL=INFO
export FASTINTERCOM_TEST_TIMEOUT=300
export FASTINTERCOM_BATCH_SIZE=100
export FASTINTERCOM_TEST_MAX_CONVERSATIONS=1000
```

### File Locations

```
~/.fast-intercom-mcp/          # Production data
~/.fast-intercom-mcp-test/     # Test data
./test_results.json            # Latest test results
./htmlcov/index.html          # Coverage report
./performance_results.json     # Performance metrics
```

---

This comprehensive testing guide ensures that all developers and contributors can effectively test, debug, and maintain the FastIntercom MCP server with confidence. Regular testing and performance monitoring help maintain high code quality and optimal performance.