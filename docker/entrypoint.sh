#!/bin/bash
set -e

# Set default paths for Docker environment
export FASTINTERCOM_DB_PATH="${FASTINTERCOM_DB_PATH:-/data/fastintercom.db}"
export FASTINTERCOM_CONFIG_PATH="${FASTINTERCOM_CONFIG_PATH:-/config/config.json}"
export FASTINTERCOM_DATA_DIR="${FASTINTERCOM_DATA_DIR:-/data}"

# Override default directories to use mounted volumes
export HOME=/data
mkdir -p /data/logs /config

# Create config from environment if not exists
if [ ! -f "$FASTINTERCOM_CONFIG_PATH" ]; then
    echo "Creating config from environment variables..."
    cat > "$FASTINTERCOM_CONFIG_PATH" << EOF
{
  "database_path": "$FASTINTERCOM_DB_PATH",
  "log_level": "${FASTINTERCOM_LOG_LEVEL:-INFO}",
  "max_sync_age_minutes": ${FASTINTERCOM_MAX_SYNC_AGE_MINUTES:-5},
  "background_sync_interval_minutes": ${FASTINTERCOM_BACKGROUND_SYNC_INTERVAL:-10},
  "initial_sync_days": ${FASTINTERCOM_INITIAL_SYNC_DAYS:-30}
}
EOF
fi

# Initialize if not already done (skip init for status/other commands)
if [ ! -f "$FASTINTERCOM_DB_PATH" ] && [ -n "$INTERCOM_ACCESS_TOKEN" ] && [ "$1" = "start" ]; then
    echo "Initializing FastIntercom..."
    # Create a temporary script for initialization since we can't pipe to CLI easily
    cat > /tmp/init.py << EOF
import os
from fast_intercom_mcp.config import Config
from fast_intercom_mcp.database import DatabaseManager

config = Config(
    intercom_token="$INTERCOM_ACCESS_TOKEN",
    database_path="$FASTINTERCOM_DB_PATH",
    initial_sync_days=${FASTINTERCOM_INITIAL_SYNC_DAYS:-30}
)
config.save("$FASTINTERCOM_CONFIG_PATH")

# Initialize database
db = DatabaseManager("$FASTINTERCOM_DB_PATH")
print("FastIntercom initialized successfully")
EOF
    python /tmp/init.py
fi

# Execute the command
# Default to "mcp" command if no args provided (for stdio MCP)
if [ $# -eq 0 ]; then
    exec python -m fast_intercom_mcp.cli mcp
else
    exec python -m fast_intercom_mcp.cli "$@"
fi