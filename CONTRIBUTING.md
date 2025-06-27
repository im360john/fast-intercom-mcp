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
cd fast-intercom-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your Intercom access token
```

### Testing Requirements

All contributions must include appropriate testing. Follow these testing requirements:

#### Required Tests for Pull Requests

**Unit Tests** (Required for all changes):
```bash
# Run unit tests
pytest tests/

# Ensure adequate coverage
pytest tests/ --cov=fast_intercom_mcp --cov-report=term-missing

# All tests must pass with no warnings
```

**Integration Tests** (Required for major changes):
```bash
# Quick integration test
export INTERCOM_ACCESS_TOKEN=your_token_here
./scripts/run_integration_test.sh --quick

# Full integration test for significant changes
./scripts/run_integration_test.sh --performance-report
```

**Code Quality Checks** (Required for all PRs):
```bash
# Linting (must pass)
ruff check . --exclude venv

# Type checking (must pass)
mypy fast_intercom_mcp/

# Import verification (must pass)
python3 -c "import fast_intercom_mcp; print('✅ Import successful')"
```

#### Testing Guidelines by Change Type

**Database Changes**:
- Unit tests for new database operations
- Database integrity verification
- Migration testing (if schema changes)
- Performance impact assessment

**API Integration Changes**:
- Mock tests for API client methods
- Integration tests with real API data
- Rate limiting and error handling tests
- Performance regression testing

**MCP Protocol Changes**:
- MCP tool functionality tests
- Protocol compliance verification
- Client compatibility testing
- Response format validation

**Performance Changes**:
- Benchmark tests before and after
- Memory usage monitoring
- Performance regression testing
- Load testing for significant changes

#### Test Environment Setup

**Local Testing Environment**:
```bash
# Set up test environment
export INTERCOM_ACCESS_TOKEN=your_test_token
export FASTINTERCOM_TEST_LOG_LEVEL=DEBUG
export FASTINTERCOM_CONFIG_DIR=~/.fast-intercom-mcp-test

# Verify environment
./scripts/verify_test_environment.sh
```

**Docker Testing** (for deployment changes):
```bash
# Test Docker build and functionality
./scripts/test_docker_install.sh

# Test with API integration
./scripts/test_docker_install.sh --with-api-test
```

#### Test Data Requirements

**Mock Data**: Use consistent mock data for unit tests
- Location: `tests/fixtures/`
- Format: JSON files with realistic structure
- Coverage: All major data scenarios

**Integration Data**: Use controlled real data for integration tests
- Scope: Last 7 days (default) or configurable
- Limits: Reasonable conversation counts (<1000 for quick tests)
- Cleanup: Automatic cleanup of test data

#### Performance Testing Requirements

**Performance Targets** (must be met):
- Sync Speed: >10 conversations/second
- Query Response: <100ms for cached data
- Memory Usage: <100MB during normal operations
- Storage Efficiency: ~2KB per conversation

**Performance Testing**:
```bash
# Run performance benchmarks
./scripts/run_performance_test.sh

# Monitor performance during development
./scripts/monitor_performance.sh &
# ... run tests ...
pkill -f monitor_performance
```

#### Testing Before Submission

**Pre-commit Checklist**:
```bash
# 1. Unit tests pass
pytest tests/ -x --tb=short

# 2. Code quality checks pass
ruff check . --exclude venv
python3 -c "import fast_intercom_mcp"

# 3. Quick integration test (if API token available)
./scripts/run_integration_test.sh --quick

# 4. Documentation updated (if needed)
# 5. Performance impact assessed (if applicable)
```

**CI/CD Requirements**:
- All GitHub Actions workflows must pass
- Fast Check workflow (automatic on PR)
- Integration tests (manual trigger recommended)
- No regression in performance metrics

#### Test Documentation

**Test Documentation Requirements**:
- Document new test scenarios in commit messages
- Update test documentation for new features
- Include testing instructions in PR descriptions
- Reference related issues and test coverage

**Test Maintenance**:
- Update test data when API responses change
- Maintain performance baselines
- Clean up obsolete tests
- Document test environment requirements

### Code Quality

- Follow PEP 8 style guidelines
- Add type hints to new functions
- Include docstrings for public methods
- Test changes with real Intercom data when possible

### Project Structure

```
fast_intercom_mcp/
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
   - Test locally with `fast-intercom-mcp` commands

3. **Test your changes**:
   ```bash
   # Test CLI functionality
   fast-intercom-mcp status
   fast-intercom-mcp sync --force --days 1
   
   # Test package imports
   python -c "from fast_intercom_mcp import *; print('All imports working')"
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
4. Test with `fast-intercom-mcp reset` and fresh initialization

#### Adding CLI commands

1. Add the command in `cli.py` using Click decorators
2. Follow the existing pattern for error handling and output
3. Test the command with various arguments

### Debugging

#### Enable verbose logging
```bash
fast-intercom-mcp --verbose status
export FASTINTERCOM_LOG_LEVEL=DEBUG
```

#### Check log files
```bash
tail -f ~/.fast_intercom_mcp/logs/fast-intercom-mcp.log
```

#### Database inspection
```bash
sqlite3 ~/.fast_intercom_mcp/data.db
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