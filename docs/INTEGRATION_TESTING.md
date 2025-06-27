# Integration Testing Procedures

## Purpose

This document provides detailed procedures for running integration tests that verify end-to-end functionality with real Intercom API data. Integration testing is critical for validating that the FastIntercom MCP server correctly syncs, stores, and serves conversation data from Intercom.

## Prerequisites

### Required Components
- **Python 3.11+** environment
- **Intercom API credentials** with appropriate permissions
- **Docker** (for deployment tests)
- **Network connectivity** to Intercom API
- **Sufficient disk space** (minimum 1GB for test data)

### Intercom API Requirements
Your Intercom access token must have these permissions:
- `conversations:read` - Read conversation data
- `contacts:read` - Read customer information
- `teams:read` - Read team/admin information (optional)

### Environment Setup
```bash
# Required environment variables
export INTERCOM_ACCESS_TOKEN=your_access_token_here

# Optional configuration
export FASTINTERCOM_TEST_LOG_LEVEL=INFO
export FASTINTERCOM_TEST_TIMEOUT=300
export FASTINTERCOM_TEST_WORKSPACE=~/.fast-intercom-mcp-test
```

### Verification Commands
```bash
# 1. Verify Python environment
python3 --version  # Should be 3.11+
python3 -c "import fast_intercom_mcp; print('✅ Package imported')"

# 2. Verify Intercom API access
curl -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
     -H "Accept: application/json" \
     https://api.intercom.io/me

# 3. Verify Docker (if running Docker tests)
docker --version
docker run hello-world
```

## Test Scenarios

### 1. Local Integration Test

**Purpose**: Validate complete sync and query functionality in local environment  
**Duration**: 2-5 minutes  
**Scope**: Last 7 days of conversation data  

#### Quick Integration Test
```bash
# Run with default settings (7 days)
./scripts/run_integration_test.sh

# Quick test mode (1 day, 100 conversations max)
./scripts/run_integration_test.sh --quick

# Expected output:
# 🔍 FastIntercom MCP Integration Test v1.0.0
# ===============================================
# ℹ️  Test workspace: /Users/username/.fast-intercom-mcp-test-1234567890
# ✅ Connected to workspace: Your Workspace Name
# ✅ Database initialized successfully (4 tables)
# ✅ Sync completed: 1,247 conversations, 5,832 messages
# ℹ️  Sync duration: 53s (23.4 conv/sec)
# ✅ MCP server started (PID: 12345)
# ✅ MCP tools test: 4/4 tools passed
# ✅ All performance targets met
# 
# Integration test PASSED ✅
```

#### Extended Integration Test
```bash
# Test with larger dataset (30 days)
./scripts/run_integration_test.sh --days 30

# Test with custom conversation limit
./scripts/run_integration_test.sh --days 7 --max-conversations 500

# Test with performance monitoring and output file
./scripts/run_integration_test.sh --performance-report --output integration_results.json

# Debug test with verbose output and preserved environment
./scripts/run_integration_test.sh --verbose --no-cleanup
```

#### Integration Test Steps (Detailed)
1. **Environment Verification**
   - Check API token validity
   - Verify required Python packages
   - Create temporary test workspace

2. **API Connection Test**
   - Test basic connectivity
   - Verify workspace permissions
   - Validate token scopes

3. **Database Initialization**
   - Create temporary database
   - Initialize schema
   - Verify table structure

4. **Data Sync Test**
   - Sync specified date range
   - Track sync performance metrics
   - Verify data integrity

5. **MCP Server Test**
   - Start MCP server in test mode
   - Test all available tools
   - Verify response formats

6. **Query Validation**
   - Test conversation search
   - Test individual conversation retrieval
   - Test server status queries

7. **Performance Measurement**
   - Measure sync speed (conversations/second)
   - Measure query response times
   - Monitor memory usage

8. **Cleanup**
   - Stop MCP server
   - Remove temporary data
   - Generate test report

### 2. GitHub Actions Integration

**Purpose**: Automated integration testing in CI/CD pipeline  
**Duration**: 5-15 minutes  
**Trigger**: Manual or scheduled  

#### Manual Trigger
```bash
# Trigger from command line
gh workflow run integration-test.yml

# Trigger with custom sync days
gh workflow run integration-test.yml -f sync_days=30 -f run_full_test=true

# Check workflow status
gh run list --workflow=integration-test.yml --limit=5

# View detailed logs
gh run view $(gh run list --workflow=integration-test.yml --limit=1 --json databaseId --jq '.[0].databaseId')
```

#### Workflow Configuration
The integration test workflow (`integration-test.yml`) performs these steps:
1. Set up Python 3.11 environment with pip caching
2. Install system dependencies (sqlite3)
3. Install Python dependencies and package
4. Configure Intercom API token (from GitHub secrets)
5. Create isolated test environment
6. Run comprehensive integration test with real API data
7. Generate performance metrics and test summary
8. Upload test artifacts (results, logs, database snapshots)
9. Comment on PR with test results (if applicable)

#### Expected GitHub Actions Results
```yaml
# Successful workflow run
✅ Checkout code
✅ Set up Python 3.11
✅ Install system dependencies
✅ Install Python dependencies
✅ Verify package installation
✅ Create test environment
✅ Run integration test
   - Package import: PASSED
   - Database initialization: PASSED
   - API connection: PASSED
   - Sync operation: PASSED (1,247 conversations, 30 days)
   - Performance metrics: PASSED (25.3 conv/sec)
✅ Generate test summary
✅ Upload test artifacts
```

### 3. Docker Clean Install Test

**Purpose**: Validate deployment in clean Docker environment  
**Duration**: 5-15 minutes  
**Scope**: Complete installation and basic functionality  

#### Basic Docker Test
```bash
# Test Docker build and basic functionality
./scripts/test_docker_install.sh

# Expected output:
# 🐳 FastIntercom MCP Docker Test v1.0.0
# ===============================================
# ℹ️  Docker version: Docker version 24.0.2
# ℹ️  Building image: fast-intercom-mcp:test
# ✅ Docker image built successfully: fast-intercom-mcp:test
# ℹ️  Image size: 892MB
# ✅ Container started successfully
# ✅ CLI help command: PASSED
# ✅ CLI init command: PASSED
# ✅ MCP server startup: PASSED
# 
# Docker test PASSED ✅
```

#### Docker Test with API Integration
```bash
# Test with real API data
./scripts/test_docker_install.sh --with-api-test

# Test with custom configuration
./scripts/test_docker_install.sh --config ./test-configs/docker-test.json

# Debug Docker issues with container preservation
./scripts/test_docker_install.sh --debug --keep-container
```

#### Docker Test Steps (Detailed)
1. **Image Build Test**
   - Build Docker image from Dockerfile
   - Verify all dependencies installed
   - Check final image size

2. **Container Startup Test**
   - Start container with test configuration
   - Verify all services start correctly
   - Check for any startup errors

3. **CLI Functionality Test**
   - Test all CLI commands
   - Verify help output
   - Test configuration commands

4. **MCP Server Test**
   - Start MCP server in container
   - Test protocol communication
   - Verify all tools are available

5. **API Integration Test** (if enabled)
   - Configure API credentials
   - Run basic sync test
   - Verify data persistence

6. **Cleanup Test**
   - Stop all services gracefully
   - Verify clean shutdown
   - Test container restart

## Performance Benchmarks

### Expected Performance Targets

#### Sync Performance (Implemented Targets)
- **Conversation Sync Speed**: 10+ conversations/second (configurable target)
- **Message Processing**: Efficient batch processing with Intercom API
- **API Rate Limit Handling**: Built-in rate limiting and retry logic
- **Database Operations**: SQLite with optimized schema and indexes

#### Response Performance (Measured by Integration Test)
- **CLI Status Command**: <100ms average response time
- **Database Queries**: Fast SQLite operations with proper indexing
- **Server Startup**: <3 seconds for MCP server initialization
- **Tool Response**: Varies by data size and query complexity

#### Resource Usage (Monitored)
- **Memory Usage**: <100MB target during normal operations
- **Database Growth**: Approximately 1.8KB per conversation average
- **Disk Space**: Efficient storage with SQLite database
- **Network Usage**: Optimized Intercom API calls with pagination

### Performance Monitoring

#### During Integration Tests
```bash
# Monitor performance during test
./scripts/run_integration_test.sh --performance-report

# Output includes performance metrics in JSON format:
# {
#   "sync_performance": {
#     "conversations_synced": 1247,
#     "messages_synced": 5832,
#     "duration_seconds": 53,
#     "conversations_per_second": 23.4
#   },
#   "query_performance": {
#     "average_response_time_ms": 47
#   },
#   "resource_usage": {
#     "memory_usage_mb": 73,
#     "database_size_mb": 45
#   }
# }
```

#### MCP Tools Performance Test
```bash
# Test MCP tool response times
python3 scripts/test_mcp_tools.py --verbose

# Save detailed results with timing
python3 scripts/test_mcp_tools.py --output mcp_performance.json

# Test specific tools for performance
python3 scripts/test_mcp_tools.py --tool search_conversations --timeout 60
```

### Performance Troubleshooting

#### Slow Sync Performance
```bash
# Diagnose sync speed issues
./scripts/diagnose_sync_performance.sh

# Check API response times
./scripts/measure_api_latency.sh

# Profile database operations
./scripts/profile_database_performance.sh
```

#### High Memory Usage
```bash
# Monitor memory during sync
./scripts/monitor_memory_usage.sh &
./scripts/run_integration_test.sh
pkill -f monitor_memory_usage

# Analyze memory patterns
./scripts/analyze_memory_profile.sh
```

## Interpreting Results

### Success Criteria

#### ✅ Complete Success
All these conditions must be met:
- API connection established successfully
- Data sync completes without errors
- All synced data passes integrity checks
- MCP server responds to all tool requests
- Performance targets met (see benchmarks above)
- No memory leaks or resource issues
- Clean shutdown and cleanup

#### ⚠️ Partial Success (Needs Investigation)
Some tests pass but with warnings:
- Sync completed but performance below targets
- Some API calls failed but retries succeeded
- Memory usage higher than expected but stable
- Minor data integrity issues in edge cases

#### ❌ Failure (Requires Fix)
Critical issues that prevent normal operation:
- API connection failures
- Data corruption or sync errors
- MCP server crashes or hangs
- Performance significantly below targets
- Memory leaks or resource exhaustion
- Database integrity failures

### Result Analysis

#### Successful Integration Test Output
```
🔍 FastIntercom MCP Integration Test v1.0.0
================================================================================

Environment:
├── Python Version: 3.11.5
├── Package Available: true
├── Test Workspace: ~/.fast-intercom-mcp-test-1234567890
└── CLI Available: fast-intercom-mcp

API Connection:
├── Status: ✅ Connected to workspace: YourCompany
├── Authentication: ✅ Valid token
├── Connectivity: ✅ HTTPS API access working
└── Test Result: PASSED

Data Sync:
├── Sync Duration: 53s
├── Conversations: ✅ 1,247 synced successfully
├── Messages: ✅ 5,832 messages processed
├── Sync Speed: ✅ 23.4 conversations/second
├── Data Verification: ✅ 1,247 conversations stored in database
└── Test Result: PASSED

Database Integrity:
├── Database Schema: ✅ 4 tables created successfully
├── Data Storage: ✅ All synced data properly stored
├── SQLite Operations: ✅ No corruption detected
└── Test Result: PASSED

MCP Server:
├── Startup: ✅ Started successfully (PID: 12345)
├── Tool Testing: ✅ 4/4 tools passed
├── Server Status: ✅ Status command working
├── Process Health: ✅ Server running stably
└── Test Result: PASSED

Performance:
├── Sync Speed: ✅ 23.4 conv/sec (target: >10)
├── Response Time: ✅ 47ms average (target: <100ms)
├── Memory Usage: ✅ 73MB (target: <100MB)
├── Database Size: ✅ 45MB
└── Test Result: PASSED

Test Results:
================================================================================
Test Duration: 83s
Tests Passed: 5/5

✅ api_connection: PASSED
✅ database_init: PASSED  
✅ data_sync: PASSED
✅ mcp_server: PASSED
✅ performance: PASSED

================================================================================
Integration test PASSED ✅
================================================================================
```

#### Failure Analysis Example
```
🔍 FastIntercom MCP Integration Test Report
================================================================================
Integration Test Result: ❌ FAILED

Failures:
├── API Connection: ❌ 401 Unauthorized
│   └── Cause: Invalid or expired access token
├── Data Sync: ❌ Skipped due to API failure
└── MCP Server: ❌ Skipped due to data unavailability

Required Actions:
1. Verify INTERCOM_ACCESS_TOKEN is correct
2. Check token permissions include 'conversations:read'
3. Confirm token hasn't expired
4. Test API access manually: curl -H "Authorization: Bearer $TOKEN" https://api.intercom.io/me

================================================================================
```

### Common Result Patterns

#### Slow Performance Results
```
Performance Issues Detected:
├── Sync Speed: ⚠️ 8.2 conversations/sec (target: >10)
├── Query Response: ⚠️ 156ms average (target: <100ms)
└── Memory Usage: ✅ 67MB peak

Recommended Actions:
├── Check network latency to Intercom API
├── Verify database isn't on slow storage
├── Consider reducing sync batch size
└── Monitor for background processes affecting performance
```

#### Data Integrity Issues
```
Data Integrity Warnings:
├── Missing Messages: ⚠️ 12 conversations have incomplete message threads
├── Timestamp Issues: ⚠️ 3 messages with future timestamps
└── Customer Links: ⚠️ 45 conversations missing customer email

Investigation Required:
├── Check Intercom API pagination handling
├── Verify message retrieval logic
└── Review customer data mapping
```

## Troubleshooting Guide

### API Connection Issues

#### 401 Unauthorized
```bash
# Verify token
curl -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
     https://api.intercom.io/me

# Check token permissions
# Token must have 'conversations:read' permission
```

#### 429 Rate Limited
```bash
# Check current rate limits
curl -I -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
     https://api.intercom.io/conversations

# Look for headers:
# X-RateLimit-Limit: 1000
# X-RateLimit-Remaining: 950
```

#### Network Connectivity
```bash
# Test basic connectivity
ping api.intercom.io

# Test HTTPS connectivity
curl -I https://api.intercom.io/

# Check for proxy issues
echo $HTTP_PROXY $HTTPS_PROXY
```

### Sync Performance Issues

#### Slow Sync Speed
```bash
# Profile sync performance
./scripts/profile_sync_performance.sh

# Check database performance
./scripts/test_database_performance.sh

# Monitor network during sync
./scripts/monitor_network_during_sync.sh
```

#### Memory Issues
```bash
# Monitor memory usage
./scripts/monitor_memory_usage.sh &
./scripts/run_integration_test.sh
pkill -f monitor_memory_usage

# Check for memory leaks
./scripts/check_memory_leaks.sh
```

### Database Issues

#### Database Locked
```bash
# Find processes using database
lsof ~/.fast-intercom-mcp-test/data.db

# Kill interfering processes
pkill -f fast-intercom-mcp

# Verify database integrity
sqlite3 ~/.fast-intercom-mcp-test/data.db "PRAGMA integrity_check;"
```

#### Schema Errors
```bash
# Check database schema
sqlite3 ~/.fast-intercom-mcp-test/data.db .schema

# Reset database if corrupted
rm ~/.fast-intercom-mcp-test/data.db
fast-intercom-mcp init --test-mode
```

### MCP Server Issues

#### Server Won't Start
```bash
# Check port availability
netstat -an | grep :3000

# Test server startup manually
fast-intercom-mcp start --test-mode --verbose

# Check logs
tail -f ~/.fast-intercom-mcp-test/logs/fast-intercom-mcp.log
```

#### Tool Failures
```bash
# Test individual MCP tools
python3 scripts/test_mcp_tools.py --tool search_conversations
python3 scripts/test_mcp_tools.py --tool get_conversation
```

## Advanced Testing Scenarios

### Load Testing
```bash
# Test with large dataset
./scripts/run_integration_test.sh --days 90 --max-conversations 10000

# Concurrent client testing
./scripts/test_concurrent_clients.sh --clients 5
```

### Failure Recovery Testing
```bash
# Test network interruption recovery
./scripts/test_network_interruption.sh

# Test database corruption recovery
./scripts/test_database_recovery.sh
```

### Cross-Platform Testing
```bash
# Test on different Python versions
pyenv local 3.11.0 && ./scripts/run_integration_test.sh
pyenv local 3.12.0 && ./scripts/run_integration_test.sh

# Test on different operating systems
./scripts/test_cross_platform.sh
```

## Integration Test Maintenance

### Updating Test Data Ranges
When conversation volume changes, adjust test parameters:

```bash
# Update default test range in scripts
# Edit scripts/run_integration_test.sh
DEFAULT_DAYS=7  # Adjust based on typical conversation volume

# Update performance targets if needed
# Edit tests/config.json performance section
```

### Adding New Test Scenarios
```bash
# Create new integration test
cp scripts/run_integration_test.sh scripts/run_custom_test.sh
# Modify for specific scenario
```

### Monitoring Test Health
```bash
# Weekly integration test health check
./scripts/weekly_integration_check.sh

# Generate integration test report
./scripts/generate_integration_report.sh --last-30-days
```

This comprehensive integration testing guide ensures that future agents and deployers can confidently validate the FastIntercom MCP server's functionality across all deployment scenarios.