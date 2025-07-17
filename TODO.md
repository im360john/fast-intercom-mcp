# Fast-Intercom-MCP Enhancement TODO List

## Phase 1: Database Migration from SQLite to PostgreSQL
- [ ] Update dependencies in pyproject.toml
- [ ] Create database schema migrations
- [ ] Implement database connection manager
- [ ] Update existing models to use PostgreSQL

## Phase 2: Streamable HTTP Transport Implementation
- [ ] Update server.py for streamable HTTP
- [ ] Create configuration management
- [ ] Implement lifespan management
- [ ] Test HTTP transport

## Phase 3: Context Window Management
- [ ] Implement token counter using tiktoken
- [ ] Create response truncator
- [ ] Add truncation logic to all tools
- [ ] Create helper functions for response formatting

## Phase 4: Intercom API Client
- [ ] Implement rate limiter
- [ ] Create API client with all endpoints
- [ ] Add error handling
- [ ] Test API integration

## Phase 5: MCP Tools Implementation
- [ ] Enhance conversation tools
- [ ] Implement article tools
- [ ] Implement ticket tools
- [ ] Enhance sync tools
- [ ] Add helper functions

## Phase 6: Deployment Configuration
- [ ] Create Dockerfile
- [ ] Create docker-compose.yml
- [ ] Add environment configuration
- [ ] Create deployment scripts

## Phase 7: Testing
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Test context window management
- [ ] Test rate limiting

## Phase 8: Documentation
- [ ] Create API documentation
- [ ] Write deployment guide
- [ ] Add usage examples
- [ ] Update README

## Current Status
Starting with Phase 1: Database Migration