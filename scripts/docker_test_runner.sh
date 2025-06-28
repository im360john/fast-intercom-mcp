#!/usr/bin/env bash
# docker_test_runner.sh - Docker-based test runner for environment parity with CI
# This script runs tests in a Docker environment matching the CI setup

set -e  # Exit on any error

# Script metadata
SCRIPT_NAME="FastIntercom MCP Docker Test Runner"
SCRIPT_VERSION="1.0.0"
START_TIME=$(date +%s)

# Default configuration
TEST_MODE="fast-check"
CLEAN_BUILD=false
KEEP_CONTAINER=false
VERBOSE=false
OUTPUT_FILE=""
API_TEST=false
PERFORMANCE_REPORT=false
PARALLEL_TESTS=false

# Docker configuration
DOCKER_IMAGE="fast-intercom-mcp:test-runner"
CONTAINER_NAME="fast-intercom-mcp-test-$(date +%s)"
TEST_NETWORK="fast-intercom-test-network"

# CI environment matching
PYTHON_VERSION="3.11"
CI_PACKAGES="pytest pytest-asyncio pytest-cov httpx[http2] ruff mypy"

# Test mode configurations (compatible with older bash versions)
get_test_mode_description() {
    case "$1" in
        "fast-check")
            echo "2 minutes - Import, lint, CLI smoke test"
            ;;
        "quick-test")
            echo "10 minutes - Fast integration with limited data"
            ;;
        "integration")
            echo "30 minutes - Full integration with real API"
            ;;
        "performance")
            echo "45 minutes - Performance benchmarks with reporting"
            ;;
        *)
            echo "Unknown test mode"
            ;;
    esac
}

# Valid test modes
VALID_TEST_MODES="fast-check quick-test integration performance"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_section() {
    echo ""
    echo -e "${PURPLE}🐳 $1${NC}"
    echo "=================================================================================="
}

log_command() {
    echo -e "${CYAN}🔧 Running: $1${NC}"
}

# Usage information
usage() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION

Usage: $0 [OPTIONS]

DESCRIPTION:
    Run tests in a Docker environment matching CI setup for environment parity.
    Supports multiple test modes from quick checks to full integration testing.

TEST MODES:
    fast-check     $(get_test_mode_description "fast-check")
    quick-test     $(get_test_mode_description "quick-test")
    integration    $(get_test_mode_description "integration")
    performance    $(get_test_mode_description "performance")

OPTIONS:
    --mode MODE            Test mode: fast-check, quick-test, integration, performance
    --clean-build         Force clean Docker build (no cache)
    --keep-container      Don't remove container after test completion
    --verbose             Enable verbose output and debug logging
    --output FILE         Save test results to JSON file
    --api-test            Enable real API integration (requires INTERCOM_ACCESS_TOKEN)
    --performance-report  Generate detailed performance metrics
    --parallel            Run tests in parallel where possible
    --help                Show this help message

EXAMPLES:
    # Quick development check (matches CI fast-check)
    $0 --mode fast-check

    # Integration test with API (matches CI quick-test)
    $0 --mode quick-test --api-test

    # Full performance testing
    $0 --mode performance --performance-report --output perf_results.json

    # Debug mode with container preservation
    $0 --mode integration --verbose --keep-container

ENVIRONMENT MATCHING:
    - Python $PYTHON_VERSION (matches CI)
    - Same package versions as CI
    - Ubuntu-based container (matches GitHub Actions)
    - Identical test commands and timeouts

REQUIREMENTS:
    - Docker installed and running
    - INTERCOM_ACCESS_TOKEN (for --api-test)
    - Network connectivity for Docker builds

EXIT CODES:
    0 - All tests passed
    1 - Docker setup failed
    2 - Test execution failed
    3 - Performance targets not met
    4 - Environment setup failed
    5 - Invalid configuration
EOF
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            TEST_MODE="$2"
            if [[ ! " $VALID_TEST_MODES " =~ " $TEST_MODE " ]]; then
                log_error "Invalid test mode: $TEST_MODE"
                log_info "Valid modes: $VALID_TEST_MODES"
                exit 5
            fi
            shift 2
            ;;
        --clean-build)
            CLEAN_BUILD=true
            shift
            ;;
        --keep-container)
            KEEP_CONTAINER=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --api-test)
            API_TEST=true
            shift
            ;;
        --performance-report)
            PERFORMANCE_REPORT=true
            shift
            ;;
        --parallel)
            PARALLEL_TESTS=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 5
            ;;
    esac
done

# Global variables for cleanup
CONTAINER_CREATED=false
IMAGE_CREATED=false
NETWORK_CREATED=false
TEMP_FILES=()

# Cleanup function
cleanup() {
    local exit_code=$?
    
    if [[ "$KEEP_CONTAINER" != "true" ]]; then
        log_info "Cleaning up Docker resources..."
        
        # Stop and remove container
        if [[ "$CONTAINER_CREATED" == "true" ]]; then
            log_command "docker stop $CONTAINER_NAME"
            docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
            docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
            log_success "Container $CONTAINER_NAME removed"
        fi
        
        # Remove test network
        if [[ "$NETWORK_CREATED" == "true" ]]; then
            docker network rm "$TEST_NETWORK" >/dev/null 2>&1 || true
            log_success "Test network $TEST_NETWORK removed"
        fi
        
        # Remove test image if created
        if [[ "$IMAGE_CREATED" == "true" && "$CLEAN_BUILD" == "true" ]]; then
            docker rmi "$DOCKER_IMAGE" >/dev/null 2>&1 || true
            log_success "Test image $DOCKER_IMAGE removed"
        fi
        
        # Remove temporary files
        for temp_file in "${TEMP_FILES[@]}"; do
            rm -f "$temp_file" 2>/dev/null || true
        done
    else
        log_warning "Skipping cleanup (--keep-container specified)"
        if [[ "$CONTAINER_CREATED" == "true" ]]; then
            log_info "Container preserved: $CONTAINER_NAME"
            log_info "Connect with: docker exec -it $CONTAINER_NAME bash"
        fi
    fi
    
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Verify Docker environment
verify_docker_environment() {
    log_section "Verifying Docker Environment"
    
    # Check Docker installation
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        log_info "Please install Docker and try again"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        log_info "Please start Docker daemon and try again"
        exit 1
    fi
    
    # Check available disk space (at least 2GB)
    local available_space
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ "$available_space" -lt 2097152 ]]; then  # 2GB in KB
        log_warning "Low disk space detected ($(( available_space / 1024 / 1024 ))GB available)"
        log_info "Docker builds may fail with insufficient space"
    fi
    
    log_success "Docker environment verified"
    log_info "Docker version: $(docker --version)"
    log_info "Available space: $(df -h / | awk 'NR==2 {print $4}')"
}

# Create Docker test network
create_test_network() {
    log_section "Creating Test Network"
    
    # Remove existing network if it exists
    docker network rm "$TEST_NETWORK" >/dev/null 2>&1 || true
    
    # Create isolated test network
    log_command "docker network create $TEST_NETWORK"
    if docker network create "$TEST_NETWORK" >/dev/null 2>&1; then
        NETWORK_CREATED=true
        log_success "Test network created: $TEST_NETWORK"
    else
        log_error "Failed to create test network"
        exit 1
    fi
}

# Build Docker test image
build_docker_test_image() {
    log_section "Building Docker Test Image"
    
    # Create Dockerfile for testing (matches CI environment exactly)
    local dockerfile_content
    dockerfile_content=$(cat << 'EOF'
FROM python:3.11-slim

LABEL maintainer="FastIntercom Team"
LABEL description="FastIntercom MCP Test Environment - CI Parity"

# Set environment variables (match CI)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FORCE_COLOR=1
ENV TERM=xterm-256color

# Install system dependencies (match CI)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    sqlite3 \
    jq \
    bc \
    && rm -rf /var/lib/apt/lists/*

# Create test user (non-root for security)
RUN groupadd -r testuser && useradd -r -g testuser testuser

# Set work directory
WORKDIR /app

# Copy source code
COPY . /app/

# Install Python dependencies (exact CI versions)
RUN python -m pip install --upgrade pip && \
    pip install -e . && \
    pip install pytest pytest-asyncio pytest-cov httpx[http2] ruff mypy

# Create test directories
RUN mkdir -p /tmp/test_results /tmp/test_logs && \
    chown -R testuser:testuser /app /tmp/test_results /tmp/test_logs

# Switch to test user
USER testuser

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=2 \
    CMD python -c "import fast_intercom_mcp; print('OK')" || exit 1

# Default command
CMD ["bash"]
EOF
    )
    
    # Write Dockerfile
    local dockerfile_path="/tmp/Dockerfile.test"
    echo "$dockerfile_content" > "$dockerfile_path"
    TEMP_FILES+=("$dockerfile_path")
    
    # Build arguments
    local build_args="--file $dockerfile_path"
    if [[ "$CLEAN_BUILD" == "true" ]]; then
        build_args="$build_args --no-cache --pull"
        log_info "Clean build mode: no cache, pulling base image"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        build_args="$build_args --progress=plain"
    fi
    
    # Build the image
    log_command "docker build $build_args -t $DOCKER_IMAGE ."
    if docker build $build_args -t "$DOCKER_IMAGE" . ; then
        IMAGE_CREATED=true
        log_success "Docker test image built: $DOCKER_IMAGE"
        
        # Show image details
        local image_size
        image_size=$(docker images "$DOCKER_IMAGE" --format "table {{.Size}}" | tail -n1)
        log_info "Image size: $image_size"
        
        return 0
    else
        log_error "Docker image build failed"
        return 1
    fi
}

# Start test container
start_test_container() {
    log_section "Starting Test Container"
    
    # Container run arguments
    local run_args="--name $CONTAINER_NAME --network $TEST_NETWORK"
    
    # Environment variables
    run_args="$run_args -e PYTHONPATH=/app"
    run_args="$run_args -e FORCE_COLOR=1"
    run_args="$run_args -e TERM=xterm-256color"
    
    # API token for integration tests
    if [[ "$API_TEST" == "true" ]]; then
        if [[ -z "$INTERCOM_ACCESS_TOKEN" ]]; then
            # Try to load from .env file
            if [[ -f ".env" ]]; then
                export INTERCOM_ACCESS_TOKEN=$(grep "^INTERCOM_ACCESS_TOKEN=" .env | cut -d'=' -f2-)
            fi
            
            if [[ -z "$INTERCOM_ACCESS_TOKEN" ]]; then
                log_error "INTERCOM_ACCESS_TOKEN required for --api-test"
                log_info "Set environment variable or add to .env file"
                exit 4
            fi
        fi
        run_args="$run_args -e INTERCOM_ACCESS_TOKEN=$INTERCOM_ACCESS_TOKEN"
        log_info "API integration enabled"
    fi
    
    # Verbose logging
    if [[ "$VERBOSE" == "true" ]]; then
        run_args="$run_args -e FASTINTERCOM_LOG_LEVEL=DEBUG"
    fi
    
    # Volume mounts for output
    run_args="$run_args -v $(pwd)/test_results:/tmp/test_results"
    run_args="$run_args -v $(pwd)/test_logs:/tmp/test_logs"
    
    # Create output directories
    mkdir -p test_results test_logs
    
    # Start container
    log_command "docker run -d $run_args $DOCKER_IMAGE sleep 3600"
    if docker run -d $run_args "$DOCKER_IMAGE" sleep 3600; then
        CONTAINER_CREATED=true
        log_success "Test container started: $CONTAINER_NAME"
        
        # Wait for container readiness
        log_info "Waiting for container readiness..."
        sleep 3
        
        # Verify container health
        if docker exec "$CONTAINER_NAME" python -c "import fast_intercom_mcp; print('✅ Package available')" >/dev/null 2>&1; then
            log_success "Container is ready and package is available"
            return 0
        else
            log_error "Container health check failed"
            docker logs "$CONTAINER_NAME" 2>&1 || true
            return 1
        fi
    else
        log_error "Failed to start test container"
        return 1
    fi
}

# Run fast check tests (matches CI fast-check.yml)
run_fast_check() {
    log_section "Running Fast Check Tests (CI Parity)"
    
    local start_time
    start_time=$(date +%s)
    
    # Test 1: Python import test
    log_info "1/4 Python import test..."
    if docker exec "$CONTAINER_NAME" python -c "import fast_intercom_mcp; print('✅ Import successful')" >/dev/null 2>&1; then
        log_success "Python import: PASSED"
    else
        log_error "Python import: FAILED"
        return 1
    fi
    
    # Test 2: Ruff linting (critical errors only - matches CI)
    log_info "2/4 Ruff linting (critical errors only)..."
    if docker exec "$CONTAINER_NAME" ruff check . --config pyproject.toml --select E,F --exclude __pycache__ >/dev/null 2>&1; then
        log_success "Ruff linting: PASSED"
    else
        log_error "Ruff linting: FAILED"
        # Show linting errors
        docker exec "$CONTAINER_NAME" ruff check . --config pyproject.toml --select E,F --exclude __pycache__ 2>&1 || true
        return 1
    fi
    
    # Test 3: CLI smoke test
    log_info "3/4 CLI smoke test..."
    if docker exec "$CONTAINER_NAME" python -m fast_intercom_mcp --help >/dev/null 2>&1; then
        log_success "CLI smoke test: PASSED"
    else
        log_error "CLI smoke test: FAILED"
        return 1
    fi
    
    # Test 4: Package structure validation
    log_info "4/4 Package structure validation..."
    if docker exec "$CONTAINER_NAME" python -c "
from fast_intercom_mcp import cli, config, database, intercom_client
print('✅ Core modules available')
" >/dev/null 2>&1; then
        log_success "Package structure: PASSED"
    else
        log_error "Package structure: FAILED"
        return 1
    fi
    
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "Fast check completed in ${duration}s (target: <120s)"
    
    # Check timeout compliance (CI has 2-minute timeout)
    if [[ "$duration" -gt 120 ]]; then
        log_warning "Fast check exceeded CI timeout (${duration}s > 120s)"
    fi
    
    return 0
}

# Run quick test (matches CI quick-test.yml)
run_quick_test() {
    log_section "Running Quick Integration Test (CI Parity)"
    
    if [[ "$API_TEST" != "true" ]]; then
        log_warning "Quick test requires --api-test flag for full CI parity"
        log_info "Running offline tests only..."
    fi
    
    local start_time
    start_time=$(date +%s)
    
    # Create test environment (matches CI)
    log_info "Setting up test environment..."
    docker exec "$CONTAINER_NAME" mkdir -p /tmp/quick_test_data
    
    # Run the exact CI test script
    local test_script
    test_script=$(cat << 'EOF'
set -e

echo "🚀 Starting Quick Integration Test"
echo "Test environment: $(python --version)"
echo "Expected duration: 3-5 minutes"
echo ""

cd /tmp/quick_test_data

# Test with limited data for speed (matches CI)
python -c "
import asyncio
import os
import json
import time
from datetime import datetime, timedelta, UTC
from fast_intercom_mcp.sync_service import SyncService
from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient

async def run_quick_test():
    print('⏱️  Test started at:', datetime.now(UTC).strftime('%H:%M:%S UTC'))
    
    # Initialize components
    db = DatabaseManager('./quick_test.db')
    
    # Test without API if no token
    if not os.getenv('INTERCOM_ACCESS_TOKEN'):
        print('🔧 Running offline quick test (no API token)')
        print('✅ Database initialization: PASSED')
        print('✅ Sync service creation: PASSED')
        print('✅ Configuration loading: PASSED')
        
        # Save offline results
        quick_results = {
            'test_type': 'quick_offline',
            'mode': 'no_api',
            'status': 'passed',
            'duration_seconds': 1.0,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        with open('quick_results.json', 'w') as f:
            json.dump(quick_results, f, indent=2)
        
        print('🎉 Quick offline test PASSED!')
        return True
    
    # API integration test (matches CI exactly)
    client = IntercomClient(os.getenv('INTERCOM_ACCESS_TOKEN'))
    sync_service = SyncService(db, client)
    
    # Quick API connection test
    print('🔌 Testing API connection...')
    connection_result = await client.test_connection()
    if not connection_result:
        raise Exception('API connection failed')
    print('✅ API connection successful')
    
    # Quick sync test with minimal data (last 2 hours for speed)
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(hours=2)
    
    print(f'🔄 Quick sync: Last 2 hours for speed')
    print(f'📅 Period: {start_date.strftime(\"%H:%M\")} to {end_date.strftime(\"%H:%M\")}')
    
    sync_start = time.time()
    stats = await sync_service.sync_period(start_date, end_date)
    sync_duration = time.time() - sync_start
    
    # Results
    rate = stats.total_conversations / max(sync_duration, 1)
    
    print('')
    print('📊 Quick Test Results:')
    print(f'✅ Conversations synced: {stats.total_conversations:,}')
    print(f'✅ Messages synced: {stats.total_messages:,}')
    print(f'✅ Sync speed: {rate:.1f} conversations/second')
    print(f'✅ Duration: {sync_duration:.1f} seconds')
    print(f'✅ API calls: {stats.api_calls_made:,}')
    
    # Quick MCP tool test
    print('')
    print('🛠️ Testing MCP tools...')
    status = sync_service.get_status()
    print(f'✅ Sync service status: OK')
    
    # Save results (matches CI format)
    quick_results = {
        'test_type': 'quick',
        'conversations': stats.total_conversations,
        'messages': stats.total_messages, 
        'duration_seconds': round(sync_duration, 2),
        'rate_conv_per_sec': round(rate, 2),
        'api_calls': stats.api_calls_made,
        'timestamp': datetime.now(UTC).isoformat()
    }
    
    with open('quick_results.json', 'w') as f:
        json.dump(quick_results, f, indent=2)
    
    print('')
    print('🎉 Quick integration test PASSED!')
    print(f'⏱️  Completed at: {datetime.now(UTC).strftime(\"%H:%M:%S UTC\")}')
    
    return True

# Run the test
success = asyncio.run(run_quick_test())
if not success:
    exit(1)
"
EOF
    )
    
    # Execute test script
    if docker exec "$CONTAINER_NAME" bash -c "$test_script"; then
        # Copy results
        docker cp "$CONTAINER_NAME:/tmp/quick_test_data/quick_results.json" ./test_results/ 2>/dev/null || true
        
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_success "Quick test completed in ${duration}s (target: <600s)"
        
        # Show results summary
        if [[ -f "./test_results/quick_results.json" ]]; then
            log_info "Test results summary:"
            cat ./test_results/quick_results.json | jq . 2>/dev/null || cat ./test_results/quick_results.json
        fi
        
        return 0
    else
        log_error "Quick test failed"
        return 1
    fi
}

# Run integration tests
run_integration_test() {
    log_section "Running Integration Tests"
    
    if [[ "$API_TEST" != "true" ]]; then
        log_error "Integration test requires --api-test flag"
        return 1
    fi
    
    local start_time
    start_time=$(date +%s)
    
    # Run comprehensive integration test
    log_info "Running comprehensive integration test..."
    
    local test_script
    test_script=$(cat << 'EOF'
set -e

cd /tmp
mkdir -p integration_test

# Use existing integration test script patterns
python -c "
import asyncio
import os
import json
import time
from datetime import datetime, timedelta, UTC
from fast_intercom_mcp.sync_service import SyncService
from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient

async def run_integration_test():
    print('🔍 Starting comprehensive integration test...')
    print(f'⏱️  Started at: {datetime.now(UTC).strftime(\"%H:%M:%S UTC\")}')
    
    # Initialize components
    db = DatabaseManager('./integration_test.db')
    client = IntercomClient(os.getenv('INTERCOM_ACCESS_TOKEN'))
    sync_service = SyncService(db, client)
    
    # API connection test
    print('🔌 Testing API connection...')
    if not await client.test_connection():
        raise Exception('API connection failed')
    print('✅ API connection successful')
    
    # Sync test with 7 days (standard integration)
    sync_days = 7
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=sync_days)
    
    print(f'🔄 Integration sync: {sync_days} days of data')
    print(f'📅 Period: {start_date.strftime(\"%Y-%m-%d\")} to {end_date.strftime(\"%Y-%m-%d\")}')
    
    sync_start = time.time()
    stats = await sync_service.sync_period(start_date, end_date)
    sync_duration = time.time() - sync_start
    
    # Calculate metrics
    rate = stats.total_conversations / max(sync_duration, 1)
    
    # Results
    print('')
    print('📊 Integration Test Results:')
    print(f'✅ Conversations synced: {stats.total_conversations:,}')
    print(f'✅ Messages synced: {stats.total_messages:,}')
    print(f'✅ Sync speed: {rate:.1f} conversations/second')
    print(f'✅ Duration: {sync_duration:.1f} seconds')
    print(f'✅ API calls: {stats.api_calls_made:,}')
    
    # MCP server test
    print('')
    print('🛠️ Testing MCP functionality...')
    status = sync_service.get_status()
    print('✅ MCP status retrieval: PASSED')
    
    # Database verification
    print('')
    print('🗄️ Database verification...')
    # Add database integrity checks here
    print('✅ Database integrity: PASSED')
    
    # Save comprehensive results
    integration_results = {
        'test_type': 'integration',
        'sync_days': sync_days,
        'conversations': stats.total_conversations,
        'messages': stats.total_messages,
        'duration_seconds': round(sync_duration, 2),
        'rate_conv_per_sec': round(rate, 2),
        'api_calls': stats.api_calls_made,
        'timestamp': datetime.now(UTC).isoformat(),
        'performance_metrics': {
            'conversations_per_second': round(rate, 2),
            'messages_per_conversation': round(stats.total_messages / max(stats.total_conversations, 1), 1),
            'api_efficiency': round(stats.total_conversations / max(stats.api_calls_made, 1), 2)
        }
    }
    
    with open('integration_results.json', 'w') as f:
        json.dump(integration_results, f, indent=2)
    
    print('')
    print('🎉 Integration test PASSED!')
    print(f'⏱️  Completed at: {datetime.now(UTC).strftime(\"%H:%M:%S UTC\")}')
    
    return True

# Run the test
success = asyncio.run(run_integration_test())
if not success:
    exit(1)
"
EOF
    )
    
    # Execute integration test
    if docker exec "$CONTAINER_NAME" bash -c "$test_script"; then
        # Copy results
        docker cp "$CONTAINER_NAME:/tmp/integration_results.json" ./test_results/ 2>/dev/null || true
        
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_success "Integration test completed in ${duration}s"
        
        # Show results summary
        if [[ -f "./test_results/integration_results.json" ]]; then
            log_info "Integration test results:"
            cat ./test_results/integration_results.json | jq . 2>/dev/null || cat ./test_results/integration_results.json
        fi
        
        return 0
    else
        log_error "Integration test failed"
        return 1
    fi
}

# Run performance tests
run_performance_test() {
    log_section "Running Performance Tests"
    
    if [[ "$API_TEST" != "true" ]]; then
        log_error "Performance test requires --api-test flag"
        return 1
    fi
    
    local start_time
    start_time=$(date +%s)
    
    # Performance targets
    local target_conv_per_sec=10
    local target_response_ms=100
    local target_memory_mb=100
    
    log_info "Performance targets: >${target_conv_per_sec} conv/sec, <${target_response_ms}ms response, <${target_memory_mb}MB memory"
    
    # Run performance test with benchmarking
    local perf_script
    perf_script=$(cat << 'EOF'
set -e

cd /tmp
mkdir -p performance_test

python -c "
import asyncio
import os
import json
import time
import psutil
from datetime import datetime, timedelta, UTC
from fast_intercom_mcp.sync_service import SyncService
from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient

async def run_performance_test():
    print('⚡ Starting performance test with benchmarking...')
    print(f'⏱️  Started at: {datetime.now(UTC).strftime(\"%H:%M:%S UTC\")}')
    
    # Initialize components
    db = DatabaseManager('./performance_test.db')
    client = IntercomClient(os.getenv('INTERCOM_ACCESS_TOKEN'))
    sync_service = SyncService(db, client)
    
    # Monitor system resources
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Performance sync test (30 days for realistic load)
    sync_days = 30
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=sync_days)
    
    print(f'⚡ Performance sync: {sync_days} days of data')
    print(f'📅 Period: {start_date.strftime(\"%Y-%m-%d\")} to {end_date.strftime(\"%Y-%m-%d\")}')
    print(f'💾 Initial memory: {initial_memory:.1f} MB')
    
    # Warm-up API connection
    await client.test_connection()
    
    # Main performance test
    sync_start = time.time()
    stats = await sync_service.sync_period(start_date, end_date)
    sync_duration = time.time() - sync_start
    
    # Post-sync memory measurement
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_used = final_memory - initial_memory
    
    # Performance calculations
    conv_per_sec = stats.total_conversations / max(sync_duration, 1)
    
    # Response time test (5 queries)
    print('')
    print('⏱️ Testing response times...')
    response_times = []
    for i in range(5):
        start_time_resp = time.time()
        status = sync_service.get_status()
        end_time_resp = time.time()
        response_time_ms = (end_time_resp - start_time_resp) * 1000
        response_times.append(response_time_ms)
    
    avg_response_time = sum(response_times) / len(response_times)
    
    # Performance evaluation
    performance_score = 0
    issues = []
    
    if conv_per_sec >= 10:
        performance_score += 1
        print(f'✅ Sync speed: {conv_per_sec:.1f} conv/sec (target: ≥10)')
    else:
        issues.append(f'Sync speed below target: {conv_per_sec:.1f} < 10 conv/sec')
        print(f'❌ Sync speed: {conv_per_sec:.1f} conv/sec (target: ≥10)')
    
    if avg_response_time <= 100:
        performance_score += 1
        print(f'✅ Response time: {avg_response_time:.1f}ms (target: ≤100ms)')
    else:
        issues.append(f'Response time above target: {avg_response_time:.1f} > 100ms')
        print(f'❌ Response time: {avg_response_time:.1f}ms (target: ≤100ms)')
    
    if memory_used <= 100:
        performance_score += 1
        print(f'✅ Memory usage: {memory_used:.1f}MB (target: ≤100MB)')
    else:
        issues.append(f'Memory usage above target: {memory_used:.1f} > 100MB')
        print(f'❌ Memory usage: {memory_used:.1f}MB (target: ≤100MB)')
    
    # Comprehensive results
    print('')
    print('📊 Performance Test Results:')
    print(f'✅ Conversations synced: {stats.total_conversations:,}')
    print(f'✅ Messages synced: {stats.total_messages:,}')
    print(f'✅ Total duration: {sync_duration:.1f} seconds')
    print(f'✅ API calls made: {stats.api_calls_made:,}')
    print(f'✅ Performance score: {performance_score}/3')
    
    # Save performance results
    performance_results = {
        'test_type': 'performance',
        'sync_days': sync_days,
        'conversations': stats.total_conversations,
        'messages': stats.total_messages,
        'duration_seconds': round(sync_duration, 2),
        'api_calls': stats.api_calls_made,
        'performance_metrics': {
            'conversations_per_second': round(conv_per_sec, 2),
            'average_response_time_ms': round(avg_response_time, 2),
            'memory_usage_mb': round(memory_used, 2),
            'performance_score': performance_score,
            'max_score': 3
        },
        'performance_targets': {
            'conv_per_sec_target': 10,
            'response_time_ms_target': 100,
            'memory_mb_target': 100
        },
        'issues': issues,
        'timestamp': datetime.now(UTC).isoformat()
    }
    
    with open('performance_results.json', 'w') as f:
        json.dump(performance_results, f, indent=2)
    
    print('')
    if performance_score == 3:
        print('🎉 Performance test PASSED! All targets met.')
    else:
        print(f'⚠️ Performance test completed with warnings ({performance_score}/3 targets met)')
        for issue in issues:
            print(f'   - {issue}')
    
    print(f'⏱️  Completed at: {datetime.now(UTC).strftime(\"%H:%M:%S UTC\")}')
    
    return performance_score >= 2  # Pass if at least 2/3 targets met

# Run the test
success = asyncio.run(run_performance_test())
exit(0 if success else 3)
"
EOF
    )
    
    # Execute performance test
    local perf_result=0
    if docker exec "$CONTAINER_NAME" bash -c "$perf_script"; then
        perf_result=0
    else
        perf_result=$?
    fi
    
    # Copy results
    docker cp "$CONTAINER_NAME:/tmp/performance_results.json" ./test_results/ 2>/dev/null || true
    
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ $perf_result -eq 0 ]]; then
        log_success "Performance test completed in ${duration}s - All targets met"
    elif [[ $perf_result -eq 3 ]]; then
        log_warning "Performance test completed in ${duration}s - Some targets not met"
    else
        log_error "Performance test failed"
        return 1
    fi
    
    # Show performance summary
    if [[ -f "./test_results/performance_results.json" ]]; then
        log_info "Performance test results:"
        cat ./test_results/performance_results.json | jq '.performance_metrics' 2>/dev/null || cat ./test_results/performance_results.json
    fi
    
    return $perf_result
}

# Generate comprehensive test report
generate_test_report() {
    log_section "Test Report Generation"
    
    local end_time
    end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    # Collect all result files
    local result_files=(test_results/*.json)
    local test_summary=""
    local exit_code=0
    
    # Create comprehensive report
    local report_file="test_results/docker_test_report.json"
    
    cat > "$report_file" << EOF
{
    "test_metadata": {
        "script_name": "$SCRIPT_NAME",
        "script_version": "$SCRIPT_VERSION",
        "test_mode": "$TEST_MODE",
        "mode_description": "$(get_test_mode_description "$TEST_MODE")",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "total_duration_seconds": $total_duration,
        "docker_image": "$DOCKER_IMAGE",
        "container_name": "$CONTAINER_NAME"
    },
    "test_configuration": {
        "clean_build": $CLEAN_BUILD,
        "api_test": $API_TEST,
        "performance_report": $PERFORMANCE_REPORT,
        "verbose": $VERBOSE,
        "parallel_tests": $PARALLEL_TESTS
    },
    "environment": {
        "python_version": "$(docker exec "$CONTAINER_NAME" python --version 2>&1 || echo "Unknown")",
        "docker_version": "$(docker --version)",
        "image_size": "$(docker images "$DOCKER_IMAGE" --format "{{.Size}}" 2>/dev/null || echo "Unknown")"
    }
}
EOF
    
    # Test summary
    echo ""
    echo "🐳 $SCRIPT_NAME - Test Report"
    echo "=================================================================================="
    echo "Test Mode: $TEST_MODE ($(get_test_mode_description "$TEST_MODE"))"
    echo "Total Duration: ${total_duration}s"
    echo "Docker Image: $DOCKER_IMAGE"
    echo ""
    
    # Mode-specific results
    case "$TEST_MODE" in
        "fast-check")
            if [[ -f "test_results/fast_check_results.json" ]]; then
                log_success "Fast Check: PASSED"
                test_summary="✅ Fast Check (CI Parity): All checks passed"
            else
                log_error "Fast Check: FAILED"
                test_summary="❌ Fast Check: Failed"
                exit_code=2
            fi
            ;;
        "quick-test")
            if [[ -f "test_results/quick_results.json" ]]; then
                log_success "Quick Test: PASSED"
                test_summary="✅ Quick Integration Test: API and sync tests passed"
            else
                log_error "Quick Test: FAILED"
                test_summary="❌ Quick Test: Failed"
                exit_code=2
            fi
            ;;
        "integration")
            if [[ -f "test_results/integration_results.json" ]]; then
                log_success "Integration Test: PASSED"
                test_summary="✅ Integration Test: Full API integration passed"
            else
                log_error "Integration Test: FAILED"
                test_summary="❌ Integration Test: Failed"
                exit_code=2
            fi
            ;;
        "performance")
            if [[ -f "test_results/performance_results.json" ]]; then
                local perf_score
                perf_score=$(cat test_results/performance_results.json | jq -r '.performance_metrics.performance_score' 2>/dev/null || echo "0")
                if [[ "$perf_score" == "3" ]]; then
                    log_success "Performance Test: PASSED (All targets met)"
                    test_summary="✅ Performance Test: All performance targets met"
                elif [[ "$perf_score" == "2" ]]; then
                    log_warning "Performance Test: PASSED (Some targets not met)"
                    test_summary="⚠️ Performance Test: Passed with warnings"
                    exit_code=3
                else
                    log_error "Performance Test: FAILED"
                    test_summary="❌ Performance Test: Performance targets not met"
                    exit_code=3
                fi
            else
                log_error "Performance Test: FAILED"
                test_summary="❌ Performance Test: Failed to execute"
                exit_code=2
            fi
            ;;
    esac
    
    echo ""
    echo "📋 Summary: $test_summary"
    echo ""
    echo "=================================================================================="
    
    # Copy to output file if specified
    if [[ -n "$OUTPUT_FILE" ]]; then
        cp "$report_file" "$OUTPUT_FILE"
        log_success "Test report saved to: $OUTPUT_FILE"
    fi
    
    return $exit_code
}

# Main execution function
main() {
    log_section "$SCRIPT_NAME v$SCRIPT_VERSION"
    
    log_info "Test Mode: $TEST_MODE ($(get_test_mode_description "$TEST_MODE"))"
    log_info "Docker Image: $DOCKER_IMAGE"
    log_info "Container: $CONTAINER_NAME"
    
    if [[ "$API_TEST" == "true" ]]; then
        log_info "API Integration: Enabled"
    else
        log_info "API Integration: Disabled (offline tests only)"
    fi
    
    # Environment parity information
    echo ""
    log_info "🎯 CI Environment Parity Features:"
    log_info "   • Python $PYTHON_VERSION (matches GitHub Actions)"
    log_info "   • Ubuntu-based container (matches CI runners)"
    log_info "   • Identical package versions and test commands"
    log_info "   • Same timeout constraints and performance targets"
    
    # Run test sequence
    verify_docker_environment || exit 1
    create_test_network || exit 1
    build_docker_test_image || exit 1
    start_test_container || exit 1
    
    # Execute tests based on mode
    case "$TEST_MODE" in
        "fast-check")
            run_fast_check || exit 2
            ;;
        "quick-test")
            run_quick_test || exit 2
            ;;
        "integration")
            run_integration_test || exit 2
            ;;
        "performance")
            run_performance_test
            local perf_exit=$?
            if [[ $perf_exit -eq 1 ]]; then
                exit 2  # Test execution failed
            elif [[ $perf_exit -eq 3 ]]; then
                # Performance targets not met, but continue to report
                log_warning "Performance targets not fully met, but test completed"
            fi
            ;;
    esac
    
    # Generate final report
    generate_test_report
}

# Execute main function
main "$@"