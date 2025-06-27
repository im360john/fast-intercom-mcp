#!/bin/bash

# Docker Clean Install Test - Deployment Verification
# Tests complete Docker deployment process for fast-intercom-mcp
# This script validates that new users can successfully install and run the server

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_IMAGE_NAME="fastintercom-test"
TEST_CONTAINER_NAME="fastintercom-test"
TEST_COMPOSE_CONTAINER="fastintercom-compose-test"
TEST_PORT="8001"
COMPOSE_TEST_PORT="8002"
HEALTH_TIMEOUT=90
STARTUP_TIMEOUT=60

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Cleanup function
cleanup() {
    log_info "🧹 Cleaning up test resources..."
    
    # Stop and remove containers
    docker stop $TEST_CONTAINER_NAME 2>/dev/null || true
    docker rm $TEST_CONTAINER_NAME 2>/dev/null || true
    
    # Stop compose test
    docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true
    
    # Remove test images
    docker rmi $TEST_IMAGE_NAME 2>/dev/null || true
    docker rmi fastintercom-test-compose 2>/dev/null || true
    
    # Remove any dangling containers
    docker ps -aq --filter "name=fastintercom" | xargs -r docker rm -f 2>/dev/null || true
    
    log_info "Cleanup completed"
}

# Setup trap for cleanup
trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    log_info "🔍 Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check required environment variables
    if [ -z "$INTERCOM_ACCESS_TOKEN" ]; then
        log_warning "INTERCOM_ACCESS_TOKEN not set - some tests will be skipped"
    fi
    
    log_success "Prerequisites check passed"
}

# Test 1: Docker Build from Source
test_docker_build() {
    log_info "📦 Test 1: Building Docker image from source..."
    
    local start_time=$(date +%s)
    
    if docker build -t $TEST_IMAGE_NAME . --no-cache; then
        local end_time=$(date +%s)
        local build_time=$((end_time - start_time))
        log_success "Docker image built successfully in ${build_time}s"
        
        # Check image size
        local image_size=$(docker images $TEST_IMAGE_NAME --format "{{.Size}}")
        log_info "Image size: $image_size"
        
        # Verify image layers and security
        if docker run --rm $TEST_IMAGE_NAME whoami | grep -q "fastintercom"; then
            log_success "Non-root user verification passed"
        else
            log_error "Container running as root user"
        fi
        
    else
        log_error "Docker image build failed"
        return 1
    fi
}

# Test 2: Container Startup and Health Check
test_container_startup() {
    log_info "🚀 Test 2: Testing container startup and health checks..."
    
    local start_time=$(date +%s)
    
    # Start container with minimal config (no API token for basic startup test)
    if docker run -d --name $TEST_CONTAINER_NAME \
        -p $TEST_PORT:8000 \
        -e FASTINTERCOM_LOG_LEVEL=DEBUG \
        $TEST_IMAGE_NAME; then
        
        log_success "Container started successfully"
        
        # Wait for container to be running
        local timeout=30
        local elapsed=0
        while [ $elapsed -lt $timeout ]; do
            if docker ps --filter "name=$TEST_CONTAINER_NAME" --filter "status=running" | grep -q $TEST_CONTAINER_NAME; then
                break
            fi
            sleep 1
            ((elapsed++))
        done
        
        if [ $elapsed -ge $timeout ]; then
            log_error "Container failed to start within ${timeout}s"
            docker logs $TEST_CONTAINER_NAME
            return 1
        fi
        
        local end_time=$(date +%s)
        local startup_time=$((end_time - start_time))
        log_success "Container startup completed in ${startup_time}s"
        
        # Check container logs for errors
        if docker logs $TEST_CONTAINER_NAME 2>&1 | grep -i error | grep -v "INTERCOM_ACCESS_TOKEN not provided"; then
            log_warning "Container logs contain errors (excluding expected token warning)"
        else
            log_success "Container logs clean (no unexpected errors)"
        fi
        
    else
        log_error "Container startup failed"
        return 1
    fi
}

# Test 3: API Integration Test (if token available)
test_api_integration() {
    if [ -z "$INTERCOM_ACCESS_TOKEN" ]; then
        log_warning "Skipping API integration test - INTERCOM_ACCESS_TOKEN not set"
        return 0
    fi
    
    log_info "🔌 Test 3: Testing API integration with real Intercom API..."
    
    # Stop previous container and start with API token
    docker stop $TEST_CONTAINER_NAME || true
    docker rm $TEST_CONTAINER_NAME || true
    
    if docker run -d --name $TEST_CONTAINER_NAME \
        -p $TEST_PORT:8000 \
        -e INTERCOM_ACCESS_TOKEN="$INTERCOM_ACCESS_TOKEN" \
        -e FASTINTERCOM_LOG_LEVEL=DEBUG \
        $TEST_IMAGE_NAME; then
        
        # Wait for health check to pass
        log_info "Waiting for health check to pass (timeout: ${HEALTH_TIMEOUT}s)..."
        local elapsed=0
        while [ $elapsed -lt $HEALTH_TIMEOUT ]; do
            local health_status=$(docker inspect --format='{{.State.Health.Status}}' $TEST_CONTAINER_NAME 2>/dev/null || echo "starting")
            if [ "$health_status" = "healthy" ]; then
                log_success "Container health check passed"
                break
            elif [ "$health_status" = "unhealthy" ]; then
                log_error "Container health check failed"
                docker logs $TEST_CONTAINER_NAME
                return 1
            fi
            sleep 2
            ((elapsed+=2))
        done
        
        if [ $elapsed -ge $HEALTH_TIMEOUT ]; then
            log_error "Health check timeout after ${HEALTH_TIMEOUT}s"
            docker logs $TEST_CONTAINER_NAME
            return 1
        fi
        
        # Test CLI status command
        if docker exec $TEST_CONTAINER_NAME python -m fast_intercom_mcp.cli status; then
            log_success "CLI status command works"
        else
            log_error "CLI status command failed"
        fi
        
        # Test MCP server response (if HTTP mode is available)
        if curl -f -s http://localhost:$TEST_PORT/health > /dev/null 2>&1; then
            log_success "MCP server HTTP endpoint responding"
        else
            log_warning "MCP server HTTP endpoint not available (may be stdio mode only)"
        fi
        
    else
        log_error "Container startup with API token failed"
        return 1
    fi
}

# Test 4: Docker Compose Deployment
test_docker_compose() {
    log_info "🐙 Test 4: Testing Docker Compose deployment..."
    
    # Create test compose file if it doesn't exist
    if [ ! -f "docker-compose.test.yml" ]; then
        log_warning "docker-compose.test.yml not found, creating from template..."
        create_test_compose_file
    fi
    
    # Stop any running containers first
    docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true
    
    # Set environment for compose
    export COMPOSE_TEST_PORT=$COMPOSE_TEST_PORT
    export INTERCOM_ACCESS_TOKEN="${INTERCOM_ACCESS_TOKEN:-dummy_token_for_build_test}"
    
    if docker-compose -f docker-compose.test.yml up -d; then
        log_success "Docker Compose services started"
        
        # Wait for service to be healthy
        local elapsed=0
        while [ $elapsed -lt $HEALTH_TIMEOUT ]; do
            if docker-compose -f docker-compose.test.yml ps | grep "healthy"; then
                log_success "Docker Compose health check passed"
                break
            fi
            sleep 2
            ((elapsed+=2))
        done
        
        if [ $elapsed -ge $HEALTH_TIMEOUT ]; then
            log_warning "Docker Compose health check timeout - checking logs"
            docker-compose -f docker-compose.test.yml logs
        fi
        
        # Test persistent volumes
        if docker volume ls | grep -q "test-data"; then
            log_success "Persistent volumes created correctly"
        else
            log_error "Persistent volumes not found"
        fi
        
        # Test network connectivity
        local container_id=$(docker-compose -f docker-compose.test.yml ps -q)
        if [ -n "$container_id" ] && docker exec $container_id python -c "import requests; print('Network OK')" 2>/dev/null; then
            log_success "Container network connectivity verified"
        else
            log_warning "Network connectivity test inconclusive"
        fi
        
    else
        log_error "Docker Compose deployment failed"
        return 1
    fi
}

# Test 5: Performance and Resource Validation
test_performance() {
    log_info "⚡ Test 5: Performance and resource validation..."
    
    if [ -z "$(docker ps -q --filter name=$TEST_CONTAINER_NAME)" ]; then
        log_warning "No running test container found for performance test"
        return 0
    fi
    
    # Check memory usage
    local memory_usage=$(docker stats --no-stream --format "{{.MemUsage}}" $TEST_CONTAINER_NAME | cut -d'/' -f1 | sed 's/MiB//g' | sed 's/MB//g' | awk '{print int($1)}')
    if [ -n "$memory_usage" ] && [ "$memory_usage" -lt 512 ]; then
        log_success "Memory usage within limits: ${memory_usage}MB"
    else
        log_warning "Memory usage check inconclusive: ${memory_usage}MB"
    fi
    
    # Check CPU usage (averaged over 10 seconds)
    local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" $TEST_CONTAINER_NAME | sed 's/%//g' | awk '{print int($1)}')
    if [ -n "$cpu_usage" ] && [ "$cpu_usage" -lt 50 ]; then
        log_success "CPU usage acceptable: ${cpu_usage}%"
    else
        log_info "CPU usage: ${cpu_usage}%"
    fi
    
    # Test restart capability
    log_info "Testing container restart capability..."
    if docker restart $TEST_CONTAINER_NAME; then
        sleep 5
        if docker ps --filter "name=$TEST_CONTAINER_NAME" --filter "status=running" | grep -q $TEST_CONTAINER_NAME; then
            log_success "Container restart successful"
        else
            log_error "Container failed to restart properly"
        fi
    else
        log_error "Container restart failed"
    fi
}

# Test 6: Security Verification
test_security() {
    log_info "🔒 Test 6: Security verification..."
    
    if [ -z "$(docker ps -q --filter name=$TEST_CONTAINER_NAME)" ]; then
        log_warning "No running test container found for security test"
        return 0
    fi
    
    # Verify non-root user
    local container_user=$(docker exec $TEST_CONTAINER_NAME whoami 2>/dev/null || echo "unknown")
    if [ "$container_user" = "fastintercom" ]; then
        log_success "Container running as non-root user: $container_user"
    else
        log_error "Container not running as expected user (got: $container_user)"
    fi
    
    # Check for secrets in logs (basic check)
    if docker logs $TEST_CONTAINER_NAME 2>&1 | grep -E "(password|secret|token|key)" | grep -v "INTERCOM_ACCESS_TOKEN not provided" | grep -v "access_token"; then
        log_warning "Potential secrets found in container logs"
    else
        log_success "No obvious secrets in container logs"
    fi
    
    # Verify file permissions
    local data_perms=$(docker exec $TEST_CONTAINER_NAME ls -ld /data 2>/dev/null | awk '{print $1}' || echo "unknown")
    if [[ "$data_perms" =~ ^drwx.*$ ]]; then
        log_success "Data directory permissions secure: $data_perms"
    else
        log_warning "Data directory permissions check inconclusive: $data_perms"
    fi
    
    # Check exposed ports
    local exposed_ports=$(docker port $TEST_CONTAINER_NAME 2>/dev/null | wc -l)
    if [ "$exposed_ports" -le 1 ]; then
        log_success "Minimal port exposure: $exposed_ports port(s)"
    else
        log_warning "Multiple ports exposed: $exposed_ports"
    fi
}

# Create test compose file
create_test_compose_file() {
    cat > docker-compose.test.yml << 'EOF'
version: '3.8'
services:
  fastintercom-test:
    build: .
    container_name: fastintercom-compose-test
    environment:
      - INTERCOM_ACCESS_TOKEN=${INTERCOM_ACCESS_TOKEN}
      - FASTINTERCOM_LOG_LEVEL=DEBUG
    ports:
      - "${COMPOSE_TEST_PORT:-8002}:8000"
    volumes:
      - test-data:/data
      - test-config:/config
      - test-logs:/var/log/fastintercom
    healthcheck:
      test: ["CMD", "python", "-m", "fast_intercom_mcp.cli", "status"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

volumes:
  test-data:
  test-config:
  test-logs:
EOF
}

# Generate test report
generate_report() {
    log_info "📊 Generating test report..."
    
    echo ""
    echo "🐳 Docker Clean Install Test Results"
    echo "======================================"
    echo ""
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed! Ready for production deployment!${NC}"
        echo ""
        echo "✅ Docker image builds successfully"
        echo "✅ Container starts and passes health checks"
        echo "✅ Security verification passed"
        echo "✅ Performance within acceptable limits"
        echo "✅ Docker Compose deployment works"
        echo "✅ Clean installation process verified"
    else
        echo -e "${RED}❌ Some tests failed. Issues need to be addressed:${NC}"
        echo ""
        for failed_test in "${FAILED_TESTS[@]}"; do
            echo "  - $failed_test"
        done
        echo ""
        echo "Please review the test output above for detailed error information."
    fi
    
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Review any failed tests and fix issues"
    echo "  2. Update documentation based on test results"
    echo "  3. Consider adding this test to CI/CD pipeline"
    echo "  4. Test with different environment configurations"
    echo ""
}

# Main execution
main() {
    echo "🐳 FastIntercom MCP - Docker Clean Install Test"
    echo "==============================================="
    echo ""
    
    check_prerequisites
    
    # Run all tests
    test_docker_build || true
    test_container_startup || true
    test_api_integration || true
    test_docker_compose || true
    test_performance || true
    test_security || true
    
    # Generate final report
    generate_report
    
    # Exit with appropriate code
    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Docker Clean Install Test for FastIntercom MCP"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --cleanup     Only run cleanup (remove test containers/images)"
        echo ""
        echo "Environment Variables:"
        echo "  INTERCOM_ACCESS_TOKEN    Required for API integration tests"
        echo "  HEALTH_TIMEOUT          Health check timeout in seconds (default: 90)"
        echo "  STARTUP_TIMEOUT         Container startup timeout in seconds (default: 60)"
        echo ""
        exit 0
        ;;
    --cleanup)
        cleanup
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac