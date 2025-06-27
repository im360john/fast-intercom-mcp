# Testing Scripts Documentation

## Overview

This directory contains all testing scripts for the FastIntercom MCP server. These scripts automate various testing scenarios from basic functionality checks to comprehensive integration testing.

## Script Categories

### Integration Test Scripts
- `run_integration_test.sh` - Main integration test runner
- `test_docker_install.sh` - Docker deployment testing
- `run_performance_test.sh` - Performance benchmarking
- `test_mcp_tools.py` - MCP protocol tool testing

### Monitoring Scripts
- `monitor_performance.sh` - Real-time performance monitoring
- `monitor_memory_usage.sh` - Memory usage tracking
- `profile_sync_performance.sh` - Sync operation profiling

### Utility Scripts
- `cleanup_test_data.sh` - Test environment cleanup
- `verify_database_integrity.py` - Database validation
- `generate_test_report.sh` - Test result reporting

## Script Details

### run_integration_test.sh

**Purpose**: Complete integration test with real Intercom API  
**Usage**: `./scripts/run_integration_test.sh [OPTIONS]`

**Options**:
- `--days N` - Number of days to sync (default: 7)
- `--max-conversations N` - Limit conversations synced
- `--performance-report` - Generate detailed performance metrics
- `--quick` - Fast test with minimal data
- `--verbose` - Enable debug logging

**Examples**:
```bash
# Quick 7-day integration test
./scripts/run_integration_test.sh

# Extended test with performance monitoring
./scripts/run_integration_test.sh --days 30 --performance-report

# Quick functionality check
./scripts/run_integration_test.sh --quick
```

**Exit Codes**:
- `0` - All tests passed
- `1` - API connection failed
- `2` - Sync operation failed
- `3` - MCP server test failed
- `4` - Performance targets not met

### test_docker_install.sh

**Purpose**: Test clean Docker installation and deployment  
**Usage**: `./scripts/test_docker_install.sh [OPTIONS]`

**Options**:
- `--with-api-test` - Include real API testing
- `--config FILE` - Use custom configuration
- `--debug` - Enable debug mode
- `--keep-container` - Don't remove test container

**Examples**:
```bash
# Basic Docker functionality test
./scripts/test_docker_install.sh

# Full Docker test with API integration
./scripts/test_docker_install.sh --with-api-test

# Debug Docker issues
./scripts/test_docker_install.sh --debug --keep-container
```

### run_performance_test.sh

**Purpose**: Dedicated performance benchmarking  
**Usage**: `./scripts/run_performance_test.sh [OPTIONS]`

**Options**:
- `--profile` - Generate detailed performance profile
- `--output FILE` - Save results to JSON file
- `--baseline FILE` - Compare against baseline results
- `--stress-test` - Run with large dataset

**Examples**:
```bash
# Standard performance test
./scripts/run_performance_test.sh

# Detailed profiling with output
./scripts/run_performance_test.sh --profile --output perf_results.json

# Stress test with large dataset
./scripts/run_performance_test.sh --stress-test
```

### test_mcp_tools.py

**Purpose**: Test individual MCP protocol tools  
**Usage**: `python3 scripts/test_mcp_tools.py [OPTIONS]`

**Options**:
- `--tool TOOL_NAME` - Test specific tool only
- `--server-url URL` - Connect to custom server
- `--test-data FILE` - Use custom test data
- `--timeout SECONDS` - Set request timeout

**Examples**:
```bash
# Test all MCP tools
python3 scripts/test_mcp_tools.py

# Test specific tool
python3 scripts/test_mcp_tools.py --tool search_conversations

# Test with custom server
python3 scripts/test_mcp_tools.py --server-url http://localhost:3001
```

### monitor_performance.sh

**Purpose**: Real-time performance monitoring during operations  
**Usage**: `./scripts/monitor_performance.sh [OPTIONS]`

**Options**:
- `--duration SECONDS` - Monitoring duration
- `--interval SECONDS` - Sample interval
- `--output FILE` - Save metrics to file
- `--quiet` - Minimal output

**Examples**:
```bash
# Monitor during integration test
./scripts/monitor_performance.sh &
./scripts/run_integration_test.sh
pkill -f monitor_performance

# Monitor for specific duration
./scripts/monitor_performance.sh --duration 300 --output metrics.log
```

### verify_database_integrity.py

**Purpose**: Comprehensive database validation  
**Usage**: `python3 scripts/verify_database_integrity.py [OPTIONS]`

**Options**:
- `--database PATH` - Specify database file
- `--fix-issues` - Attempt to fix detected issues
- `--report FILE` - Generate detailed report
- `--quick` - Fast integrity check only

**examples**:
```bash
# Basic integrity check
python3 scripts/verify_database_integrity.py

# Full validation with report
python3 scripts/verify_database_integrity.py --report integrity_report.json

# Check and fix issues
python3 scripts/verify_database_integrity.py --fix-issues
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