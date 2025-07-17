# Fast-Intercom-MCP Enhancement Implementation

This document describes the implementation of enhancements to the Fast-Intercom-MCP server, including PostgreSQL support, Streamable HTTP transport, Articles/Tickets integration, and intelligent response truncation.

## Overview of Enhancements

### 1. PostgreSQL Migration
- Migrated from SQLite to PostgreSQL for better performance and scalability
- Added full-text search capabilities using PostgreSQL's tsvector
- Implemented connection pooling with asyncpg

### 2. Streamable HTTP Transport
- Implemented FastMCP server with stateless HTTP transport
- Replaced SSE with simpler HTTP responses for better compatibility
- Added lifecycle management for proper resource cleanup

### 3. Context Window Management
- Intelligent response truncation using tiktoken for token counting
- Automatic truncation to fit within AI agent context windows
- Helpful instructions provided when responses are truncated

### 4. Enhanced API Integration
- Rate-limited Intercom API client (900 calls/minute)
- Support for Articles API (search, list, get)
- Support for Tickets API (search, get, list types/states)
- Direct API queries for tickets (no local storage required)

### 5. Enhanced MCP Tools
- **Conversations**: Search with natural language timeframes, get details
- **Articles**: Search, list, and retrieve full content
- **Tickets**: Search, get details, list types and states
- **Sync**: Manual sync of conversations and articles to local DB

## Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/fast-intercom-mcp.git
cd fast-intercom-mcp
cp .env.example .env
# Edit .env with your configuration
```

### 2. Configure Environment
Edit `.env` file:
```env
INTERCOM_ACCESS_TOKEN=your_token_here
DATABASE_URL=postgresql://localhost/intercom_mcp
POSTGRES_PASSWORD=secure_password
```

### 3. Run with Docker Compose
```bash
docker-compose up -d
```

### 4. Verify Installation
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Configuration

### Environment Variables
- `INTERCOM_ACCESS_TOKEN`: Your Intercom API token (required)
- `DATABASE_URL`: PostgreSQL connection string
- `HTTP_HOST`: Server host (default: 0.0.0.0)
- `HTTP_PORT`: Server port (default: 8000)
- `MAX_RESPONSE_TOKENS`: Maximum tokens per response (default: 40000)
- `MAX_ITEMS_PER_SEARCH`: Maximum items to return (default: 20)

### Database Schema
The PostgreSQL schema includes:
- `conversations`: Full-text searchable conversation data
- `articles`: Help center articles with search capabilities
- `sync_metadata`: Tracks sync status and history

## Usage Examples

### Search Conversations
```json
{
  "tool": "search_conversations",
  "arguments": {
    "query": "billing issue",
    "timeframe": "last 7 days",
    "limit": 10
  }
}
```

### Search Articles
```json
{
  "tool": "search_articles",
  "arguments": {
    "query": "password reset",
    "limit": 5,
    "include_preview": true
  }
}
```

### Search Tickets
```json
{
  "tool": "search_tickets",
  "arguments": {
    "customer_email": "user@example.com",
    "ticket_state": "open",
    "limit": 15
  }
}
```

## Response Truncation

When responses exceed the configured token limit, the system automatically:
1. Truncates the response to fit within the limit
2. Provides metadata about truncation
3. Offers suggestions for refining searches

Example truncated response:
```json
{
  "data": [...],
  "meta": {
    "total_items": 100,
    "returned_items": 20,
    "truncated": true,
    "estimated_tokens": 38500
  },
  "assistant_instruction": "⚠️ Response truncated..."
}
```

## Architecture

### Components
1. **FastMCP Server** (`server.py`): HTTP transport layer
2. **API Client** (`api/client.py`): Rate-limited Intercom API access
3. **Context Manager** (`utils/context_window.py`): Token counting and truncation
4. **MCP Tools** (`tools/`): Enhanced tool implementations
5. **Database** (`db/connection.py`): AsyncPG connection pooling

### Data Flow
1. MCP request → FastMCP server
2. Tool execution → API client or database query
3. Response → Context window truncation
4. Truncated response → AI agent

## Testing

Run tests:
```bash
pytest tests/unit/test_context_window.py
```

## Production Deployment

### Using Docker
```bash
docker build -t fast-intercom-mcp .
docker run -d \
  --name fast-intercom-mcp \
  -p 8000:8000 \
  --env-file .env \
  fast-intercom-mcp
```

### Scaling Considerations
- The stateless HTTP design allows horizontal scaling
- Use a load balancer to distribute requests
- Share the PostgreSQL database between instances
- Consider Redis for distributed rate limiting

## Monitoring

- Health check endpoint: `POST /mcp` with `get_sync_status` tool
- Log level configurable via `FASTINTERCOM_LOG_LEVEL`
- Metrics available: token usage, truncation frequency, API rate limit usage

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check DATABASE_URL format
   - Ensure PostgreSQL is running
   - Verify network connectivity

2. **Rate Limit Errors**
   - Reduce concurrent requests
   - Increase rate limit window
   - Check Intercom API quota

3. **Large Response Truncation**
   - Reduce MAX_ITEMS_PER_SEARCH
   - Use more specific search filters
   - Enable preview mode for lists

## Future Enhancements

- [ ] Redis-based distributed rate limiting
- [ ] Webhook support for real-time updates
- [ ] Advanced caching strategies
- [ ] GraphQL API support
- [ ] Custom field mapping

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details