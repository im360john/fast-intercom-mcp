# FastIntercom MCP Server - Docker Deployment

This document explains how to deploy FastIntercom MCP Server using Docker for both local and remote deployments.

## Quick Start

### 1. Environment Setup

Copy the environment template:
```bash
cp docker/.env.example .env
```

Edit `.env` and set your Intercom token:
```bash
INTERCOM_ACCESS_TOKEN=your_token_here
FASTINTERCOM_INITIAL_SYNC_DAYS=90  # or 0 for ALL history
```

### 2. Deploy with Docker Compose

```bash
# Start the service
docker-compose up -d

# Check status
docker-compose exec fastintercom python -m fast_intercom_mcp.cli status

# View logs
docker-compose logs -f fastintercom
```

### 3. Local MCP Integration

For local Claude Desktop integration, the MCP server runs in stdio mode by default. Update your `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fast-intercom-mcp": {
      "command": "docker",
      "args": ["exec", "-i", "fastintercom-mcp", "python", "-m", "fast_intercom_mcp.cli", "start"],
      "env": {
        "INTERCOM_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Deployment Options

### Local Development
- Use docker-compose for easy setup
- Data persists in Docker volumes
- Low latency for local MCP requests

### Remote Deployment
- Expose port 8000 for remote MCP access
- Configure networking and security
- Use production-grade reverse proxy

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `INTERCOM_ACCESS_TOKEN` | Required | Your Intercom API token |
| `FASTINTERCOM_INITIAL_SYNC_DAYS` | 30 | Days of history to sync (0 = ALL) |
| `FASTINTERCOM_MAX_SYNC_AGE_MINUTES` | 5 | Trigger sync if data is stale |
| `FASTINTERCOM_BACKGROUND_SYNC_INTERVAL` | 10 | Background sync interval (minutes) |
| `FASTINTERCOM_LOG_LEVEL` | INFO | Logging level |

### Persistent Data

Docker volumes store:
- `/data` - Database and user data
- `/config` - Configuration files  
- `/var/log/fastintercom` - Application logs

### Health Monitoring

The container includes health checks:
```bash
docker ps  # Check health status
docker-compose ps  # Check service status
```

## Testing Docker Installation

### Automated Testing

FastIntercom includes comprehensive Docker installation tests to verify deployment integrity:

```bash
# Run complete Docker installation test
./scripts/test_docker_install.sh

# Run with API integration (requires INTERCOM_ACCESS_TOKEN)
INTERCOM_ACCESS_TOKEN=your_token_here ./scripts/test_docker_install.sh

# Test Docker Compose deployment
docker-compose -f docker-compose.test.yml up --build
```

### Test Coverage

The automated tests verify:
- ✅ Docker image builds successfully
- ✅ Container starts and passes health checks
- ✅ Intercom API connection (when token provided)
- ✅ MCP server responds correctly
- ✅ Docker Compose deployment works
- ✅ Persistent data storage functions
- ✅ Security configuration (non-root user, etc.)
- ✅ Performance within resource limits
- ✅ Clean shutdown and cleanup

### Manual Verification

For production deployments, manually verify:

1. **Environment Variables**: All required variables are set
2. **Network Security**: Only necessary ports exposed
3. **Persistent Volumes**: Data survives container restarts
4. **Resource Limits**: Memory and CPU usage within bounds
5. **Log Output**: No errors in container logs
6. **API Connectivity**: Intercom API responses working

### Performance Benchmarks

Expected performance metrics:
- **Image Size**: ~200-300MB
- **Memory Usage**: <512MB under normal load
- **Startup Time**: <60 seconds
- **Health Check**: Responds within 10 seconds

## Troubleshooting

### Common Issues

#### Build Failures
```bash
# Clean build cache and retry
docker system prune -f
docker build --no-cache -t fastintercom-mcp .
```

#### Health Check Failures  
```bash
# Check container logs
docker logs fastintercom-mcp

# Manual health check
docker exec fastintercom-mcp python -m fast_intercom_mcp.cli status
```

#### API Connection Issues
```bash
# Verify token is set
docker exec fastintercom-mcp env | grep INTERCOM

# Test API connectivity
docker exec fastintercom-mcp python -c "
from fast_intercom_mcp.intercom_client import IntercomClient
client = IntercomClient()
print('API Status:', client.test_connection())
"
```

### Permission Issues
If you encounter permission issues, ensure the fastintercom user has access to mounted volumes:

```bash
# Check file permissions
docker exec fastintercom-mcp ls -la /data /config

# Fix permissions if needed
docker exec --user root fastintercom-mcp chown -R fastintercom:fastintercom /data /config
```

### Memory Usage
The container is limited to 512MB RAM by default. Monitor and adjust if needed:

```bash
# Monitor resource usage
docker stats fastintercom-mcp

# Adjust in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G  # Increase if needed
```

### Network Access
For remote deployments, uncomment the ports section in docker-compose.yml and configure your firewall appropriately:

```yaml
ports:
  - "8000:8000"  # Expose HTTP MCP port
```

### Testing in CI/CD

The Docker install test can be integrated into your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Test Docker Installation
  run: |
    chmod +x scripts/test_docker_install.sh
    ./scripts/test_docker_install.sh
```

### Debugging Steps

1. **Check Docker Environment**:
   ```bash
   docker --version
   docker-compose --version
   docker info
   ```

2. **Verify Image Build**:
   ```bash
   docker build -t fastintercom-test .
   docker run --rm fastintercom-test python -m fast_intercom_mcp.cli --help
   ```

3. **Test Compose Configuration**:
   ```bash
   docker-compose config
   docker-compose -f docker-compose.test.yml config
   ```

4. **Clean Installation Test**:
   ```bash
   # Full clean test
   ./scripts/test_docker_install.sh --cleanup
   ./scripts/test_docker_install.sh
   ```