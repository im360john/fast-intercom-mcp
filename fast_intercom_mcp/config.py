"""Configuration management for FastIntercom MCP server."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """FastIntercom configuration."""

    intercom_token: str
    database_path: str | None = None
    log_level: str = "INFO"
    max_sync_age_minutes: int = 5
    background_sync_interval_minutes: int = 10
    initial_sync_days: int = 30  # 0 means ALL history
    connection_pool_size: int = 5  # Database connection pool size
    api_timeout_seconds: int = 300
    sync_mode: str = "activity"  # "activity" or "new_only"
    
    # Streamable HTTP settings
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    http_path: str = "/mcp"
    
    # PostgreSQL settings (if database_url is provided, it overrides database_path)
    database_url: str | None = None
    
    # Context window management
    max_response_tokens: int = 40000
    max_items_per_search: int = 20
    max_article_preview_length: int = 500
    max_conversation_messages: int = 10
    
    # Rate limiting
    rate_limit_calls: int = 900  # Conservative under 1000/min limit
    rate_limit_window: int = 60  # seconds
    
    # Intercom API settings
    intercom_api_version: str = "2.13"
    intercom_api_base_url: str = "https://api.intercom.io"

    @classmethod
    def load(cls, config_path: str | None = None) -> "Config":
        """Load configuration from file or environment variables."""
        # Load .env file if it exists
        load_dotenv()

        if config_path is None:
            config_path = cls.get_default_config_path()

        config_data = {}

        # Load from file if it exists
        if Path(config_path).exists():
            with open(config_path) as f:
                config_data = json.load(f)

        # Override with environment variables
        env_overrides = {
            "intercom_token": os.getenv("INTERCOM_ACCESS_TOKEN"),
            "database_path": os.getenv("FASTINTERCOM_DB_PATH"),
            "database_url": os.getenv("DATABASE_URL"),
            "log_level": os.getenv("FASTINTERCOM_LOG_LEVEL"),
            "max_sync_age_minutes": os.getenv("FASTINTERCOM_MAX_SYNC_AGE_MINUTES"),
            "background_sync_interval_minutes": os.getenv("FASTINTERCOM_BACKGROUND_SYNC_INTERVAL"),
            "initial_sync_days": os.getenv("FASTINTERCOM_INITIAL_SYNC_DAYS"),
            "connection_pool_size": os.getenv("FASTINTERCOM_DB_POOL_SIZE"),
            "api_timeout_seconds": os.getenv("FASTINTERCOM_API_TIMEOUT_SECONDS"),
            "sync_mode": os.getenv("FASTINTERCOM_SYNC_MODE"),
            "http_host": os.getenv("HTTP_HOST"),
            "http_port": os.getenv("HTTP_PORT"),
            "http_path": os.getenv("HTTP_PATH"),
            "max_response_tokens": os.getenv("MAX_RESPONSE_TOKENS"),
            "max_items_per_search": os.getenv("MAX_ITEMS_PER_SEARCH"),
            "max_article_preview_length": os.getenv("MAX_ARTICLE_PREVIEW_LENGTH"),
            "max_conversation_messages": os.getenv("MAX_CONVERSATION_MESSAGES"),
            "rate_limit_calls": os.getenv("RATE_LIMIT_CALLS"),
            "rate_limit_window": os.getenv("RATE_LIMIT_WINDOW"),
        }

        for key, value in env_overrides.items():
            if value is not None:
                if key in [
                    "max_sync_age_minutes",
                    "background_sync_interval_minutes",
                    "initial_sync_days",
                    "connection_pool_size",
                    "api_timeout_seconds",
                    "http_port",
                    "max_response_tokens",
                    "max_items_per_search",
                    "max_article_preview_length",
                    "max_conversation_messages",
                    "rate_limit_calls",
                    "rate_limit_window",
                ]:
                    config_data[key] = int(value)
                else:
                    config_data[key] = value

        # Validate required fields
        if not config_data.get("intercom_token"):
            raise ValueError(
                "Intercom access token is required. Set INTERCOM_ACCESS_TOKEN environment variable "
                "or include 'intercom_token' in config file."
            )

        # Validate pool size if provided
        if "connection_pool_size" in config_data:
            pool_size = config_data["connection_pool_size"]
            if pool_size < 1 or pool_size > 20:
                raise ValueError(f"Database pool size must be between 1 and 20, got {pool_size}")

        # Validate sync mode
        if "sync_mode" in config_data:
            sync_mode = config_data["sync_mode"]
            if sync_mode not in ["activity", "new_only"]:
                raise ValueError(
                    f"Invalid sync_mode '{sync_mode}'. Must be 'activity' or 'new_only'"
                )

        return cls(**config_data)

    def save(self, config_path: str | None = None):
        """Save configuration to file."""
        if config_path is None:
            config_path = self.get_default_config_path()

        # Ensure config directory exists
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)

        # Don't save the token to file for security
        config_data = asdict(self)
        config_data.pop("intercom_token", None)

        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)

    @staticmethod
    def get_default_config_path() -> str:
        """Get the default configuration file path."""
        config_dir = os.getenv("FASTINTERCOM_CONFIG_DIR")
        if config_dir:
            return str(Path(config_dir) / "config.json")
        return str(Path.home() / ".fastintercom" / "config.json")

    @staticmethod
    def get_default_data_dir() -> str:
        """Get the default data directory."""
        config_dir = os.getenv("FASTINTERCOM_CONFIG_DIR")
        if config_dir:
            return str(Path(config_dir))
        return str(Path.home() / ".fastintercom")

    @staticmethod
    def get_test_workspace_dir() -> str:
        """Get the test workspace directory."""
        # Check for environment variable first
        test_workspace = os.getenv("FASTINTERCOM_TEST_WORKSPACE")
        if test_workspace:
            return str(Path(test_workspace))

        # Try to find project root by looking for pyproject.toml
        current_path = Path.cwd()
        for path in [current_path] + list(current_path.parents):
            if (path / "pyproject.toml").exists():
                return str(path / ".test-workspace")

        # Fall back to current directory
        return str(current_path / ".test-workspace")


# Import setup_logging from the new core module
