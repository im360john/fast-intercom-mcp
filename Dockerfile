FROM python:3.11-slim

LABEL maintainer="FastIntercom Team"
LABEL description="FastIntercom MCP Server for Intercom data synchronization"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FASTINTERCOM_DATA_DIR=/data
ENV FASTINTERCOM_CONFIG_DIR=/config

# Create app user
RUN groupadd -r fastintercom && useradd -r -g fastintercom fastintercom

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install dependencies first
RUN pip install --no-cache-dir --upgrade pip && \
    pip install mcp httpx click python-dotenv fastapi uvicorn[standard] pydantic

# Copy application code
COPY fast_intercom_mcp/ ./fast_intercom_mcp/

# Set Python path to find the module
ENV PYTHONPATH=/app

# Create data and config directories
RUN mkdir -p /data /config /var/log/fastintercom && \
    chown -R fastintercom:fastintercom /data /config /var/log/fastintercom /app

# Create startup script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -m fast_intercom_mcp.cli status || exit 1

# Switch to non-root user
USER fastintercom

# Expose MCP server port for HTTP mode
EXPOSE 8000

# Default command
ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]