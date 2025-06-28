# FastIntercom MCP Testing Guide

## Table of Contents

- [Overview](#overview)
- [Test Consistency and Quality Assurance](#test-consistency-and-quality-assurance)
- [Test Consistency Guidelines](#test-consistency-guidelines)
- [Pre-commit Validation Procedures](#pre-commit-validation-procedures)
- [Docker Test Runner and Local CI Mirror](#docker-test-runner-and-local-ci-mirror)
- [Environment Setup Best Practices](#environment-setup-best-practices)
- [Test Types](#test-types)
- [Running Tests](#running-tests)
- [CI/CD Pipeline](#cicd-pipeline)
- [Manual Verification](#manual-verification)
- [Test Configuration](#test-configuration)
- [Success Criteria](#success-criteria)
- [Troubleshooting](#troubleshooting)
- [Continuous Integration](#continuous-integration)
- [Integration with Development Workflow](#integration-with-development-workflow)
- [Future Test Expansion](#future-test-expansion)
- [Quick Reference](#quick-reference)

## Overview

This document provides comprehensive testing procedures for the FastIntercom MCP server. It serves as a complete guide for future agents and deployers to understand, run, and maintain the testing infrastructure.

The testing strategy covers multiple layers:
- Unit Tests (pytest)
- Integration Tests (real API)
- Docker Tests (clean install)
- Performance Tests (benchmarking)
- CI/CD Tests (automated)
- **Test Consistency Tools (NEW)** - Standardized validation and pre-commit workflows
- **Local CI Mirror Testing (NEW)** - Docker-based environment parity with CI

## Test Consistency and Quality Assurance

The project now includes robust test consistency tools to ensure uniform validation across all development environments and maintain code quality standards.

### Quick Reference - New Testing Tools

```bash
# Pre-commit validation (recommended before every commit)
./scripts/pre_commit_validation.sh

# Docker CI parity testing (matches GitHub Actions exactly)
./scripts/docker_test_runner.sh --mode fast-check

# Auto-fix linting and formatting issues
./scripts/pre_commit_validation.sh --fix

# Full validation with performance reporting
./scripts/docker_test_runner.sh --mode performance --performance-report
```

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
**Framework**: Custom integration script with comprehensive testing  
**Location**: `scripts/run_integration_test.sh`  
**Duration**: 1-5 minutes  
**Prerequisites**: Valid Intercom API token  

```bash
# Quick integration test (1 day, 100 conversations)
./scripts/run_integration_test.sh --quick

# Standard integration test (7 days of data)
./scripts/run_integration_test.sh

# Extended integration test (30 days of data)
./scripts/run_integration_test.sh --days 30

# Performance benchmark test
./scripts/run_integration_test.sh --performance-report

# Debug test with verbose output
./scripts/run_integration_test.sh --verbose --no-cleanup
```

### 3. Docker Tests
**Purpose**: Test clean installation and deployment  
**Framework**: Comprehensive Docker testing script  
**Location**: `scripts/test_docker_install.sh`  
**Duration**: 2-10 minutes  

```bash
# Basic Docker functionality test
./scripts/test_docker_install.sh

# Full Docker test with API integration
./scripts/test_docker_install.sh --with-api-test

# Debug Docker issues with container preservation
./scripts/test_docker_install.sh --debug --keep-container

# Test with custom configuration
./scripts/test_docker_install.sh --config ./test-configs/docker-test.json
```

### 4. MCP Protocol Tests
**Purpose**: Test individual MCP tools and protocol compliance  
**Framework**: Python-based MCP tool tester  
**Location**: `scripts/test_mcp_tools.py`  
**Duration**: 30 seconds - 2 minutes  

```bash
# Test all MCP tools
python3 scripts/test_mcp_tools.py

# Test specific tool
python3 scripts/test_mcp_tools.py --tool search_conversations

# Verbose testing with results output
python3 scripts/test_mcp_tools.py --verbose --output mcp_results.json

# Test with custom timeout
python3 scripts/test_mcp_tools.py --timeout 60
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
python3 -c "import fast_intercom_mcp; print('✅ Import successful')"

# 2. CLI availability check
fast-intercom-mcp --help

# 3. Run unit tests
pytest tests/ -x --tb=short

# 4. Quick integration test (requires API token)
export INTERCOM_ACCESS_TOKEN=your_token_here
./scripts/run_integration_test.sh --quick

# 5. Test MCP tools
python3 scripts/test_mcp_tools.py
```

#### Complete Test Suite
```bash
# 1. Full unit test suite with coverage
pytest tests/ --cov=fast_intercom_mcp --cov-report=html

# 2. Integration test with performance monitoring
./scripts/run_integration_test.sh --performance-report --output integration_results.json

# 3. Docker clean install test
./scripts/test_docker_install.sh --with-api-test

# 4. MCP protocol compliance test
python3 scripts/test_mcp_tools.py --verbose --output mcp_results.json
```

### CI/CD Pipeline

#### GitHub Actions Workflows

**Fast Check** (runs on every PR and push to main):
```bash
# Trigger manually
gh workflow run fast-check.yml

# View results
gh run list --workflow=fast-check.yml --limit=5

# Check latest run status
gh run view $(gh run list --workflow=fast-check.yml --limit=1 --json databaseId --jq '.[0].databaseId')
```

**Integration Test** (manual trigger with workflow_dispatch):
```bash
# Trigger integration test workflow from Issue #37
gh workflow run integration-test.yml

# Trigger with custom parameters
gh workflow run integration-test.yml -f sync_days=30 -f run_full_test=true

# View detailed logs
gh run view --log
```

Note: The integration test workflow was implemented in Issue #37 and runs comprehensive API testing with real data.

#### Expected CI/CD Results
- **Fast Check**: < 2 minutes, validates imports, linting, and CLI smoke test
- **Integration Test**: 5-30 minutes, validates real API functionality with 30+ days of data
- **Docker Test**: Can be triggered via local scripts for deployment validation

## Test Consistency Guidelines

### Environment Detection and Validation

All testing scripts now include automatic environment detection to ensure consistent behavior across different development setups:

**Supported Environments:**
- **Poetry Projects**: Detected via `pyproject.toml` + `poetry` command
- **Virtual Environments**: Detected via `venv/` or `.venv/` directories
- **System Python**: Fallback when no virtual environment is detected

**Environment Setup Verification:**
```bash
# Verify your environment is properly detected
./scripts/pre_commit_validation.sh --verbose

# Check available tools in current environment
command -v poetry && echo "✅ Poetry available" || echo "❌ Poetry not found"
command -v ruff && echo "✅ Ruff available" || echo "❌ Ruff not found"
command -v pytest && echo "✅ Pytest available" || echo "❌ Pytest not found"
```

### Code Quality Standards

**Mandatory Checks Before Commit:**
1. **Import Validation**: `python -c "import fast_intercom_mcp; print('✅ Import successful')"`
2. **Linting**: `ruff check . --config pyproject.toml`
3. **Code Formatting**: `ruff format --check . --config pyproject.toml`
4. **Type Checking**: `mypy fast_intercom_mcp/ --config-file pyproject.toml`
5. **CLI Functionality**: `python -m fast_intercom_mcp --help`
6. **Unit Tests**: `pytest tests/ -x --tb=short`

**Consistency Enforcement:**
- All scripts use environment-aware commands
- Standardized error handling and reporting
- Uniform timeout and performance targets
- Cross-platform compatibility (Linux, macOS, Windows)

## Pre-commit Validation Procedures

### Automated Pre-commit Validation

The `pre_commit_validation.sh` script provides comprehensive pre-commit validation with intelligent environment detection.

#### Basic Usage
```bash
# Full validation (recommended for pre-commit)
./scripts/pre_commit_validation.sh

# Fast validation (linting and imports only)
./scripts/pre_commit_validation.sh --fast

# Auto-fix issues before validation
./scripts/pre_commit_validation.sh --fix

# Quiet mode for CI/automated environments
./scripts/pre_commit_validation.sh --quiet

# Debug mode with verbose output
./scripts/pre_commit_validation.sh --verbose
```

#### Advanced Options
```bash
# Skip specific validation types
./scripts/pre_commit_validation.sh --skip-tests --skip-type-check

# Save validation results to JSON
./scripts/pre_commit_validation.sh --output validation_results.json

# Skip import or CLI checks
./scripts/pre_commit_validation.sh --no-import-check --no-cli-check
```

#### Validation Sequence

1. **Environment Detection** (auto-detects Poetry, venv, or system Python)
2. **Environment Setup** (installs dependencies as needed)
3. **Import Validation** (tests module imports)
4. **CLI Validation** (tests CLI availability via multiple methods)
5. **Code Linting** (ruff with project configuration)
6. **Code Formatting** (ruff format check)
7. **Type Checking** (mypy with project configuration)
8. **Unit Tests** (pytest with smart test discovery)

#### Exit Codes
- `0` - All validations passed
- `1` - Environment setup failed
- `2` - Import test failed
- `3` - Linting failed
- `4` - Type checking failed
- `5` - Tests failed
- `6` - CLI test failed
- `7` - Multiple validation failures

### Git Pre-commit Hook Setup

#### Install Pre-commit Hook
```bash
# Copy example hook to Git hooks directory
cp scripts/example-pre-commit-hook .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Verify hook installation
ls -la .git/hooks/pre-commit
```

#### Hook Features
- Automatically runs `pre_commit_validation.sh --fast --quiet`
- Provides helpful error messages and fix suggestions
- Blocks commits if validation fails
- Fast execution (< 30 seconds) optimized for pre-commit workflow

#### Manual Hook Testing
```bash
# Test pre-commit hook manually
.git/hooks/pre-commit

# Test what would run during pre-commit
./scripts/pre_commit_validation.sh --fast
```

## Docker Test Runner and Local CI Mirror

### Docker-based CI Parity Testing

The `docker_test_runner.sh` script provides local testing that exactly matches the CI environment, ensuring consistency between local development and automated testing.

#### Test Modes

**Fast Check** (2 minutes - matches CI fast-check):
```bash
./scripts/docker_test_runner.sh --mode fast-check
```
- Python import validation
- Critical linting (E,F errors only)
- CLI smoke test
- Package structure validation

**Quick Test** (10 minutes - matches CI quick-test):
```bash
./scripts/docker_test_runner.sh --mode quick-test --api-test
```
- Fast integration with limited data (2 hours)
- API connection validation
- MCP tools testing
- Basic sync functionality

**Integration Test** (30 minutes):
```bash
./scripts/docker_test_runner.sh --mode integration --api-test
```
- Comprehensive integration with 7 days of data
- Full API functionality testing
- Database integrity validation
- MCP protocol compliance

**Performance Test** (45 minutes):
```bash
./scripts/docker_test_runner.sh --mode performance --api-test --performance-report
```
- Performance benchmarking with 30 days of data
- Resource usage monitoring
- Response time measurement
- Performance target validation

#### Advanced Docker Testing Options

```bash
# Clean build (no Docker cache)
./scripts/docker_test_runner.sh --mode integration --clean-build

# Keep container for debugging
./scripts/docker_test_runner.sh --mode fast-check --keep-container --verbose

# Save detailed results
./scripts/docker_test_runner.sh --mode performance --output perf_results.json

# Parallel test execution (where supported)
./scripts/docker_test_runner.sh --mode quick-test --parallel
```

#### Environment Parity Features

**Exact CI Matching:**
- Python 3.11 (matches GitHub Actions)
- Ubuntu-based container (matches CI runners)
- Identical package versions: `pytest pytest-asyncio pytest-cov httpx[http2] ruff mypy`
- Same timeout constraints and performance targets
- Identical test commands and environment variables

**Container Features:**
- Non-root test user for security
- Isolated test network
- Volume mounts for result preservation
- Health checks for container readiness
- Automatic cleanup (unless `--keep-container` specified)

#### Docker Test Results

Results are saved to `test_results/` directory:
```bash
# View fast check results
cat test_results/docker_test_report.json | jq '.test_metadata'

# View performance metrics
cat test_results/performance_results.json | jq '.performance_metrics'

# View integration test summary
cat test_results/integration_results.json | jq '.summary'
```

### Environment Setup Best Practices

#### Development Environment Verification

**Required Tools Check:**
```bash
# Verify all required development tools
echo "🔍 Development Environment Check:"
command -v python3 >/dev/null 2>&1 && echo "✅ Python 3 available" || echo "❌ Python 3 not found"
command -v poetry >/dev/null 2>&1 && echo "✅ Poetry available" || echo "❌ Poetry not found"
command -v docker >/dev/null 2>&1 && echo "✅ Docker available" || echo "❌ Docker not found"
command -v git >/dev/null 2>&1 && echo "✅ Git available" || echo "❌ Git not found"
```

**Environment-Specific Setup:**

*Poetry Projects (Recommended):*
```bash
# Install dependencies
poetry install

# Verify installation
poetry run python -c "import fast_intercom_mcp; print('✅ Package available')"

# Run validation
poetry run ./scripts/pre_commit_validation.sh
```

*Virtual Environment Projects:*
```bash
# Create and activate environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Verify installation
python -c "import fast_intercom_mcp; print('✅ Package available')"

# Run validation
./scripts/pre_commit_validation.sh
```

*System Python (Not Recommended):*
```bash
# Install with user flag
python3 -m pip install --user -e .

# Verify installation
python3 -c "import fast_intercom_mcp; print('✅ Package available')"

# Run validation
./scripts/pre_commit_validation.sh
```

#### Environment Troubleshooting

**Common Environment Issues:**

*Import Failures:*
```bash
# Problem: ImportError when running tests
# Solution: Ensure package is installed in development mode
pip install -e .  # or poetry install
python3 -c "import fast_intercom_mcp; print('✅ Import works')"
```

*Tool Availability Issues:*
```bash
# Problem: ruff/mypy not found
# Solution: Install tools in current environment
poetry add --group dev ruff mypy pytest  # Poetry
pip install ruff mypy pytest  # venv
python3 -m pip install --user ruff mypy pytest  # system
```

*Poetry Issues:*
```bash
# Problem: Poetry commands fail
# Solution: Reinstall dependencies
poetry env remove python  # Remove environment
poetry install  # Reinstall
```

*Docker Issues:*
```bash
# Problem: Docker build fails
# Solution: Check Docker daemon and disk space
docker info  # Verify daemon running
df -h  # Check available disk space (need 2GB+)
docker system prune  # Clean up if space is low
```

### Manual Verification

#### Local MCP Server Test
```bash
# 1. Start MCP server in test mode
fast-intercom-mcp start --test-mode &
SERVER_PID=$!

# 2. Test MCP tools
python3 scripts/test_mcp_tools.py --verbose

# 3. Test specific tools
python3 scripts/test_mcp_tools.py --tool search_conversations
python3 scripts/test_mcp_tools.py --tool get_server_status

# 4. Clean up
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

# NEW: For pre-commit validation debugging
./scripts/pre_commit_validation.sh --verbose

# NEW: For Docker test runner debugging
./scripts/docker_test_runner.sh --mode fast-check --verbose --keep-container
```

#### NEW: Test Consistency Debugging

**Pre-commit Validation Issues:**
```bash
# Problem: Pre-commit validation fails with environment errors
# Solution: Run with verbose output to see environment detection
./scripts/pre_commit_validation.sh --verbose

# Problem: Linting failures
# Solution: Auto-fix and see what was changed
./scripts/pre_commit_validation.sh --fix --verbose

# Problem: Import failures in validation
# Solution: Check environment setup
./scripts/pre_commit_validation.sh --verbose 2>&1 | grep -A10 "Environment Setup"
```

**Docker Test Runner Issues:**
```bash
# Problem: Docker build fails
# Solution: Use clean build and verbose output
./scripts/docker_test_runner.sh --mode fast-check --clean-build --verbose

# Problem: Container starts but tests fail
# Solution: Keep container for inspection
./scripts/docker_test_runner.sh --mode fast-check --keep-container --verbose
docker exec -it fast-intercom-mcp-test-<timestamp> bash

# Problem: API tests fail in Docker
# Solution: Check environment variable passing
./scripts/docker_test_runner.sh --mode quick-test --api-test --verbose 2>&1 | grep INTERCOM
```

**Environment Detection Issues:**
```bash
# Problem: Wrong environment detected
# Solution: Check environment indicators
echo "Current directory: $(pwd)"
echo "Poetry available: $(command -v poetry >/dev/null 2>&1 && echo "Yes" || echo "No")"
echo "Virtual env files:"
ls -la | grep -E "(venv|\.venv|pyproject\.toml)"

# Problem: Tools not found in environment
# Solution: Verify tool installation in detected environment
if command -v poetry >/dev/null 2>&1; then
    poetry run which ruff mypy pytest
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate && which ruff mypy pytest
else
    which ruff mypy pytest
fi
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

### Standardized Pre-commit Testing

#### Recommended Pre-commit Workflow
```bash
# Standard pre-commit sequence (copy-paste ready)
echo "🔍 Running standardized pre-commit validation..."
./scripts/pre_commit_validation.sh --fast
echo "✅ Pre-commit validation completed"
```

#### Advanced Pre-commit Options
```bash
# Auto-fix issues before committing
./scripts/pre_commit_validation.sh --fix

# Full validation with all checks
./scripts/pre_commit_validation.sh

# CI-style validation with Docker
./scripts/docker_test_runner.sh --mode fast-check
```

#### Integration with Git Hooks
```bash
# Install standardized pre-commit hook
cp scripts/example-pre-commit-hook .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Test hook manually
.git/hooks/pre-commit
```

### Pull Request Testing

**Enhanced PR Testing Workflow:**

**Before Creating PR:**
```bash
# 1. Run standardized pre-commit validation with auto-fix
./scripts/pre_commit_validation.sh --fix

# 2. Run Docker CI parity test (matches GitHub Actions exactly)
./scripts/docker_test_runner.sh --mode fast-check

# 3. Optional: Quick integration test if API changes
./scripts/docker_test_runner.sh --mode quick-test --api-test
```

**PR Requirements:**
- All PRs must pass Fast Check workflow (automatically triggered)
- NEW: Pre-commit validation must pass locally before pushing
- NEW: Docker CI parity tests recommended for environment consistency
- Integration tests run on manual trigger
- Performance regression tests on major changes

**PR Testing Checklist:**
- [ ] Local pre-commit validation passes: `./scripts/pre_commit_validation.sh`
- [ ] Docker fast-check passes: `./scripts/docker_test_runner.sh --mode fast-check`
- [ ] All existing tests pass: `pytest tests/`
- [ ] No linting issues: `ruff check .`
- [ ] Type checking passes: `mypy fast_intercom_mcp/`
- [ ] CLI functionality works: `python -m fast_intercom_mcp --help`

### Release Testing

**Enhanced Release Testing Process:**

**Pre-Release Validation:**
```bash
# 1. Full pre-commit validation suite
./scripts/pre_commit_validation.sh --verbose --output release_validation.json

# 2. Comprehensive Docker testing with performance metrics
./scripts/docker_test_runner.sh --mode performance --performance-report --output release_performance.json

# 3. Traditional integration testing
./scripts/run_integration_test.sh --performance-report

# 4. Docker deployment testing
./scripts/test_docker_install.sh --with-api-test
```

**Release Requirements:**
- Complete test suite must pass
- NEW: All test consistency validations must pass
- NEW: Docker performance tests must meet targets
- Docker tests must pass
- Performance benchmarks must be met
- Documentation must be updated
- NEW: Pre-commit hooks must be tested and working

**Release Testing Checklist:**
- [ ] Full pre-commit validation: `./scripts/pre_commit_validation.sh`
- [ ] Docker performance test: `./scripts/docker_test_runner.sh --mode performance`
- [ ] Integration test with metrics: `./scripts/run_integration_test.sh --performance-report`
- [ ] Docker installation test: `./scripts/test_docker_install.sh --with-api-test`
- [ ] MCP tools comprehensive test: `python3 scripts/test_mcp_tools.py --verbose`
- [ ] Pre-commit hook installation test: `cp scripts/example-pre-commit-hook .git/hooks/pre-commit && .git/hooks/pre-commit`
- [ ] Documentation updated to reflect any new features or changes

### Continuous Integration Enhancement

**Local CI Mirror Testing:**
- Use `./scripts/docker_test_runner.sh` to exactly match CI environment
- Test locally before pushing to avoid CI failures
- Performance benchmarking with identical constraints
- Environment parity ensures consistent results

**Quality Gates:**
1. **Development Gate**: Pre-commit validation passes
2. **PR Gate**: Docker fast-check passes + code review
3. **Integration Gate**: Full Docker integration test passes
4. **Release Gate**: Performance tests meet targets + comprehensive validation

## Future Test Expansion

### Planned Test Additions
- Load testing with multiple concurrent clients
- Network failure simulation and recovery
- Database corruption recovery testing
- Memory leak detection over extended runs
- **NEW**: Multi-environment test matrix (Python 3.9, 3.10, 3.11, 3.12)
- **NEW**: Cross-platform consistency testing (Linux, macOS, Windows)
- **NEW**: Container security scanning integration
- **NEW**: API versioning compatibility testing

### Test Infrastructure Improvements
- Automated performance regression detection
- Test result trending and analysis
- Integration with monitoring systems
- Automated test data generation
- **NEW**: Test consistency metrics dashboard
- **NEW**: Pre-commit hook analytics and optimization
- **NEW**: Docker image caching and optimization
- **NEW**: Parallel test execution optimization
- **NEW**: Environment setup time optimization

### NEW: Test Consistency Evolution

**Short-term Improvements (Next Release):**
- Integration with GitHub Actions for automatic hook validation
- Pre-commit hook performance optimization (target: < 15 seconds)
- Enhanced Docker test runner with ARM64 support
- Test result caching for faster repeated runs

**Medium-term Improvements (6 months):**
- Automated test environment provisioning
- Integration test data factory for consistent test datasets
- Performance regression detection with historical trending
- Cross-environment test result comparison

**Long-term Vision (1 year):**
- AI-powered test case generation based on code changes
- Predictive test failure analysis
- Automatic environment recovery and healing
- Test coverage gap analysis and recommendations

## Quick Reference

### Most Common Test Commands

#### Daily Development Testing
```bash
# NEW: Standardized pre-commit validation
./scripts/pre_commit_validation.sh --fast      # Quick validation (30s)

# Traditional unit and integration tests
pytest tests/ -x --tb=short                    # Quick unit tests
./scripts/run_integration_test.sh --quick      # Quick integration
python3 scripts/test_mcp_tools.py              # MCP tools test
```

#### Before PR Submission
```bash
# NEW: Full pre-commit validation with auto-fix
./scripts/pre_commit_validation.sh --fix       # Auto-fix + full validation

# NEW: Docker CI parity testing
./scripts/docker_test_runner.sh --mode fast-check  # Matches CI exactly

# Traditional comprehensive testing
pytest tests/ --cov=fast_intercom_mcp         # Full unit tests
./scripts/run_integration_test.sh             # Full integration
./scripts/test_docker_install.sh              # Docker test
```

#### Before Release
```bash
# NEW: Performance testing with Docker parity
./scripts/docker_test_runner.sh --mode performance --performance-report

# Traditional performance and integration testing
./scripts/run_integration_test.sh --performance-report  # With metrics
./scripts/test_docker_install.sh --with-api-test        # Full Docker test
python3 scripts/test_mcp_tools.py --verbose --output mcp_results.json
```

### NEW: Test Consistency Commands

#### Environment Detection and Setup
```bash
# Detect current environment
./scripts/pre_commit_validation.sh --verbose | head -20

# Verify all tools are available
command -v poetry ruff mypy pytest docker

# Environment-specific setup
poetry install                    # Poetry projects
source venv/bin/activate && pip install -e .  # venv projects
```

#### Quick Quality Checks
```bash
# Fast pre-commit check (< 30 seconds)
./scripts/pre_commit_validation.sh --fast

# Auto-fix common issues
./scripts/pre_commit_validation.sh --fix

# Docker CI parity check (< 2 minutes)
./scripts/docker_test_runner.sh --mode fast-check
```

#### Comprehensive Validation
```bash
# Full local validation
./scripts/pre_commit_validation.sh --verbose

# Full Docker integration test
./scripts/docker_test_runner.sh --mode integration --api-test

# Performance benchmarking
./scripts/docker_test_runner.sh --mode performance --performance-report --output perf.json
```

### Emergency Test Commands

#### Quick Health Checks
```bash
# Test if server is functional
fast-intercom-mcp status

# NEW: Quick import and CLI validation
./scripts/pre_commit_validation.sh --fast --no-cli-check --skip-tests

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

#### Emergency Environment Recovery
```bash
# NEW: Environment detection and recovery
./scripts/pre_commit_validation.sh --verbose 2>&1 | grep "Environment:\|Python:\|Error:"

# Reinstall in current environment
if command -v poetry >/dev/null 2>&1; then
    poetry install --no-cache
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate && pip install -e . --force-reinstall
else
    python3 -m pip install --user -e . --force-reinstall
fi

# Verify recovery
python3 -c "import fast_intercom_mcp; print('✅ Package recovered')"
```

#### Emergency Docker Testing
```bash
# NEW: Quick Docker-based validation (bypasses local environment issues)
./scripts/docker_test_runner.sh --mode fast-check --clean-build

# Docker-based integration test (if local environment is broken)
./scripts/docker_test_runner.sh --mode quick-test --api-test --verbose
```

---

## Summary: Enhanced Testing Paradigm

The FastIntercom MCP project now implements a **comprehensive test consistency framework** that ensures reliable, reproducible testing across all development environments and deployment scenarios.

### Key Innovations

**🔄 Test Consistency Tools:**
- Automatic environment detection (Poetry, venv, system Python)
- Standardized validation sequences with intelligent error handling
- Cross-platform compatibility with uniform behavior

**🐳 Local CI Mirror Testing:**
- Docker-based testing that exactly matches GitHub Actions environment
- Multiple test modes from fast checks (2 min) to performance testing (45 min)
- Environment parity ensures local tests predict CI results

**⚡ Pre-commit Integration:**
- Smart pre-commit validation with auto-fix capabilities
- Git hook integration for automatic quality enforcement
- Fast mode optimized for development workflow (< 30 seconds)

**📊 Performance and Quality Tracking:**
- Comprehensive result reporting with JSON output
- Performance benchmarking with historical tracking capability
- Quality gate enforcement at development, PR, and release stages

### Migration Guide

**For Existing Developers:**
```bash
# Install new pre-commit hook
cp scripts/example-pre-commit-hook .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Replace old validation commands with new standardized tools
# OLD: pytest tests/ && ruff check .
# NEW: ./scripts/pre_commit_validation.sh --fast

# Replace Docker testing with CI parity testing
# OLD: ./scripts/test_docker_install.sh
# NEW: ./scripts/docker_test_runner.sh --mode fast-check
```

**For New Contributors:**
1. Read this testing guide completely
2. Install and test pre-commit hook
3. Run `./scripts/pre_commit_validation.sh --verbose` to verify environment
4. Use Docker testing for complex validation: `./scripts/docker_test_runner.sh --mode integration --api-test`

This enhanced testing framework ensures that **every commit maintains quality**, **every PR is properly validated**, and **every release meets performance targets** through consistent, automated, and comprehensive testing procedures.

---

*This testing guide ensures comprehensive validation of the FastIntercom MCP server across all deployment scenarios and use cases with enhanced consistency and reliability.*