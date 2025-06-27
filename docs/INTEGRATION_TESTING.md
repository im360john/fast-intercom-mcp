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

# Expected output:
# 🔍 Testing FastIntercom MCP Integration
# ✅ API Connection: Connected to workspace 'Your Workspace'
# ✅ Database: Initialized successfully
# ✅ Sync: 1,247 conversations (7 days)
# ✅ Performance: 23.4 conv/sec, 47ms avg response
# ✅ Queries: All MCP tools working correctly
# ✅ Memory: 73MB peak usage
# 
# Integration test PASSED ✅
```

#### Extended Integration Test
```bash
# Test with larger dataset (30 days)
./scripts/run_integration_test.sh --days 30

# Test with custom conversation limit
./scripts/run_integration_test.sh --days 7 --max-conversations 500

# Test with performance monitoring
./scripts/run_integration_test.sh --performance-report
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

# Check workflow status
gh run list --workflow=integration-test.yml --limit=5

# View detailed logs
gh run view $(gh run list --workflow=integration-test.yml --limit=1 --json databaseId --jq '.[0].databaseId')
```

#### Workflow Configuration
The integration test workflow performs these steps:
1. Set up Python 3.11 environment
2. Install dependencies
3. Configure Intercom API token (from secrets)
4. Run integration test suite
5. Upload test results and logs
6. Report status to PR (if applicable)

#### Expected GitHub Actions Results
```yaml
# Successful run indicators
✅ Set up Python 3.11
✅ Install dependencies  
✅ Configure API credentials
✅ Run integration tests
   - API Connection: PASSED
   - Data Sync: PASSED (1,247 conversations)
   - MCP Server: PASSED (all tools working)
   - Performance: PASSED (25.3 conv/sec)
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
# 🐳 Testing Docker Clean Install
# ✅ Building Docker image...
# ✅ Starting container...
# ✅ Testing CLI functionality...
# ✅ Testing MCP server startup...
# ✅ Basic functionality verified
# 
# Docker test PASSED ✅
```

#### Docker Test with API Integration
```bash
# Test with real API data
./scripts/test_docker_install.sh --with-api-test

# Test with custom configuration
./scripts/test_docker_install.sh --config ./test-configs/docker-test.json
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

#### Sync Performance
- **Conversation Sync Speed**: 10-50 conversations/second
- **Message Processing**: 50-200 messages/second
- **API Rate Limit Handling**: No 429 errors during normal operation
- **Database Write Speed**: 100+ conversations/second to SQLite

#### Response Performance
- **Cached Query Response**: <100ms for conversation searches
- **Individual Conversation**: <50ms for cached conversations
- **Server Status Query**: <10ms for status information
- **MCP Tool Response**: <200ms for complex searches

#### Resource Usage
- **Memory Usage**: <100MB during sync operations
- **Peak Memory**: <150MB during large dataset sync
- **Disk I/O**: Efficient SQLite operations
- **Network Usage**: Optimized API calls with batching

### Performance Monitoring

#### During Integration Tests
```bash
# Monitor performance during test
./scripts/run_integration_test.sh --performance-report

# Output includes:
# Performance Metrics:
# ├── Sync Speed: 23.4 conversations/sec
# ├── Query Response: 47ms average
# ├── Memory Usage: 73MB peak
# ├── Database Size: 45MB (1,247 conversations)
# └── API Efficiency: 1.2 calls per conversation
```

#### Performance Test Script
```bash
# Dedicated performance test
./scripts/run_performance_test.sh

# With detailed profiling
./scripts/run_performance_test.sh --profile --output perftest_results.json
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
🔍 FastIntercom MCP Integration Test Report
================================================================================

Environment:
├── Python Version: 3.11.5
├── Package Version: 0.4.0-dev
├── Test Workspace: ~/.fast-intercom-mcp-test
└── API Workspace: YourCompany (workspace_id: abc123)

API Connection:
├── Status: ✅ Connected
├── Permissions: ✅ conversations:read, contacts:read
├── Rate Limits: ✅ 1000/hour remaining
└── Response Time: 145ms average

Data Sync:
├── Date Range: 2024-06-20 to 2024-06-27 (7 days)
├── Conversations: ✅ 1,247 synced successfully
├── Messages: ✅ 5,832 messages processed
├── Customers: ✅ 891 unique customers
├── Sync Speed: ✅ 23.4 conversations/second
├── API Calls: ✅ 1,502 calls (1.2 per conversation)
└── Duration: ✅ 53.2 seconds

Data Integrity:
├── Conversation IDs: ✅ All unique, no duplicates
├── Message Threading: ✅ All threads complete
├── Timestamps: ✅ All in correct chronological order
├── Customer Links: ✅ All conversations linked to customers
└── Schema Validation: ✅ All data matches expected schema

MCP Server:
├── Startup: ✅ Started in 2.3 seconds
├── Tool Registration: ✅ 4 tools registered
├── search_conversations: ✅ 15 test queries successful
├── get_conversation: ✅ 10 individual retrievals successful
├── get_server_status: ✅ Status reporting functional
└── sync_conversations: ✅ Manual sync triggers working

Performance:
├── Query Response: ✅ 47ms average (target: <100ms)
├── Memory Usage: ✅ 73MB peak (target: <100MB)
├── Database Size: ✅ 45MB (1.8KB per conversation)
├── CPU Usage: ✅ <5% during queries
└── Disk I/O: ✅ Efficient SQLite operations

Cleanup:
├── MCP Server: ✅ Stopped gracefully
├── Database: ✅ Closed properly
├── Temp Files: ✅ All cleaned up
└── Memory: ✅ Fully released

================================================================================
Integration Test Result: ✅ PASSED
Test Duration: 1m 23s
Report Generated: 2024-06-27 14:35:22 UTC
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