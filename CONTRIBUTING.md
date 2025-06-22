# Contributing to FastIntercom MCP

## Development Setup

### Prerequisites

- Python 3.11+
- Intercom access token with read permissions
- Git

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd FastIntercomMCP

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your Intercom access token
```

### Testing

```bash
# Run basic functionality tests
python -c "
import asyncio
from fastintercom import DatabaseManager, Config

def test_basic():
    print('Testing database...')
    db = DatabaseManager(':memory:')  # In-memory test
    print('✅ Database working')
    
    print('Testing config...')
    config = Config.load()
    print(f'✅ Config loaded: {config.intercom_token[:10] if config.intercom_token else \"No token\"}...')

test_basic()
"

# Test with real API
python -c "
import asyncio
from fastintercom import IntercomClient, Config

async def test_api():
    config = Config.load()
    if not config.intercom_token:
        print('❌ No Intercom token found')
        return
    
    client = IntercomClient(config.intercom_token)
    connected = await client.test_connection()
    print(f'API Connection: {\"✅ Connected\" if connected else \"❌ Failed\"}')

asyncio.run(test_api())
"
```

### Code Quality

- Follow PEP 8 style guidelines
- Add type hints to new functions
- Include docstrings for public methods
- Test changes with real Intercom data when possible

### Project Structure

```
fastintercom/
├── __init__.py          # Package exports
├── cli.py              # Command-line interface
├── config.py           # Configuration management
├── database.py         # SQLite database operations
├── intercom_client.py  # Intercom API client
├── mcp_server.py       # MCP server implementation
├── models.py           # Data models
└── sync_service.py     # Background sync service
```

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Add functionality to appropriate modules
   - Update type hints and docstrings
   - Test locally with `fastintercom` commands

3. **Test your changes**:
   ```bash
   # Test CLI functionality
   fastintercom status
   fastintercom sync --force --days 1
   
   # Test package imports
   python -c "from fastintercom import *; print('All imports working')"
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**

### Common Development Tasks

#### Adding a new MCP tool

1. Add the tool definition in `mcp_server.py` `list_tools()` function
2. Add the tool handler in `mcp_server.py` `call_tool()` function
3. Add any required database methods in `database.py`
4. Test with Claude Desktop integration

#### Modifying the database schema

1. Update the schema in `database.py` `_init_database()` method
2. Add migration logic if needed for existing installations
3. Update related model classes in `models.py`
4. Test with `fastintercom reset` and fresh initialization

#### Adding CLI commands

1. Add the command in `cli.py` using Click decorators
2. Follow the existing pattern for error handling and output
3. Test the command with various arguments

### Debugging

#### Enable verbose logging
```bash
fastintercom --verbose status
export FASTINTERCOM_LOG_LEVEL=DEBUG
```

#### Check log files
```bash
tail -f ~/.fastintercom/logs/fastintercom.log
```

#### Database inspection
```bash
sqlite3 ~/.fastintercom/data.db
.tables
.schema conversations
SELECT COUNT(*) FROM conversations;
```

### Performance Considerations

- Database queries should use indexes where possible
- Background sync operations should not block MCP requests
- Memory usage should remain under 100MB for typical workloads
- Response times should stay under 100ms for cached data

### Security Guidelines

- Never commit API tokens or sensitive data
- Use environment variables for configuration
- Validate all user inputs in CLI commands
- Log errors without exposing sensitive information

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Include steps to reproduce for bug reports