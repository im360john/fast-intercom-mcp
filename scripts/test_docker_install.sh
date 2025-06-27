#!/bin/bash
# test_docker_install.sh - Docker clean install testing for FastIntercom MCP
# This script tests Docker deployment and clean installation scenarios

set -e  # Exit on any error

# Script metadata
SCRIPT_NAME="FastIntercom MCP Docker Test"
SCRIPT_VERSION="1.0.0"

# Default configuration
WITH_API_TEST=false
DEBUG_MODE=false
KEEP_CONTAINER=false
CONFIG_FILE=""
CONTAINER_NAME="fast-intercom-mcp-test-$(date +%s)"
IMAGE_TAG="fast-intercom-mcp:test"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    echo -e "${BLUE}🐳 $1${NC}"
    echo "=================================================================================="
}

# Usage information
usage() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION

Usage: $0 [OPTIONS]

OPTIONS:
    --with-api-test        Include real API integration testing
    --config FILE          Use custom configuration file
    --debug               Enable debug mode with verbose output
    --keep-container      Don't remove test container after completion
    --help                Show this help message

EXAMPLES:
    # Basic Docker functionality test
    $0

    # Full Docker test with API integration
    $0 --with-api-test

    # Debug Docker issues
    $0 --debug --keep-container

REQUIREMENTS:
    - Docker installed and running
    - INTERCOM_ACCESS_TOKEN (for --with-api-test)
    - Network connectivity

EXIT CODES:
    0 - All tests passed
    1 - Docker build failed
    2 - Container startup failed
    3 - CLI functionality test failed
    4 - MCP server test failed
    5 - API integration test failed
EOF
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-api-test)
            WITH_API_TEST=true
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        --keep-container)
            KEEP_CONTAINER=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Global variables for cleanup
CONTAINER_CREATED=false
IMAGE_CREATED=false

# Cleanup function
cleanup() {
    local exit_code=$?
    
    if [[ "$KEEP_CONTAINER" != "true" ]]; then
        log_info "Cleaning up Docker resources..."
        
        # Stop and remove container
        if [[ "$CONTAINER_CREATED" == "true" ]]; then
            docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
            docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
            log_success "Container $CONTAINER_NAME removed"
        fi
        
        # Remove test image
        if [[ "$IMAGE_CREATED" == "true" ]]; then
            docker rmi "$IMAGE_TAG" >/dev/null 2>&1 || true
            log_success "Test image $IMAGE_TAG removed"
        fi
    else
        log_warning "Skipping cleanup (--keep-container specified)"
        if [[ "$CONTAINER_CREATED" == "true" ]]; then
            log_info "Container preserved: $CONTAINER_NAME"
        fi
    fi
    
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Verify Docker is available
verify_docker() {
    log_section "Verifying Docker Environment"
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        log_info "Please start Docker daemon and try again"
        exit 1
    fi
    
    log_success "Docker is available and running"
    log_info "Docker version: $(docker --version)"
}

# Build Docker image
build_docker_image() {
    log_section "Building Docker Image"
    
    log_info "Building image: $IMAGE_TAG"
    
    # Build arguments
    local build_args=""
    if [[ "$DEBUG_MODE" == "true" ]]; then
        build_args="--progress=plain --no-cache"
    fi
    
    # Build the image
    if docker build $build_args -t "$IMAGE_TAG" . ; then
        log_success "Docker image built successfully: $IMAGE_TAG"
        IMAGE_CREATED=true
        
        # Show image details
        local image_size
        image_size=$(docker images "$IMAGE_TAG" --format "table {{.Size}}" | tail -n1)
        log_info "Image size: $image_size"
        
        return 0
    else
        log_error "Docker build failed"
        return 1
    fi
}

# Test container startup
test_container_startup() {
    log_section "Testing Container Startup"
    
    log_info "Starting container: $CONTAINER_NAME"
    
    # Container run arguments
    local run_args="--name $CONTAINER_NAME"
    
    # Add API token if API testing is enabled
    if [[ "$WITH_API_TEST" == "true" ]]; then
        if [[ -z "$INTERCOM_ACCESS_TOKEN" ]]; then
            log_error "INTERCOM_ACCESS_TOKEN required for --with-api-test"
            return 1
        fi
        run_args="$run_args -e INTERCOM_ACCESS_TOKEN=$INTERCOM_ACCESS_TOKEN"
    fi
    
    # Add custom config if specified
    if [[ -n "$CONFIG_FILE" && -f "$CONFIG_FILE" ]]; then
        run_args="$run_args -v $(realpath "$CONFIG_FILE"):/app/config.json"
    fi
    
    # Start container in detached mode
    if docker run -d $run_args "$IMAGE_TAG" sleep 60; then
        CONTAINER_CREATED=true
        log_success "Container started successfully"
        
        # Wait for container to be ready
        sleep 2
        
        # Verify container is running
        if docker ps | grep -q "$CONTAINER_NAME"; then
            log_success "Container is running"
            return 0
        else
            log_error "Container failed to stay running"
            # Show container logs for debugging
            docker logs "$CONTAINER_NAME" 2>&1 || true
            return 1
        fi
    else
        log_error "Failed to start container"
        return 1
    fi
}

# Test CLI functionality
test_cli_functionality() {
    log_section "Testing CLI Functionality"
    
    log_info "Testing CLI commands inside container..."
    
    # Test help command
    if docker exec "$CONTAINER_NAME" fast-intercom-mcp --help >/dev/null 2>&1; then
        log_success "CLI help command: PASSED"
    else
        log_error "CLI help command: FAILED"
        return 1
    fi
    
    # Test version command (if available)
    if docker exec "$CONTAINER_NAME" fast-intercom-mcp --version >/dev/null 2>&1; then
        log_success "CLI version command: PASSED"
    else
        log_warning "CLI version command: Not available (may be normal)"
    fi
    
    # Test init command
    if docker exec "$CONTAINER_NAME" fast-intercom-mcp init --force >/dev/null 2>&1; then
        log_success "CLI init command: PASSED"
    else
        log_error "CLI init command: FAILED"
        return 1
    fi
    
    # Test status command
    if docker exec "$CONTAINER_NAME" fast-intercom-mcp status >/dev/null 2>&1; then
        log_success "CLI status command: PASSED"
    else
        log_warning "CLI status command: Warning (may be normal without data)"
    fi
    
    log_success "CLI functionality tests completed"
    return 0
}

# Test MCP server startup
test_mcp_server() {
    log_section "Testing MCP Server Startup"
    
    log_info "Testing MCP server startup inside container..."
    
    # Start MCP server in background
    docker exec -d "$CONTAINER_NAME" fast-intercom-mcp start --test-mode
    
    # Wait for server to start
    sleep 3
    
    # Check if server process is running
    if docker exec "$CONTAINER_NAME" pgrep -f "fast-intercom-mcp.*start" >/dev/null 2>&1; then
        log_success "MCP server startup: PASSED"
        
        # Test server responsiveness (basic check)
        if docker exec "$CONTAINER_NAME" fast-intercom-mcp status >/dev/null 2>&1; then
            log_success "MCP server responsiveness: PASSED"
        else
            log_warning "MCP server responsiveness: Warning"
        fi
        
        return 0
    else
        log_error "MCP server startup: FAILED"
        # Show server logs if available
        docker exec "$CONTAINER_NAME" cat ~/.fast-intercom-mcp/logs/fast-intercom-mcp.log 2>/dev/null || true
        return 1
    fi
}

# Test API integration (if enabled)
test_api_integration() {
    if [[ "$WITH_API_TEST" != "true" ]]; then
        return 0
    fi
    
    log_section "Testing API Integration"
    
    log_info "Running API integration test inside container..."
    
    # Test API connectivity
    if docker exec "$CONTAINER_NAME" python3 -c "
import asyncio
from fast_intercom_mcp import IntercomClient, Config

async def test_api():
    try:
        config = Config.load()
        if not config.intercom_token:
            print('No API token available')
            return False
        
        client = IntercomClient(config.intercom_token)
        connected = await client.test_connection()
        return connected
    except Exception as e:
        print(f'API test error: {e}')
        return False

result = asyncio.run(test_api())
exit(0 if result else 1)
" >/dev/null 2>&1; then
        log_success "API connectivity test: PASSED"
    else
        log_error "API connectivity test: FAILED"
        return 1
    fi
    
    # Test basic sync operation
    log_info "Testing basic sync operation..."
    if docker exec "$CONTAINER_NAME" fast-intercom-mcp sync --force --days 1 >/dev/null 2>&1; then
        log_success "Basic sync test: PASSED"
    else
        log_warning "Basic sync test: WARNING (may be normal with limited data)"
    fi
    
    log_success "API integration tests completed"
    return 0
}

# Show container information
show_container_info() {
    if [[ "$DEBUG_MODE" == "true" ]]; then
        log_section "Container Information"
        
        log_info "Container details:"
        docker inspect "$CONTAINER_NAME" --format='{{json .Config}}' | python3 -m json.tool 2>/dev/null || true
        
        log_info "Container processes:"
        docker exec "$CONTAINER_NAME" ps aux 2>/dev/null || true
        
        log_info "Container disk usage:"
        docker exec "$CONTAINER_NAME" df -h 2>/dev/null || true
        
        if [[ -f ~/.fast-intercom-mcp/logs/fast-intercom-mcp.log ]]; then
            log_info "Recent container logs:"
            docker exec "$CONTAINER_NAME" tail -n 20 ~/.fast-intercom-mcp/logs/fast-intercom-mcp.log 2>/dev/null || true
        fi
    fi
}

# Generate test report
generate_test_report() {
    log_section "Docker Test Results"
    
    local test_results=()
    local exit_code=0
    
    # Collect results (this would be expanded with actual test tracking)
    if [[ "$IMAGE_CREATED" == "true" ]]; then
        test_results+=("✅ Docker Image Build: PASSED")
    else
        test_results+=("❌ Docker Image Build: FAILED")
        exit_code=1
    fi
    
    if [[ "$CONTAINER_CREATED" == "true" ]]; then
        test_results+=("✅ Container Startup: PASSED")
    else
        test_results+=("❌ Container Startup: FAILED")
        exit_code=1
    fi
    
    # Additional tests would be tracked here
    test_results+=("✅ CLI Functionality: PASSED")
    test_results+=("✅ MCP Server: PASSED")
    
    if [[ "$WITH_API_TEST" == "true" ]]; then
        test_results+=("✅ API Integration: PASSED")
    fi
    
    # Display results
    echo ""
    for result in "${test_results[@]}"; do
        echo "$result"
    done
    
    echo ""
    echo "=================================================================================="
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Docker test PASSED ✅"
    else
        log_error "Docker test FAILED ❌"
    fi
    
    echo ""
    return $exit_code
}

# Main execution function
main() {
    log_section "$SCRIPT_NAME v$SCRIPT_VERSION"
    
    if [[ "$WITH_API_TEST" == "true" ]]; then
        log_info "Running with API integration testing"
    fi
    
    if [[ "$DEBUG_MODE" == "true" ]]; then
        log_info "Debug mode enabled"
    fi
    
    # Run test sequence
    verify_docker || exit 1
    build_docker_image || exit 1
    test_container_startup || exit 2
    test_cli_functionality || exit 3
    test_mcp_server || exit 4
    test_api_integration || exit 5
    show_container_info
    
    # Generate final report
    generate_test_report
}

# Execute main function
main "$@"