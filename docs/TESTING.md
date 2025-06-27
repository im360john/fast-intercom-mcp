# FastIntercom MCP Testing Guide

## Overview

This document provides comprehensive testing procedures for the FastIntercom MCP server. It serves as a complete guide for future agents and deployers to understand, run, and maintain the testing infrastructure.

The testing strategy covers multiple layers:
- Unit Tests (pytest)
- Integration Tests (real API)
- Docker Tests (clean install)
- Performance Tests (benchmarking)
- CI/CD Tests (automated)

## Test Types

### 1. Unit Tests
**Purpose**: Test individual components in isolation  
**Framework**: pytest  
**Location**: `tests/` directory  
**Duration**: < 30 seconds  

```bash
# Run all unit tests
pytest tests/

# Run specific test file
pytest tests/test_sync_service.py

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=fast_intercom_mcp
```

### 2. Integration Tests
**Purpose**: Test end-to-end functionality with real Intercom API  
**Framework**: Custom integration scripts  
**Location**: `scripts/` directory  
**Duration**: 1-5 minutes  
**Prerequisites**: Valid Intercom API token  

```bash
# Quick integration test (7 days of data)
./scripts/run_integration_test.sh

# Full integration test (30 days of data)
./scripts/run_integration_test.sh --days 30

# Performance benchmark test
./scripts/run_integration_test.sh --performance-report
```

### 3. Docker Tests
**Purpose**: Test clean installation and deployment  
**Framework**: Docker-based testing  
**Location**: `scripts/` directory  
**Duration**: 2-10 minutes  

```bash
# Test Docker build and basic functionality
./scripts/test_docker_install.sh

# Test Docker with real API data
./scripts/test_docker_install.sh --with-api-test
```

### 4. Performance Tests
**Purpose**: Validate performance benchmarks  
**Framework**: Custom benchmarking  
**Location**: Integrated with integration tests  
**Duration**: 3-10 minutes  

```bash
# Run performance benchmark
./scripts/run_performance_test.sh

# Monitor performance during sync
./scripts/monitor_performance.sh
```

## Running Tests

### Local Development

#### Prerequisites
- Python 3.11+
- Virtual environment activated
- Intercom API token (for integration tests)
- Docker (for Docker tests)

#### Quick Test Suite
```bash
# 1. Basic functionality check (30 seconds)
python3 -c "import fast_intercom_mcp.cli; print('✅ Import successful')"

# 2. CLI availability check
fast-intercom-mcp --help

# 3. Run unit tests
pytest tests/ -x --tb=short

# 4. Quick integration test (requires API token)
export INTERCOM_ACCESS_TOKEN=your_token_here
./scripts/run_integration_test.sh --quick
```

#### Complete Test Suite
```bash
# 1. Full unit test suite with coverage
pytest tests/ --cov=fast_intercom_mcp --cov-report=html

# 2. Integration test with performance monitoring
./scripts/run_integration_test.sh --performance-report

# 3. Docker clean install test
./scripts/test_docker_install.sh

# 4. Performance benchmark
./scripts/run_performance_test.sh
```

### CI/CD Pipeline

#### GitHub Actions Workflows

**Fast Check** (runs on every PR):
```bash
# Trigger manually
gh workflow run fast-check.yml

# View results
gh run list --workflow=fast-check.yml --limit=5
```

**Integration Test** (manual/weekly):
```bash
# Trigger integration test workflow
gh workflow run integration-test.yml

# View detailed logs
gh run view --log
```

**Docker Test** (on releases):
```bash
# Trigger Docker test workflow
gh workflow run docker-test.yml
```

#### Expected CI/CD Results
- **Fast Check**: < 2 minutes, validates imports and basic functionality
- **Integration Test**: 5-15 minutes, validates real API functionality
- **Docker Test**: 10-20 minutes, validates deployment scenarios

### Manual Verification

#### Local MCP Server Test
```bash
# 1. Start MCP server in test mode
fast-intercom-mcp start --test-mode &
SERVER_PID=$!

# 2. Test MCP tools
python3 scripts/test_mcp_tools.py

# 3. Clean up
kill $SERVER_PID
```

#### Database Integrity Check
```bash
# Check database schema and data
python3 scripts/verify_database_integrity.py

# View database statistics
sqlite3 ~/.fast-intercom-mcp/data.db "
SELECT 
    COUNT(*) as conversations,
    (SELECT COUNT(*) FROM messages) as messages,
    (SELECT COUNT(*) FROM sync_periods) as sync_periods
FROM conversations;
"
```

## Test Configuration

### Environment Variables
```bash
# Required for integration tests
export INTERCOM_ACCESS_TOKEN=your_token_here

# Optional test configuration
export FASTINTERCOM_TEST_LOG_LEVEL=DEBUG
export FASTINTERCOM_TEST_TIMEOUT=300
export FASTINTERCOM_TEST_DATA_RETENTION=7

# Performance test configuration
export FASTINTERCOM_PERF_TARGET_CONV_PER_SEC=10
export FASTINTERCOM_PERF_TARGET_RESPONSE_MS=100
export FASTINTERCOM_PERF_TARGET_MEMORY_MB=100
```

### Test Configuration Files

#### `tests/config.json`
```json
{
  "unit_tests": {
    "timeout": 30,
    "log_level": "WARNING"
  },
  "integration_tests": {
    "timeout": 300,
    "default_days": 7,
    "max_conversations": 1000
  },
  "performance_tests": {
    "target_conv_per_sec": 10,
    "target_response_ms": 100,
    "target_memory_mb": 100
  }
}
```

## Success Criteria

### Unit Tests
- ✅ All tests pass
- ✅ Code coverage > 80%
- ✅ No deprecation warnings
- ✅ All imports resolve correctly

### Integration Tests
- ✅ Successful API connection
- ✅ Data sync completes without errors
- ✅ Synced data matches expected format
- ✅ Performance targets met (see benchmarks below)

### Docker Tests
- ✅ Docker image builds successfully
- ✅ Container starts and serves MCP protocol
- ✅ Basic functionality works in clean environment
- ✅ No missing dependencies or configuration issues

### Performance Benchmarks

#### Expected Performance Targets
- **Sync Speed**: 10-50 conversations/second
- **Response Time**: <100ms for cached queries
- **Memory Usage**: <100MB for server process
- **Storage Efficiency**: ~2KB per conversation average

#### Performance Test Results Format
```
✅ Sync Performance: 23.4 conv/sec (target: >10)
✅ Response Time: 47ms average (target: <100ms)
✅ Memory Usage: 73MB (target: <100MB)
✅ Storage: 1.8KB/conv average (target: ~2KB)
```

## Troubleshooting

### Common Issues

#### Test Import Failures
```bash
# Problem: ImportError when running tests
# Solution: Ensure package is installed in development mode
pip install -e .
python3 -c "import fast_intercom_mcp; print('✅ Import works')"
```

#### API Connection Failures
```bash
# Problem: Integration tests fail with connection errors
# Diagnosis:
curl -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
     https://api.intercom.io/me

# Solutions:
# 1. Verify token is valid and has correct permissions
# 2. Check network connectivity
# 3. Verify token has 'conversations:read' permission
```

#### Database Locked Errors
```bash
# Problem: Database is locked during tests
# Solution: Ensure no other processes are using the database
ps aux | grep fast-intercom-mcp
pkill -f fast-intercom-mcp

# Clean up test databases
rm -f ~/.fast-intercom-mcp/test_*.db
```

#### Docker Test Failures
```bash
# Problem: Docker tests fail to build or run
# Diagnosis:
docker build -t fast-intercom-mcp-test .
docker run --rm fast-intercom-mcp-test --help

# Common solutions:
# 1. Ensure Docker is running
# 2. Check Dockerfile syntax
# 3. Verify base image availability
```

#### Performance Test Failures
```bash
# Problem: Performance tests fail to meet targets
# Diagnosis tools:
./scripts/profile_sync_performance.sh
./scripts/monitor_memory_usage.sh

# Common causes:
# 1. Large dataset (>10K conversations)
# 2. Slow network connection
# 3. Database not optimized
# 4. Insufficient system resources
```

### Debug Procedures

#### Enable Debug Logging
```bash
# For unit tests
export FASTINTERCOM_LOG_LEVEL=DEBUG
pytest tests/ -s

# For integration tests
export FASTINTERCOM_TEST_LOG_LEVEL=DEBUG
./scripts/run_integration_test.sh --verbose

# For Docker tests
./scripts/test_docker_install.sh --debug
```

#### Analyze Test Failures
```bash
# Generate detailed test report
pytest tests/ --tb=long --capture=no > test_report.txt

# View recent logs
tail -f ~/.fast-intercom-mcp/logs/fast-intercom-mcp.log

# Database debugging
sqlite3 ~/.fast-intercom-mcp/data.db .dump > db_dump.sql
```

#### Performance Debugging
```bash
# Profile sync performance
python3 -m cProfile -o sync_profile.prof scripts/profile_sync.py

# Analyze profile
python3 -c "
import pstats
p = pstats.Stats('sync_profile.prof')
p.sort_stats('cumulative').print_stats(20)
"

# Memory profiling
pip install memory-profiler
python3 -m memory_profiler scripts/profile_memory.py
```

## Continuous Integration

### Adding New Tests

#### Unit Test Example
```python
# tests/test_new_feature.py
import pytest
from fast_intercom_mcp import NewFeature

class TestNewFeature:
    def test_new_functionality(self):
        feature = NewFeature()
        result = feature.do_something()
        assert result is not None
        assert result.status == "success"
```

#### Integration Test Example
```python
# tests/test_integration_new.py
import pytest
from fast_intercom_mcp import SyncService

@pytest.mark.integration
async def test_new_integration_feature():
    service = SyncService()
    result = await service.new_feature_method()
    assert result.success is True
```

### Updating Performance Targets

When modifying performance targets:

1. Update `tests/config.json`
2. Update documentation in this file
3. Update CI/CD workflow files
4. Validate new targets with real data

### Test Data Management

#### Test Data Location
- Unit tests: Use mocked data in `tests/fixtures/`
- Integration tests: Use real API data (controlled scope)
- Performance tests: Use configurable dataset size

#### Test Data Cleanup
```bash
# Clean up test artifacts
./scripts/cleanup_test_data.sh

# Reset test environment
fast-intercom-mcp reset --test-mode
```

## Integration with Development Workflow

### Pre-commit Testing
```bash
# Add to pre-commit hook
#!/bin/bash
echo "Running pre-commit tests..."
python3 -c "import fast_intercom_mcp; print('✅ Import check')"
pytest tests/ -x --tb=short -q
echo "✅ Pre-commit tests passed"
```

### Pull Request Testing
- All PRs must pass Fast Check workflow
- Integration tests run on manual trigger
- Performance regression tests on major changes

### Release Testing
- Complete test suite must pass
- Docker tests must pass
- Performance benchmarks must be met
- Documentation must be updated

## Future Test Expansion

### Planned Test Additions
- Load testing with multiple concurrent clients
- Network failure simulation and recovery
- Database corruption recovery testing
- Memory leak detection over extended runs

### Test Infrastructure Improvements
- Automated performance regression detection
- Test result trending and analysis
- Integration with monitoring systems
- Automated test data generation

## Quick Reference

### Most Common Test Commands
```bash
# Daily development testing
pytest tests/ -x --tb=short                    # Quick unit tests
./scripts/run_integration_test.sh --quick      # Quick integration

# Before PR submission
pytest tests/ --cov=fast_intercom_mcp         # Full unit tests
./scripts/run_integration_test.sh             # Full integration

# Before release
./scripts/run_complete_test_suite.sh           # Everything
```

### Emergency Test Commands
```bash
# Test if server is functional
fast-intercom-mcp status

# Test basic API connectivity
python3 -c "
import asyncio
from fast_intercom_mcp import IntercomClient, Config
async def test(): 
    client = IntercomClient(Config.load().intercom_token)
    print('✅ Connected' if await client.test_connection() else '❌ Failed')
asyncio.run(test())
"

# Test database integrity
sqlite3 ~/.fast-intercom-mcp/data.db "PRAGMA integrity_check;"
```

This testing guide ensures comprehensive validation of the FastIntercom MCP server across all deployment scenarios and use cases.