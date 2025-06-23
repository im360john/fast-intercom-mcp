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

## Troubleshooting

### Permission Issues
If you encounter permission issues, ensure the fastintercom user has access to mounted volumes.

### Memory Usage
The container is limited to 512MB RAM by default. Adjust in docker-compose.yml if needed.

### Network Access
For remote deployments, uncomment the ports section in docker-compose.yml and configure your firewall appropriately.