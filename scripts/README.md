# Testing Scripts Documentation

## Overview

This directory contains all testing scripts for the FastIntercom MCP server. These scripts automate various testing scenarios from basic functionality checks to comprehensive integration testing.

## Script Categories

### Integration Test Scripts
- `run_integration_test.sh` - Main integration test runner with comprehensive API testing
- `test_docker_install.sh` - Docker deployment and clean install testing
- `test_mcp_tools.py` - MCP protocol tool testing and validation

### Monitoring Scripts
Note: Performance monitoring is integrated into the main integration test script.
- Performance metrics are captured during `run_integration_test.sh --performance-report`
- MCP tool performance is measured by `test_mcp_tools.py`
- Docker resource usage is monitored by `test_docker_install.sh`

### Utility Scripts
Note: Cleanup and reporting are integrated into the main test scripts.
- Test environment cleanup is handled automatically by each script
- Database validation is built into the integration test
- Test reporting is included in script outputs and optional JSON files

## Script Details

### run_integration_test.sh

**Purpose**: Complete integration test with real Intercom API  
**Usage**: `./scripts/run_integration_test.sh [OPTIONS]`

**Options**:
- `--days N` - Number of days to sync (default: 7)
- `--max-conversations N` - Limit conversations synced (default: 1000)
- `--performance-report` - Generate detailed performance metrics in JSON
- `--quick` - Fast test with minimal data (1 day, 100 conversations)
- `--verbose` - Enable debug logging
- `--output FILE` - Save results to JSON file
- `--no-cleanup` - Don't clean up test environment (for debugging)
- `--help` - Show detailed usage information

**Examples**:
```bash
# Quick 7-day integration test
./scripts/run_integration_test.sh

# Quick functionality check (1 day, 100 conversations)
./scripts/run_integration_test.sh --quick

# Extended test with performance monitoring
./scripts/run_integration_test.sh --days 30 --performance-report

# Debug test with verbose output and preserved environment
./scripts/run_integration_test.sh --verbose --no-cleanup

# Save detailed results to file
./scripts/run_integration_test.sh --performance-report --output integration_results.json
```

**Exit Codes**:
- `0` - All tests passed
- `1` - API connection failed
- `2` - Sync operation failed
- `3` - MCP server test failed
- `4` - Performance targets not met
- `5` - Environment setup failed

### test_docker_install.sh

**Purpose**: Test clean Docker installation and deployment  
**Usage**: `./scripts/test_docker_install.sh [OPTIONS]`

**Options**:
- `--with-api-test` - Include real API integration testing
- `--config FILE` - Use custom configuration file
- `--debug` - Enable debug mode with verbose output
- `--keep-container` - Don't remove test container after completion
- `--help` - Show detailed usage information

**Examples**:
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

### Performance Testing

**Note**: Performance testing is integrated into the main integration test script.

**Performance Monitoring**: Use `run_integration_test.sh --performance-report`  
**MCP Performance**: Use `test_mcp_tools.py --verbose`  
**Docker Performance**: Use `test_docker_install.sh` with resource monitoring  

**Examples**:
```bash
# Integration test with performance metrics
./scripts/run_integration_test.sh --performance-report --output perf_results.json

# MCP tools performance testing
python3 scripts/test_mcp_tools.py --verbose --output mcp_performance.json

# Docker test with debug info
./scripts/test_docker_install.sh --debug
```

### test_mcp_tools.py

**Purpose**: Test individual MCP protocol tools  
**Usage**: `python3 scripts/test_mcp_tools.py [OPTIONS]`

**Options**:
- `--tool TOOL_NAME` - Test specific tool only
- `--server-url URL` - MCP server URL (default: stdio)
- `--timeout SECONDS` - Request timeout in seconds (default: 30)
- `--verbose` - Enable verbose output with detailed responses
- `--output FILE` - Save results to JSON file
- `--help` - Show detailed usage information

**Examples**:
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

### Performance Monitoring

**Purpose**: Performance monitoring is integrated into test scripts  
**Usage**: Built into existing test scripts

**Available Monitoring**:
- Integration test performance: `--performance-report` flag
- MCP tools timing: Built into `test_mcp_tools.py`
- Docker resource usage: Built into `test_docker_install.sh --debug`

**Examples**:
```bash
# Monitor performance during integration test
./scripts/run_integration_test.sh --performance-report

# Monitor MCP tools performance
python3 scripts/test_mcp_tools.py --verbose

# Monitor Docker resource usage
./scripts/test_docker_install.sh --debug
```

### Database Validation

**Purpose**: Database validation is integrated into integration test  
**Usage**: Built into `run_integration_test.sh`

**Available Validation**:
- Schema verification: Automatic during database initialization test
- Data integrity: Automatic during sync verification
- Storage validation: Automatic conversation and message count checks

**Manual Database Checks**:
```bash
# Check database integrity via SQLite
sqlite3 ~/.fast-intercom-mcp/data.db "PRAGMA integrity_check;"

# View database statistics
sqlite3 ~/.fast-intercom-mcp/data.db "SELECT COUNT(*) FROM conversations;"

# Run integration test with database validation
./scripts/run_integration_test.sh --verbose
```

## Script Implementation Examples

### Integration Test Script Template

```bash
#!/bin/bash
# run_integration_test.sh - Integration test runner

set -e  # Exit on any error

# Default configuration
DAYS=7
MAX_CONVERSATIONS=1000
PERFORMANCE_REPORT=false
QUICK_MODE=false
VERBOSE=false

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --max-conversations)
            MAX_CONVERSATIONS="$2"
            shift 2
            ;;
        --performance-report)
            PERFORMANCE_REPORT=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            DAYS=1
            MAX_CONVERSATIONS=100
            shift
            ;;
        --verbose)
            VERBOSE=true
            export FASTINTERCOM_LOG_LEVEL=DEBUG
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Test environment setup
setup_test_environment() {
    echo "🔍 Setting up test environment..."
    
    # Create test workspace
    export FASTINTERCOM_CONFIG_DIR=~/.fast-intercom-mcp-test
    mkdir -p "$FASTINTERCOM_CONFIG_DIR"
    
    # Verify API token
    if [[ -z "$INTERCOM_ACCESS_TOKEN" ]]; then
        echo "❌ INTERCOM_ACCESS_TOKEN not set"
        exit 1
    fi
    
    # Test API connectivity
    if ! curl -s -H "Authorization: Bearer $INTERCOM_ACCESS_TOKEN" \
            https://api.intercom.io/me > /dev/null; then
        echo "❌ API connection failed"
        exit 1
    fi
    
    echo "✅ Test environment ready"
}

# Run integration test
run_integration_test() {
    echo "🔍 Running integration test..."
    
    # Initialize test database
    fast-intercom-mcp init --force
    
    # Run sync test
    start_time=$(date +%s)
    fast-intercom-mcp sync --force --days "$DAYS" \
        --max-conversations "$MAX_CONVERSATIONS"
    end_time=$(date +%s)
    
    sync_duration=$((end_time - start_time))
    echo "✅ Sync completed in ${sync_duration}s"
    
    # Test MCP server
    fast-intercom-mcp start --test-mode &
    server_pid=$!
    sleep 3
    
    # Test MCP tools
    python3 scripts/test_mcp_tools.py
    
    # Clean up
    kill $server_pid 2>/dev/null || true
    
    echo "✅ Integration test completed"
}

# Generate performance report
generate_performance_report() {
    if [[ "$PERFORMANCE_REPORT" == "true" ]]; then
        echo "📊 Generating performance report..."
        python3 scripts/generate_performance_report.py
    fi
}

# Cleanup test environment
cleanup_test_environment() {
    rm -rf ~/.fast-intercom-mcp-test
    echo "✅ Cleanup completed"
}

# Main execution
main() {
    echo "🔍 FastIntercom MCP Integration Test"
    echo "=================================================================================="
    
    setup_test_environment
    run_integration_test
    generate_performance_report
    cleanup_test_environment
    
    echo "🎉 Integration test PASSED"
}

# Execute main function
main "$@"
```

### MCP Tools Test Script Template

```python
#!/usr/bin/env python3
"""
test_mcp_tools.py - MCP protocol tool testing
"""

import asyncio
import json
import sys
import time
from typing import Any, Dict, List

# Test configuration
TEST_QUERIES = [
    {
        "tool": "search_conversations",
        "arguments": {
            "query": "billing",
            "timeframe": "last 7 days",
            "limit": 10
        },
        "expected_keys": ["conversations", "total_count"]
    },
    {
        "tool": "get_server_status",
        "arguments": {},
        "expected_keys": ["status", "conversation_count", "last_sync"]
    },
    {
        "tool": "get_conversation",
        "arguments": {
            "conversation_id": "test_conversation_id"
        },
        "expected_keys": ["conversation", "messages"]
    }
]

class MCPToolTester:
    """MCP tool testing class."""
    
    def __init__(self, server_url: str = "http://localhost:3000"):
        self.server_url = server_url
        self.results = []
    
    async def test_tool(self, tool_name: str, arguments: Dict[str, Any], 
                       expected_keys: List[str]) -> Dict[str, Any]:
        """Test individual MCP tool."""
        start_time = time.time()
        
        try:
            # Mock MCP call - replace with actual MCP client implementation
            result = await self._call_mcp_tool(tool_name, arguments)
            
            # Validate response structure
            validation_errors = []
            for key in expected_keys:
                if key not in result:
                    validation_errors.append(f"Missing key: {key}")
            
            duration = time.time() - start_time
            
            return {
                "tool": tool_name,
                "status": "PASSED" if not validation_errors else "FAILED",
                "duration_ms": round(duration * 1000, 2),
                "validation_errors": validation_errors,
                "result_size": len(json.dumps(result))
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                "tool": tool_name,
                "status": "ERROR",
                "duration_ms": round(duration * 1000, 2),
                "error": str(e),
                "result_size": 0
            }
    
    async def _call_mcp_tool(self, tool_name: str, 
                           arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Mock MCP tool call - implement actual MCP client here."""
        # This would use the actual MCP client library
        # For now, return mock success response
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if tool_name == "search_conversations":
            return {
                "conversations": [
                    {"id": "conv_1", "summary": "Test conversation"}
                ],
                "total_count": 1
            }
        elif tool_name == "get_server_status":
            return {
                "status": "active",
                "conversation_count": 1247,
                "last_sync": "2024-06-27T14:35:22Z"
            }
        elif tool_name == "get_conversation":
            return {
                "conversation": {"id": arguments["conversation_id"]},
                "messages": []
            }
        
        return {}
    
    async def run_all_tests(self) -> bool:
        """Run all MCP tool tests."""
        print("🔍 Testing MCP Tools")
        print("=" * 50)
        
        all_passed = True
        
        for test_config in TEST_QUERIES:
            result = await self.test_tool(
                test_config["tool"],
                test_config["arguments"],
                test_config["expected_keys"]
            )
            
            self.results.append(result)
            
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            print(f"{status_icon} {result['tool']}: {result['status']} "
                  f"({result['duration_ms']}ms)")
            
            if result["status"] != "PASSED":
                all_passed = False
                if "validation_errors" in result:
                    for error in result["validation_errors"]:
                        print(f"   └── {error}")
                if "error" in result:
                    print(f"   └── Error: {result['error']}")
        
        print("=" * 50)
        return all_passed
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "PASSED"])
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
            },
            "test_results": self.results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }

async def main():
    """Main test execution."""
    tester = MCPToolTester()
    
    success = await tester.run_all_tests()
    report = tester.generate_report()
    
    print(f"📊 Test Summary: {report['summary']['passed_tests']}/{report['summary']['total_tests']} passed "
          f"({report['summary']['success_rate']}%)")
    
    # Save detailed report
    with open("mcp_test_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Script Dependencies

### Required Python Packages
```bash
# Install required packages for scripts
pip install -r scripts/requirements.txt

# Or install individually:
pip install asyncio aiohttp psutil pytest
```

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install curl jq sqlite3

# macOS
brew install curl jq sqlite3

# Verify installations
curl --version
jq --version
sqlite3 --version
```

## Script Maintenance

### Adding New Scripts
1. Create script file with appropriate extension (.sh, .py)
2. Add executable permissions: `chmod +x scripts/new_script.sh`
3. Add documentation to this README
4. Include script in test suites where appropriate
5. Add to `.gitignore` any temporary files created

### Script Conventions
- Use `set -e` in bash scripts for error handling
- Include usage documentation in script headers
- Use consistent exit codes (0=success, 1-255=various failures)
- Clean up temporary files and processes
- Provide verbose and quiet modes where appropriate

### Error Handling
```bash
# Bash error handling template
#!/bin/bash
set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Cleanup function
cleanup() {
    local exit_code=$?
    echo "Cleaning up..."
    # Add cleanup commands here
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT INT TERM
```

## Integration with CI/CD

### GitHub Actions Usage
Scripts are integrated into GitHub Actions workflows:

```yaml
# .github/workflows/integration-test.yml
- name: Run Integration Tests
  run: |
    export INTERCOM_ACCESS_TOKEN="${{ secrets.INTERCOM_ACCESS_TOKEN }}"
    ./scripts/run_integration_test.sh --performance-report

- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: integration-test-results
    path: |
      mcp_test_results.json
      performance_report.json
```

### Local Development Usage
```bash
# Daily development testing
./scripts/run_integration_test.sh --quick

# Before PR submission
./scripts/run_integration_test.sh --performance-report

# Performance monitoring
./scripts/monitor_performance.sh &
# ... run tests ...
pkill -f monitor_performance
```

## Troubleshooting Scripts

### Script Permission Issues
```bash
# Fix script permissions
chmod +x scripts/*.sh

# Verify permissions
ls -la scripts/
```

### Missing Dependencies
```bash
# Check for missing commands
./scripts/check_dependencies.sh

# Install missing dependencies
./scripts/install_dependencies.sh
```

### Script Debugging
```bash
# Enable bash debugging
bash -x scripts/run_integration_test.sh

# Python script debugging
python3 -u scripts/test_mcp_tools.py --verbose
```

This comprehensive script documentation ensures that all testing automation is well-documented and maintainable for future development.