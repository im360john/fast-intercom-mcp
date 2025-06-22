# FastIntercomMCP - Project Transition Plan

**Objective**: Extract FastIntercomMCP as a standalone project while maintaining current ask-intercom functionality

**Timeline**: 2-3 days for clean extraction and integration  
**Risk Level**: Low (reversible at any step)  
**Strategy**: Branch-based development with fallback preservation

## 🗺️ Transition Overview

### Phase 1: Preparation & Planning ✅
- [x] Specification written
- [x] Competitive analysis complete  
- [x] Test plan designed
- [x] Architecture validated

### Phase 2: Code Extraction (Next)
- [ ] Create FastIntercomMCP repository
- [ ] Extract relevant code from ask-intercom
- [ ] Set up standalone project structure
- [ ] Implement MCP server

### Phase 3: Integration & Testing
- [ ] Modify ask-intercom to use FastIntercomMCP
- [ ] Test integration thoroughly
- [ ] Performance validation
- [ ] Deploy and verify

### Phase 4: Finalization
- [ ] Documentation and examples
- [ ] Open source release
- [ ] Community setup

## 📋 Detailed Step-by-Step Plan

### Step 1: Repository Setup

#### 1.1 Create New Repository
```bash
# Create new repository on GitHub
# Repository name: FastIntercomMCP
# Description: High-performance MCP server for Intercom conversation analytics
# Public repository with MIT license

# Clone locally
cd ~/Developer
git clone https://github.com/[username]/FastIntercomMCP.git
cd FastIntercomMCP
```

#### 1.2 Initial Project Structure
```bash
# Create directory structure
mkdir -p {src,tests,docs,docker,examples}
mkdir -p tests/{unit,integration,performance,security,e2e,chaos}
mkdir -p src/{sync,query,mcp,models}
mkdir -p docker/{development,production}
mkdir -p examples/{python,typescript,curl}

# Create initial files
touch README.md
touch requirements.txt
touch pyproject.toml
touch Dockerfile
touch docker-compose.yml
touch .env.example
touch .gitignore
touch .pre-commit-config.yaml
```

#### 1.3 Copy Documentation
```bash
# Copy our planning documents to new repo
cp ~/Developer/ask-intercom-test/docs/FastIntercomMCP-*.md ./docs/
mv docs/FastIntercomMCP-Spec.md docs/SPECIFICATION.md
mv docs/FastIntercomMCP-Competitive-Analysis.md docs/COMPETITIVE_ANALYSIS.md
mv docs/FastIntercomMCP-Test-Plan.md docs/TEST_PLAN.md
```

### Step 2: Code Extraction from ask-intercom

#### 2.1 Identify Components to Extract
**From current ask-intercom project:**

```bash
# Files to extract/adapt:
src/intercom_client.py        # → src/sync/intercom_client.py (sync logic only)
src/models.py                 # → src/models/conversations.py
src/config.py                 # → src/config.py (database config)
src/logger.py                 # → src/logger.py
src/mcp/universal_adapter.py  # → src/mcp/adapter.py (adapt for standalone)
src/mcp/client_fixed.py       # → Not needed (we're building the server)
src/mcp/intercom_mcp_server.py # → src/mcp/server.py (main server)
```

#### 2.2 Extract Intercom Sync Logic
```bash
cd ~/Developer/ask-intercom-test

# Create extraction branch
git checkout -b extract-for-fastintercom

# Copy files to FastIntercomMCP project
cp src/logger.py ~/Developer/FastIntercomMCP/src/
cp src/config.py ~/Developer/FastIntercomMCP/src/
cp src/models.py ~/Developer/FastIntercomMCP/src/models/conversations.py

# Extract sync logic from intercom_client.py
# We need the API calling logic but not the MCP adapter parts
```

#### 2.3 Create Sync Engine (New Component)
**File**: `src/sync/engine.py`
```python
"""
Extract and adapt:
- Conversation fetching logic from intercom_client.py
- Pagination handling  
- Rate limiting compliance
- Error handling and retry logic
- Add database storage logic
"""

class IntercomSyncEngine:
    def __init__(self, intercom_token: str, database_url: str):
        self.intercom_client = IntercomAPIClient(intercom_token)
        self.db = DatabaseClient(database_url)
    
    async def full_sync(self):
        """Initial sync of all conversations"""
        
    async def incremental_sync(self):
        """Sync only new/modified conversations"""
        
    async def webhook_sync(self, webhook_data):
        """Process real-time webhook updates"""
```

#### 2.4 Create Database Layer (New Component)
**File**: `src/database/client.py`
```python
"""
New component for database operations:
- PostgreSQL connection management
- Schema creation and migration
- Optimized conversation storage
- Query interface for MCP server
"""

class DatabaseClient:
    def __init__(self, database_url: str):
        self.url = database_url
        self.pool = None
    
    async def store_conversations(self, conversations: List[Conversation]):
        """Store conversations with upsert logic"""
        
    async def search_conversations(self, filters: dict) -> List[Conversation]:
        """Search conversations with filters"""
```

#### 2.5 Adapt MCP Server
```bash
# Take existing MCP server logic and make it standalone
cp src/mcp/intercom_mcp_server.py ~/Developer/FastIntercomMCP/src/mcp/server.py

# Modify to work with local database instead of API
# Add FastMCP framework integration
# Implement all tools from specification
```

### Step 3: New Repository Development

#### 3.1 Set Up Development Environment
```bash
cd ~/Developer/FastIntercomMCP

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "fast-intercom-mcp"
version = "0.1.0"
description = "High-performance MCP server for Intercom conversation analytics"
authors = ["Your Name <email@example.com>"]
license = "MIT"
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
fastmcp = "^0.9.0"
asyncpg = "^0.29.0"
httpx = "^0.25.0"
pydantic = "^2.5.0"
structlog = "^23.2.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
black = "^23.0.0"
ruff = "^0.1.0"
pre-commit = "^3.6.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

# Install dependencies
poetry install
```

#### 3.2 Implement Core Components
```bash
# 1. Database schema and migrations
touch src/database/schema.sql
touch src/database/migrations/

# 2. Sync engine implementation  
# - Implement IntercomSyncEngine class
# - Add rate limiting and error handling
# - Add database storage logic

# 3. MCP server implementation
# - Implement FastMCP-based server
# - Add all tools from specification
# - Add query optimization

# 4. Configuration management
# - Environment variable handling
# - Database connection configuration
# - Logging setup

# 5. CLI interface for management
touch src/cli.py  # sync commands, server start, etc.
```

#### 3.3 Docker Setup
```dockerfile
# Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false
RUN poetry install --no-dev

COPY . .
EXPOSE 8000

CMD ["python", "-m", "src.mcp.server"]
```

```yaml
# docker-compose.yml
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
    ports:
      - "5432:5432"
      
  fastintercom-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://fastintercom:${DB_PASSWORD}@fastintercom-db:5432/intercom
      INTERCOM_ACCESS_TOKEN: ${INTERCOM_ACCESS_TOKEN}
    depends_on:
      - fastintercom-db
    volumes:
      - ./logs:/app/logs

volumes:
  postgres_data:
```

#### 3.4 Initial Testing
```bash
# Set up test database
docker-compose up -d fastintercom-db

# Run basic tests
poetry run pytest tests/unit/ -v

# Test sync functionality
poetry run python -m src.cli sync --full

# Test MCP server
poetry run python -m src.mcp.server &
# Test MCP tools with simple client
```

### Step 4: Integration Back to ask-intercom

#### 4.1 Modify ask-intercom Universal Adapter
```bash
cd ~/Developer/ask-intercom-test

# Create integration branch
git checkout feature/mcp-integration
git checkout -b integrate-fastintercom-mcp
```

**File**: `src/mcp/universal_adapter.py`
```python
class FastIntercomMCPBackend(MCPBackend):
    """Backend using FastIntercomMCP standalone server."""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.client = None
    
    async def initialize(self) -> bool:
        """Test connection to FastIntercomMCP server."""
        try:
            # Test connection to FastIntercomMCP
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.server_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via FastIntercomMCP server."""
        # Implement MCP client call to FastIntercomMCP server
```

#### 4.2 Update Configuration
**File**: `.env` (add new variables)
```bash
# FastIntercomMCP integration
ENABLE_FAST_INTERCOM_MCP=true
FAST_INTERCOM_MCP_URL=http://localhost:8000
```

**File**: `src/config.py`
```python
class Config:
    # Existing config...
    
    # FastIntercomMCP settings
    enable_fast_intercom_mcp: bool = False
    fast_intercom_mcp_url: str = "http://localhost:8000"
```

#### 4.3 Update Universal Adapter Priority
```python
# In UniversalMCPAdapter initialization
backends_to_test = []

if self.config.enable_fast_intercom_mcp:
    backends_to_test.append(
        ("fast_intercom_mcp", FastIntercomMCPBackend(self.config.fast_intercom_mcp_url))
    )

if self.prefer_official:
    backends_to_test.append(
        ("official_mcp", OfficialMCPBackend(self.mcp_server_url, self.intercom_token))
    )

# Rest of existing backends...
```

### Step 5: Testing Integration

#### 5.1 Start FastIntercomMCP Server
```bash
cd ~/Developer/FastIntercomMCP

# Start with test data
docker-compose up -d
poetry run python -m src.cli sync --full  # Initial sync
poetry run python -m src.mcp.server      # Start MCP server
```

#### 5.2 Test ask-intercom Integration
```bash
cd ~/Developer/ask-intercom-test

# Enable FastIntercomMCP in config
echo "ENABLE_FAST_INTERCOM_MCP=true" >> .env

# Test CLI with FastIntercomMCP backend
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "show me issues from the last 24 hours"

# Verify it's using FastIntercomMCP (should see logs indicating fast backend)
tail -f .ask-intercom-analytics/logs/backend-$(date +%Y-%m-%d).jsonl
```

#### 5.3 Performance Validation
```bash
# Benchmark before and after
time env ENABLE_FAST_INTERCOM_MCP=false poetry run python -m src.cli "show issues from today"
time env ENABLE_FAST_INTERCOM_MCP=true poetry run python -m src.cli "show issues from today"

# Should see dramatic improvement (5-30 seconds → <1 second)
```

### Step 6: Documentation & Release

#### 6.1 Update ask-intercom Documentation
```bash
# Update docs/04-Current-Status.md
# Add FastIntercomMCP integration status
# Update performance metrics

# Update docs/05-Next-Steps.md
# Mark FastIntercomMCP as completed
# Update roadmap
```

#### 6.2 Create FastIntercomMCP Documentation
```bash
cd ~/Developer/FastIntercomMCP

# Create comprehensive README.md
cat > README.md << 'EOF'
# FastIntercomMCP

High-performance MCP server for Intercom conversation analytics

## Quick Start

```bash
docker-compose up -d
# Set INTERCOM_ACCESS_TOKEN in .env
python -m src.cli sync --full
python -m src.mcp.server
```

## Features

- 100x faster than Intercom REST API
- Advanced conversation analytics
- MCP protocol native
- Production ready

[Full documentation in docs/](./docs/)
EOF
```

#### 6.3 Commit and Release
```bash
# FastIntercomMCP repository
cd ~/Developer/FastIntercomMCP
git add .
git commit -m "feat: initial FastIntercomMCP implementation with MCP server and database optimization"
git push origin main

# Create initial release
git tag v0.1.0
git push origin v0.1.0

# ask-intercom repository  
cd ~/Developer/ask-intercom-test
git add .
git commit -m "feat: integrate FastIntercomMCP for 100x performance improvement"
git push origin integrate-fastintercom-mcp

# Create PR for integration
```

## 🔄 Fallback & Rollback Plan

### Immediate Rollback (if integration fails)
```bash
cd ~/Developer/ask-intercom-test

# Disable FastIntercomMCP
echo "ENABLE_FAST_INTERCOM_MCP=false" >> .env

# System immediately falls back to existing MCP/REST implementations
# Zero downtime rollback
```

### Complete Rollback (if major issues)
```bash
# Revert integration branch
git checkout feature/mcp-integration
git reset --hard HEAD~n  # Where n is number of commits to revert

# System returns to previous state
# FastIntercomMCP repository remains for future use
```

## 📊 Success Validation Checklist

### Technical Validation
- [ ] FastIntercomMCP server starts successfully
- [ ] Database sync completes without errors
- [ ] MCP tools respond correctly
- [ ] ask-intercom integration works
- [ ] Performance improvement verified (>10x faster)
- [ ] Fallback mechanisms work correctly

### Functional Validation
- [ ] All existing ask-intercom queries work with FastIntercomMCP
- [ ] Results are consistent between backends
- [ ] No data loss or corruption
- [ ] Error handling works properly
- [ ] Concurrent usage works

### Documentation Validation
- [ ] README.md is clear and complete
- [ ] Installation instructions work
- [ ] Examples run successfully
- [ ] API documentation is accurate

## 🎯 Risk Mitigation

### Low Risk Factors ✅
- **Reversible changes**: All changes can be reverted with configuration
- **Fallback preserved**: Original functionality remains intact
- **Incremental integration**: Can enable/disable FastIntercomMCP per query
- **Isolated development**: New project doesn't affect existing code

### Risk Mitigation Strategies
1. **Feature flags**: ENABLE_FAST_INTERCOM_MCP allows instant rollback
2. **Gradual rollout**: Test with subset of queries first
3. **Monitoring**: Comprehensive logging and error tracking
4. **Backup plan**: Original MCP/REST backends remain available

## 📈 Expected Outcomes

### Performance Improvements
- **Query response time**: 5-30 seconds → <1 second
- **Concurrent users**: 1-2 → 100+
- **Complex analytics**: Impossible → <200ms
- **API costs**: $0.10-0.50/query → $0 after sync

### Development Benefits
- **Standalone project**: Valuable open source contribution
- **Reusable component**: Other teams can use FastIntercomMCP
- **Architecture improvement**: Clean separation of concerns
- **Market validation**: Test demand for high-performance MCP servers

### Strategic Benefits
- **Thought leadership**: First high-performance Intercom MCP server
- **Community value**: Contribute to MCP ecosystem
- **Product differentiation**: Unique performance advantage
- **Future foundation**: Ready for multi-platform expansion

---

**This transition plan ensures a clean, low-risk extraction of FastIntercomMCP while maintaining full functionality and performance in ask-intercom.**