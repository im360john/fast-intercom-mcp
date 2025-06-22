# FastIntercomMCP - Technical Specification

**Version:** 1.0  
**Status:** Planning Phase  
**Repository:** TBD (`github.com/[username]/FastIntercomMCP`)

## 🎯 Project Overview

FastIntercomMCP is a high-performance Model Context Protocol (MCP) server that provides lightning-fast analytics over Intercom conversation data by maintaining a local database cache.

### Key Value Propositions
- **100x faster queries** - Sub-50ms response times vs 5+ seconds with Intercom REST API
- **Unlimited analytics** - Complex SQL queries impossible with REST API rate limits
- **Cost optimization** - Eliminate per-query API costs after initial sync
- **MCP native** - Works with Claude Desktop, Cursor, and any MCP-compatible client

## 🏗️ Architecture

### High-Level Design
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │ ←→ │  FastIntercomMCP │ ←→ │ Local Database  │
│ (Claude, etc.)  │    │     Server       │    │  (PostgreSQL)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ↓
                       ┌──────────────────┐
                       │  Intercom API    │
                       │  (Sync Process)  │
                       └──────────────────┘
```

### Core Components

#### 1. **Sync Engine**
- **Full sync**: Initial load of all conversations via Intercom API
- **Incremental sync**: Periodic updates of new/modified conversations
- **Webhook support**: Real-time updates when available
- **Rate limit handling**: Respects Intercom's 83 requests/10 seconds limit

#### 2. **Database Layer**
- **Primary**: PostgreSQL with optimized indexes for time-based queries
- **Schema**: Normalized conversation, message, and customer data
- **Full-text search**: PostgreSQL's built-in text search capabilities
- **Analytics views**: Pre-computed aggregations for common queries

#### 3. **MCP Server**
- **JSON-RPC 2.0**: Standards-compliant MCP implementation
- **Tool interface**: Exposes conversation search and analysis tools
- **Connection management**: Persistent connections with cleanup
- **Error handling**: Graceful degradation and detailed error messages

#### 4. **Query Engine**
- **SQL generation**: Convert MCP tool calls to optimized SQL queries  
- **Result formatting**: Transform database results to MCP-compatible responses
- **Caching layer**: Query result caching for repeated requests
- **Security**: SQL injection prevention and query validation

## 🔧 Technical Specifications

### Database Schema

#### Conversations Table
```sql
CREATE TABLE conversations (
    id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    state VARCHAR(20) NOT NULL, -- open, closed, snoozed
    priority VARCHAR(10), -- not_priority, priority
    assignee_id VARCHAR(50),
    customer_id VARCHAR(50),
    tags TEXT[],
    conversation_rating INTEGER,
    team_assignee_id VARCHAR(50),
    statistics JSONB, -- response times, etc.
    raw_data JSONB -- full Intercom response
);

-- Optimized indexes
CREATE INDEX idx_conversations_created_at ON conversations (created_at DESC);
CREATE INDEX idx_conversations_state ON conversations (state);
CREATE INDEX idx_conversations_customer_id ON conversations (customer_id);
CREATE INDEX idx_conversations_tags ON conversations USING GIN (tags);
CREATE INDEX idx_conversations_fulltext ON conversations USING GIN (to_tsvector('english', raw_data::text));
```

#### Messages Table
```sql
CREATE TABLE conversation_messages (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id VARCHAR(50) REFERENCES conversations(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    author_type VARCHAR(20), -- user, admin, bot
    author_id VARCHAR(50),
    message_type VARCHAR(20), -- comment, note, assignment
    body TEXT,
    attachments JSONB,
    raw_data JSONB
);

-- Optimized indexes
CREATE INDEX idx_messages_conversation_id ON conversation_messages (conversation_id);
CREATE INDEX idx_messages_created_at ON conversation_messages (created_at DESC);
CREATE INDEX idx_messages_fulltext ON conversation_messages USING GIN (to_tsvector('english', body));
```

#### Customers Table
```sql
CREATE TABLE customers (
    id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE,
    signed_up_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    custom_attributes JSONB,
    tags TEXT[],
    raw_data JSONB
);

-- Optimized indexes
CREATE INDEX idx_customers_email ON customers (email);
CREATE INDEX idx_customers_created_at ON customers (created_at DESC);
CREATE INDEX idx_customers_tags ON customers USING GIN (tags);
```

### MCP Tools Interface

#### Tool: search_conversations
```json
{
  "name": "search_conversations",
  "description": "Search and filter conversations with advanced analytics",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string", 
        "description": "Natural language query or keywords"
      },
      "timeframe": {
        "type": "object",
        "properties": {
          "start_date": {"type": "string", "format": "date-time"},
          "end_date": {"type": "string", "format": "date-time"},
          "relative": {"type": "string", "enum": ["today", "yesterday", "last_7_days", "last_30_days", "last_90_days"]}
        }
      },
      "filters": {
        "type": "object",
        "properties": {
          "state": {"type": "array", "items": {"type": "string"}},
          "priority": {"type": "string"},
          "assignee_id": {"type": "string"},
          "customer_id": {"type": "string"},
          "tags": {"type": "array", "items": {"type": "string"}},
          "rating": {"type": "integer", "minimum": 1, "maximum": 5}
        }
      },
      "aggregation": {
        "type": "object",
        "properties": {
          "group_by": {"type": "string", "enum": ["day", "week", "month", "assignee", "tag", "priority"]},
          "metrics": {"type": "array", "items": {"type": "string", "enum": ["count", "avg_response_time", "resolution_rate"]}}
        }
      },
      "limit": {"type": "integer", "default": 50, "maximum": 1000},
      "offset": {"type": "integer", "default": 0}
    }
  }
}
```

#### Tool: analyze_conversations
```json
{
  "name": "analyze_conversations",
  "description": "Perform advanced analytics on conversation data",
  "inputSchema": {
    "type": "object",
    "properties": {
      "analysis_type": {
        "type": "string",
        "enum": ["sentiment_trends", "topic_analysis", "performance_metrics", "customer_satisfaction"]
      },
      "timeframe": {"$ref": "#/components/timeframe"},
      "filters": {"$ref": "#/components/filters"},
      "dimensions": {
        "type": "array",
        "items": {"type": "string", "enum": ["assignee", "team", "tag", "priority", "time_period"]}
      }
    }
  }
}
```

#### Tool: get_conversation_details
```json
{
  "name": "get_conversation_details", 
  "description": "Get full details of a specific conversation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "conversation_id": {"type": "string", "description": "Intercom conversation ID"},
      "include_messages": {"type": "boolean", "default": true},
      "include_customer": {"type": "boolean", "default": true}
    },
    "required": ["conversation_id"]
  }
}
```

### Performance Specifications

#### Target Performance Metrics
- **Query response time**: <50ms for standard searches
- **Complex analytics**: <200ms for aggregation queries
- **Full-text search**: <100ms across 40k+ conversations
- **Sync performance**: 1000+ conversations/minute during initial sync
- **Memory usage**: <500MB for 40k conversations with full text
- **Concurrent requests**: 100+ simultaneous MCP connections

#### Caching Strategy
- **Query result cache**: Redis/in-memory cache with 5-minute TTL
- **Connection pooling**: PostgreSQL connection pool (10-50 connections)
- **Prepared statements**: Pre-compiled SQL for common query patterns
- **Materialized views**: Pre-computed aggregations for dashboard queries

## 🔌 Integration Patterns

### MCP Client Integration
```python
# Example usage from any MCP client
import mcp

client = mcp.Client("http://localhost:8000")

# Fast local queries instead of slow API calls
results = await client.call_tool("search_conversations", {
    "timeframe": {"relative": "last_7_days"},
    "query": "authentication error",
    "aggregation": {"group_by": "day", "metrics": ["count"]}
})
```

### REST API Fallback
```python
# Hybrid mode: local when available, API when needed
class HybridIntercomClient:
    def __init__(self):
        self.mcp_client = MCPClient("http://localhost:8000")
        self.api_client = IntercomAPIClient()
    
    async def search(self, query):
        try:
            # Try local first (fast)
            return await self.mcp_client.search_conversations(query)
        except MCPConnectionError:
            # Fallback to API (slow but always available)
            return await self.api_client.search_conversations(query)
```

## 🚀 Deployment Options

### Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  fastintercom-db:
    image: postgres:15
    environment:
      POSTGRES_DB: intercom
      POSTGRES_USER: fastintercom
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  fastintercom-mcp:
    image: fastintercom-mcp:latest
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://fastintercom:${DB_PASSWORD}@fastintercom-db:5432/intercom
      INTERCOM_ACCESS_TOKEN: ${INTERCOM_ACCESS_TOKEN}
    depends_on:
      - fastintercom-db
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastintercom-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fastintercom-mcp
  template:
    spec:
      containers:
      - name: fastintercom-mcp
        image: fastintercom-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: fastintercom-secrets
              key: database-url
```

### Single Server Deployment
```bash
# Simple deployment on VPS/cloud instance
docker run -d \
  --name fastintercom-mcp \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://localhost/intercom \
  -e INTERCOM_ACCESS_TOKEN=your_token \
  fastintercom-mcp:latest
```

## 🔐 Security & Configuration

### Environment Variables
```bash
# Required
INTERCOM_ACCESS_TOKEN=your_intercom_token
DATABASE_URL=postgresql://user:pass@host:port/db

# Optional
MCP_PORT=8000
MCP_HOST=0.0.0.0
LOG_LEVEL=INFO
CACHE_TTL=300
MAX_CONNECTIONS=50
SYNC_INTERVAL=3600  # seconds

# Security
ALLOWED_ORIGINS=https://claude.ai,http://localhost:3000
API_KEY_HEADER=X-API-Key  # Optional API key protection
```

### Access Control
- **Origin validation**: Restrict MCP connections by origin
- **API key authentication**: Optional API key for additional security
- **Rate limiting**: Per-client request rate limiting
- **Query validation**: SQL injection prevention
- **Read-only mode**: Database connections with read-only permissions

## 📊 Monitoring & Observability

### Metrics
- **Query performance**: Response times, slow query detection
- **Database health**: Connection pool usage, query statistics
- **Sync status**: Last sync time, error rates, data freshness
- **MCP connections**: Active connections, request rates

### Logging
```json
{
  "timestamp": "2025-06-22T10:30:00Z",
  "level": "INFO",
  "component": "query_engine",
  "message": "Conversation search completed",
  "duration_ms": 45,
  "query_type": "search_conversations",
  "result_count": 127,
  "filters": {"timeframe": "last_7_days", "query": "billing issue"}
}
```

### Health Checks
- **HTTP endpoint**: `/health` for load balancer checks
- **Database connectivity**: PostgreSQL connection validation  
- **Sync status**: Last successful sync timestamp
- **MCP protocol**: Protocol version and capability checks

## 🧪 Testing Strategy (See Test Plan Document)

- **Unit tests**: Core components (sync, query, MCP protocol)
- **Integration tests**: Database operations, MCP client interactions
- **Performance tests**: Load testing, query optimization validation
- **End-to-end tests**: Full workflow from sync to MCP query
- **Security tests**: SQL injection, authentication, authorization

## 📈 Roadmap

### v1.0 (MVP)
- ✅ Basic conversation sync and storage
- ✅ Core MCP tools (search, analyze, get details)
- ✅ PostgreSQL backend with optimized schema
- ✅ Docker deployment
- ✅ Documentation and examples

### v1.1 (Performance)
- 🔄 Query result caching
- 🔄 Connection pooling optimization
- 🔄 Materialized views for analytics
- 🔄 Streaming responses for large result sets

### v1.2 (Features)
- 🔄 Real-time webhook sync
- 🔄 Advanced analytics (sentiment, topics)
- 🔄 Multi-tenant support
- 🔄 REST API endpoint (non-MCP clients)

### v2.0 (Enterprise)
- 🔄 Kubernetes operator
- 🔄 Multi-database support (MySQL, SQLite)
- 🔄 Advanced security (RBAC, audit logs)
- 🔄 Performance monitoring dashboard

---

**Status**: Specification complete, ready for implementation phase