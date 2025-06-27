# FastIntercom MCP Server

[![Fast Check](https://github.com/evolsb/fast-intercom-mcp/actions/workflows/fast-check.yml/badge.svg)](https://github.com/evolsb/fast-intercom-mcp/actions/workflows/fast-check.yml)

High-performance Model Context Protocol (MCP) server for Intercom conversation analytics. Provides fast, local access to Intercom conversations through intelligent caching and background synchronization.

## Features

- **🚀 Fast Local Access**: Sub-100ms response times for conversation searches
- **🧠 Intelligent Sync**: Request-triggered background updates ensure fresh data
- **💾 Efficient Storage**: SQLite-based local storage (~2KB per conversation)
- **🔍 Powerful Search**: Natural language timeframes and text search
- **⚡ MCP Integration**: Direct integration with Claude Desktop and MCP clients

## Quick Start

### Installation

```bash
# Clone and install
git clone <repository-url>
cd fast-intercom-mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### Setup

```bash
# Initialize with your Intercom credentials
fast-intercom-mcp init

# Check status
fast-intercom-mcp status

# Sync conversation history
fast-intercom-mcp sync --force --days 7
```

### Claude Desktop Integration

Add to your Claude Desktop configuration (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "fast-intercom-mcp": {
      "command": "fast-intercom-mcp",
      "args": ["start"],
      "env": {
        "INTERCOM_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Usage

### CLI Commands

```bash
fast-intercom-mcp status              # Show server status and statistics
fast-intercom-mcp sync                # Incremental sync of recent conversations  
fast-intercom-mcp sync --force --days 7  # Force sync last 7 days
fast-intercom-mcp start               # Start MCP server
fast-intercom-mcp logs                # View recent log entries
fast-intercom-mcp reset               # Reset all data
```

### MCP Tools

Once connected to Claude Desktop, you can ask questions like:

- "Search for conversations about billing in the last 7 days"
- "Show me customer conversations from yesterday" 
- "What's the status of the FastIntercom server?"
- "Get conversation details for ID 123456789"

## Configuration

### Environment Variables

```bash
INTERCOM_ACCESS_TOKEN=your_token_here
FASTINTERCOM_LOG_LEVEL=INFO
FASTINTERCOM_MAX_SYNC_AGE_MINUTES=5
FASTINTERCOM_BACKGROUND_SYNC_INTERVAL=10
```

### Configuration File

Located at `~/.fast-intercom-mcp/config.json`:

```json
{
  "log_level": "INFO",
  "max_sync_age_minutes": 5,
  "background_sync_interval_minutes": 10,
  "initial_sync_days": 30
}
```

## Architecture

### Intelligent Sync Strategy

FastIntercom uses a sophisticated caching strategy:

1. **Immediate Response**: MCP requests return data instantly from local cache
2. **Background Sync**: Stale timeframes trigger background updates
3. **Smart Triggers**: System learns from request patterns to optimize sync timing
4. **Fresh Data**: Next request gets updated data from background sync

### Components

- **Database**: SQLite with optimized schema for fast searches
- **Sync Service**: Background service with intelligent refresh logic  
- **MCP Server**: Model Context Protocol implementation
- **CLI Interface**: Command-line tools for management and monitoring

## Development

### Testing

#### Quick Tests
```bash
# Unit tests
pytest tests/

# Integration test (requires API key)
./scripts/run_integration_test.sh

# Docker test
./scripts/test_docker_install.sh
```

#### Comprehensive Testing
```bash
# Full unit test suite with coverage
pytest tests/ --cov=fast_intercom_mcp

# Integration test with performance report
./scripts/run_integration_test.sh --performance-report

# Docker clean install test
./scripts/test_docker_install.sh --with-api-test

# Performance benchmarking
./scripts/run_performance_test.sh
```

#### CI/CD Integration
- **Fast Check**: Runs on every PR (unit tests, linting, imports)
- **Integration Test**: Manual/weekly trigger with real API data
- **Docker Test**: On releases and deployment validation

For detailed testing procedures, see:
- [`docs/TESTING.md`](docs/TESTING.md) - Complete testing guide
- [`docs/INTEGRATION_TESTING.md`](docs/INTEGRATION_TESTING.md) - Integration test procedures
- [`scripts/README.md`](scripts/README.md) - Test script documentation

### Local Development

```bash
# Install in development mode
pip install -e .

# Run with verbose logging
fast-intercom-mcp --verbose status

# Monitor logs in real-time
tail -f ~/.fast-intercom-mcp/logs/fast-intercom-mcp.log
```

## Performance

### Typical Performance Metrics

- **Response Time**: <100ms for cached queries
- **Storage Efficiency**: ~2KB per conversation average
- **Sync Speed**: 10-50 conversations/second
- **Memory Usage**: <100MB for server process

### Storage Requirements

- **Small workspace**: 100-500 conversations, ~5-25 MB
- **Medium workspace**: 1,000-5,000 conversations, ~50-250 MB
- **Large workspace**: 10,000+ conversations, ~500+ MB

## Troubleshooting

### Common Issues

**Connection Failed**
- Verify your Intercom access token
- Check token permissions (read conversations required)
- Test: `curl -H "Authorization: Bearer YOUR_TOKEN" https://api.intercom.io/me`

**Database Locked**
- Stop any running FastIntercom processes: `ps aux | grep fast-intercom-mcp`
- Check log file: `~/.fast-intercom-mcp/logs/fast-intercom-mcp.log`

**MCP Server Not Responding**
- Verify Claude Desktop config JSON syntax
- Restart Claude Desktop after configuration changes
- Check that the `fast-intercom-mcp` command is available in PATH

### Debug Mode

```bash
fast-intercom-mcp --verbose start    # Enable verbose logging
export FASTINTERCOM_LOG_LEVEL=DEBUG  # Set debug level
```

## API Reference

### MCP Tools

#### `search_conversations`
Search conversations with flexible filters.

**Parameters:**
- `query` (string): Text to search in conversation messages
- `timeframe` (string): Natural language timeframe ("last 7 days", "this month", etc.)
- `customer_email` (string): Filter by specific customer email
- `limit` (integer): Maximum conversations to return (default: 50)

#### `get_conversation`
Get full details of a specific conversation.

**Parameters:**
- `conversation_id` (string, required): Intercom conversation ID

#### `get_server_status`
Get server status and statistics.

**Parameters:** None

#### `sync_conversations`
Trigger manual conversation sync.

**Parameters:**
- `force` (boolean): Force full sync even if recent data exists

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: This README and inline code documentation
- **Logs**: Check `~/.fast-intercom-mcp/logs/fast-intercom-mcp.log` for detailed information