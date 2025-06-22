# Multi-stage Dockerfile for FastIntercomMCP
# Optimized for both development and production builds

# =============================================================================
# Base Stage - Common dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r fastintercom && \
    useradd -r -g fastintercom -d /app -s /bin/bash fastintercom && \
    mkdir -p /app /app/logs && \
    chown -R fastintercom:fastintercom /app

# Set working directory
WORKDIR /app

# =============================================================================
# Dependencies Stage - Install Python dependencies
# =============================================================================
FROM base as dependencies

# Install Poetry
RUN pip install poetry==1.7.1

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-dev && rm -rf $POETRY_CACHE_DIR

# =============================================================================
# Development Stage - For local development
# =============================================================================
FROM dependencies as development

# Install development dependencies
RUN poetry install && rm -rf $POETRY_CACHE_DIR

# Copy source code
COPY --chown=fastintercom:fastintercom . .

# Switch to non-root user
USER fastintercom

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command for development (with auto-reload)
CMD ["poetry", "run", "python", "-m", "src.mcp.server", "--reload"]

# =============================================================================
# Production Stage - Optimized for production
# =============================================================================
FROM base as production

# Copy virtual environment from dependencies stage
COPY --from=dependencies /app/.venv /app/.venv

# Ensure virtual environment is in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY --chown=fastintercom:fastintercom . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R fastintercom:fastintercom /app/logs /app/data

# Switch to non-root user
USER fastintercom

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Production command
CMD ["python", "-m", "src.mcp.server"]

# =============================================================================
# Testing Stage - For running tests in CI/CD
# =============================================================================
FROM dependencies as testing

# Install test dependencies
RUN poetry install --with=test && rm -rf $POETRY_CACHE_DIR

# Copy source code
COPY --chown=fastintercom:fastintercom . .

# Switch to non-root user
USER fastintercom

# Command for running tests
CMD ["poetry", "run", "pytest", "-v", "--cov=src", "--cov-report=xml"]

# =============================================================================
# Build Arguments and Labels
# =============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="FastIntercomMCP" \
      org.label-schema.description="High-performance MCP server for Intercom conversation analytics" \
      org.label-schema.url="https://github.com/evolsb/FastIntercomMCP" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/evolsb/FastIntercomMCP" \
      org.label-schema.vendor="evolsb" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"

# =============================================================================
# Usage Examples:
# 
# Development:
# docker build --target development -t fastintercom-mcp:dev .
# docker run -p 8000:8000 -v .:/app fastintercom-mcp:dev
#
# Production:
# docker build --target production -t fastintercom-mcp:latest .
# docker run -p 8000:8000 -e INTERCOM_ACCESS_TOKEN=xxx fastintercom-mcp:latest
#
# Testing:
# docker build --target testing -t fastintercom-mcp:test .
# docker run fastintercom-mcp:test
# =============================================================================