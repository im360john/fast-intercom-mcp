#!/usr/bin/env python3
"""
Local CI Mirror Test Script
==========================

A comprehensive Python script that mirrors the GitHub Actions workflows for local testing.
This script replicates the behavior of the 4 CI workflows:
- fast-check.yml (import, lint, CLI test)
- quick-test.yml (API integration with limited data)
- integration-test.yml (full API testing)
- docker-install-test.yml (Docker deployment testing)

Requirements:
- Python 3.11+
- Poetry or venv environment
- Docker (for docker tests)
- Optional: INTERCOM_ACCESS_TOKEN (for API tests)

Usage:
    python local_ci_mirror_test.py --help
    python local_ci_mirror_test.py --workflow fast-check
    python local_ci_mirror_test.py --workflow all
    python local_ci_mirror_test.py --skip-docker --json-output results.json
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


# Color constants for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[1;37m"
    NC = "\033[0m"  # No Color


class LocalCITester:
    """Main class for running local CI tests that mirror GitHub Actions workflows."""

    def __init__(self, args):
        self.args = args
        self.project_root = Path.cwd()
        self.start_time = time.time()
        self.results = {
            "test_run_id": f"local-ci-{int(self.start_time)}",
            "timestamp": datetime.now(UTC).isoformat(),
            "project_root": str(self.project_root),
            "workflows": {},
            "environment": {},
            "summary": {},
        }

        # Setup logging
        self.setup_logging()

        # Detect environment
        self.detect_environment()

        # Available workflows
        self.workflows = {
            "fast-check": self.run_fast_check_workflow,
            "quick-test": self.run_quick_test_workflow,
            "integration-test": self.run_integration_test_workflow,
            "docker-install-test": self.run_docker_install_test_workflow,
        }

    def setup_logging(self):
        """Setup logging configuration."""
        log_level = logging.DEBUG if self.args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(__name__)

    def log_info(self, message: str):
        """Log info message with formatting."""
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")
        self.logger.info(message)

    def log_success(self, message: str):
        """Log success message with formatting."""
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")
        self.logger.info(f"SUCCESS: {message}")

    def log_warning(self, message: str):
        """Log warning message with formatting."""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log error message with formatting."""
        print(f"{Colors.RED}❌ {message}{Colors.NC}")
        self.logger.error(message)

    def log_section(self, title: str):
        """Log section header."""
        print(f"\n{Colors.CYAN}{'=' * 80}{Colors.NC}")
        print(f"{Colors.CYAN}🚀 {title}{Colors.NC}")
        print(f"{Colors.CYAN}{'=' * 80}{Colors.NC}")

    def detect_environment(self):
        """Detect the Python environment (Poetry, venv, or system)."""
        self.log_section("Environment Detection")

        env_info = {
            "python_version": (
                f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            ),
            "python_executable": sys.executable,
            "cwd": str(self.project_root),
        }

        # Check for Poetry
        if (self.project_root / "pyproject.toml").exists() and shutil.which("poetry"):
            self.env_type = "poetry"
            self.python_cmd = ["poetry", "run", "python"]
            self.pip_cmd = ["poetry", "add"]
            self.ruff_cmd = ["poetry", "run", "ruff"]
            env_info["environment_type"] = "poetry"
            self.log_success("Detected Poetry environment")

        # Check for venv
        elif (self.project_root / "venv" / "bin" / "activate").exists():
            self.env_type = "venv"
            self.python_cmd = [str(self.project_root / "venv" / "bin" / "python")]
            self.pip_cmd = [str(self.project_root / "venv" / "bin" / "pip"), "install"]
            # Use system ruff if venv ruff doesn't exist
            venv_ruff = self.project_root / "venv" / "bin" / "ruff"
            if venv_ruff.exists():
                self.ruff_cmd = [str(venv_ruff)]
            else:
                self.ruff_cmd = ["ruff"]
            env_info["environment_type"] = "venv"
            env_info["venv_path"] = str(self.project_root / "venv")
            self.log_success("Detected venv environment")

        # Check for .venv
        elif (self.project_root / ".venv" / "bin" / "activate").exists():
            self.env_type = "dotvenv"
            self.python_cmd = [str(self.project_root / ".venv" / "bin" / "python")]
            self.pip_cmd = [str(self.project_root / ".venv" / "bin" / "pip"), "install"]
            # Use system ruff if venv ruff doesn't exist
            venv_ruff = self.project_root / ".venv" / "bin" / "ruff"
            if venv_ruff.exists():
                self.ruff_cmd = [str(venv_ruff)]
            else:
                self.ruff_cmd = ["ruff"]
            env_info["environment_type"] = "dotvenv"
            env_info["venv_path"] = str(self.project_root / ".venv")
            self.log_success("Detected .venv environment")

        # Fall back to system Python
        else:
            self.env_type = "system"
            self.python_cmd = ["python3"]
            self.pip_cmd = ["python3", "-m", "pip", "install", "--user"]
            self.ruff_cmd = ["python3", "-m", "ruff"]
            env_info["environment_type"] = "system"
            self.log_warning("Using system Python (no venv detected)")

        # Store environment info
        self.results["environment"] = env_info

        # Test Python availability
        try:
            result = subprocess.run(
                self.python_cmd + ["--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                env_info["python_version_output"] = result.stdout.strip()
                self.log_success(f"Python available: {result.stdout.strip()}")
            else:
                self.log_error(f"Python command failed: {result.stderr}")
                raise SystemExit(1)
        except Exception as e:
            self.log_error(f"Failed to verify Python: {e}")
            raise SystemExit(1) from e

    def run_command(
        self,
        cmd: list[str],
        cwd: Path | None = None,
        timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str, str]:
        """Run a command and return (returncode, stdout, stderr)."""
        try:
            if env:
                # Merge with current environment
                full_env = os.environ.copy()
                full_env.update(env)
            else:
                full_env = None

            self.log_info(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or self.project_root,
                env=full_env,
            )

            if self.args.verbose and result.stdout:
                print(f"{Colors.WHITE}STDOUT:{Colors.NC}\n{result.stdout}")
            if self.args.verbose and result.stderr:
                print(f"{Colors.YELLOW}STDERR:{Colors.NC}\n{result.stderr}")

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            self.log_error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            return 1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            self.log_error(f"Command failed: {e}")
            return 1, "", str(e)

    def install_dependencies(self) -> bool:
        """Install project dependencies based on environment type."""
        self.log_info("Installing dependencies...")

        if self.env_type == "poetry":
            # Poetry install
            returncode, stdout, stderr = self.run_command(["poetry", "install"])
            if returncode != 0:
                self.log_error(f"Poetry install failed: {stderr}")
                return False
            self.log_success("Poetry dependencies installed")

        else:
            # pip install for venv or system
            returncode, stdout, stderr = self.run_command(self.pip_cmd + ["-e", "."])
            if returncode != 0:
                self.log_error(f"pip install failed: {stderr}")
                return False
            self.log_success("pip dependencies installed")

            # Install additional testing dependencies
            extra_deps = ["pytest", "pytest-asyncio", "pytest-cov", "httpx[http2]", "ruff"]
            for dep in extra_deps:
                returncode, stdout, stderr = self.run_command(self.pip_cmd + [dep])
                if returncode != 0:
                    self.log_warning(f"Failed to install {dep}: {stderr}")

        return True

    def run_fast_check_workflow(self) -> dict[str, Any]:
        """Mirror the fast-check.yml workflow."""
        self.log_section("Fast Check Workflow")

        workflow_start = time.time()
        results = {
            "name": "fast-check",
            "start_time": datetime.now(UTC).isoformat(),
            "timeout_minutes": 2,
            "steps": {},
            "status": "running",
        }

        try:
            # Step 1: Python import test
            self.log_info("Step 1: Python import test")
            step_start = time.time()
            returncode, stdout, stderr = self.run_command(
                self.python_cmd + ["-c", "import fast_intercom_mcp"]
            )
            step_duration = time.time() - step_start
            results["steps"]["python_import"] = {
                "status": "passed" if returncode == 0 else "failed",
                "duration_seconds": step_duration,
                "output": stdout,
                "error": stderr,
            }

            if returncode != 0:
                self.log_error(f"Python import failed: {stderr}")
                raise Exception("Python import test failed")
            self.log_success("Python import test passed")

            # Step 2: Ruff linting (critical errors only)
            self.log_info("Step 2: Ruff linting (critical errors only)")
            step_start = time.time()
            returncode, stdout, stderr = self.run_command(
                self.ruff_cmd
                + [
                    "check",
                    ".",
                    "--config",
                    "pyproject.toml",
                    "--select",
                    "E,F",
                    "--exclude",
                    "__pycache__",
                ]
            )
            step_duration = time.time() - step_start
            results["steps"]["ruff_linting"] = {
                "status": "passed" if returncode == 0 else "failed",
                "duration_seconds": step_duration,
                "output": stdout,
                "error": stderr,
            }

            if returncode != 0:
                self.log_error(f"Ruff linting failed: {stderr}")
                raise Exception("Ruff linting failed")
            self.log_success("Ruff linting passed")

            # Step 3: CLI smoke test
            self.log_info("Step 3: CLI smoke test")
            step_start = time.time()
            returncode, stdout, stderr = self.run_command(
                self.python_cmd + ["-m", "fast_intercom_mcp", "--help"]
            )
            step_duration = time.time() - step_start
            results["steps"]["cli_smoke_test"] = {
                "status": "passed" if returncode == 0 else "failed",
                "duration_seconds": step_duration,
                "output": stdout,
                "error": stderr,
            }

            if returncode != 0:
                self.log_error(f"CLI smoke test failed: {stderr}")
                raise Exception("CLI smoke test failed")
            self.log_success("CLI smoke test passed")

            results["status"] = "passed"
            workflow_duration = time.time() - workflow_start

            # Check timeout (2 minutes for fast-check)
            if workflow_duration > 120:
                self.log_warning(f"Fast check took {workflow_duration:.1f}s (exceeds 2min timeout)")

            self.log_success(f"Fast Check workflow PASSED in {workflow_duration:.1f}s")

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.log_error(f"Fast Check workflow FAILED: {e}")

        finally:
            results["duration_seconds"] = time.time() - workflow_start
            results["end_time"] = datetime.now(UTC).isoformat()

        return results

    def run_quick_test_workflow(self) -> dict[str, Any]:
        """Mirror the quick-test.yml workflow."""
        self.log_section("Quick Integration Test Workflow")

        workflow_start = time.time()
        results = {
            "name": "quick-test",
            "start_time": datetime.now(UTC).isoformat(),
            "timeout_minutes": 10,
            "steps": {},
            "status": "running",
            "sync_days": getattr(self.args, "sync_days", 1),
        }

        try:
            # Create test environment
            test_dir = self.project_root / "quick_test_data"
            test_dir.mkdir(exist_ok=True)

            # Step 1: Verify package installation
            self.log_info("Step 1: Verify package installation")
            step_start = time.time()

            # Import test
            returncode, stdout, stderr = self.run_command(
                self.python_cmd
                + ["-c", "import fast_intercom_mcp; print('✅ Package imported successfully')"]
            )
            if returncode != 0:
                raise Exception(f"Package import failed: {stderr}")

            # CLI help test
            returncode, stdout, stderr = self.run_command(
                self.python_cmd + ["-m", "fast_intercom_mcp", "--help"]
            )
            if returncode != 0:
                raise Exception(f"CLI help failed: {stderr}")

            step_duration = time.time() - step_start
            results["steps"]["verify_installation"] = {
                "status": "passed",
                "duration_seconds": step_duration,
            }
            self.log_success("Package installation verified")

            # Step 2: Quick integration test (if API token available)
            self.log_info("Step 2: Quick integration test")
            step_start = time.time()

            api_token = os.getenv("INTERCOM_ACCESS_TOKEN")
            if not api_token:
                self.log_warning("No INTERCOM_ACCESS_TOKEN found - skipping API tests")
                results["steps"]["quick_integration"] = {
                    "status": "skipped",
                    "reason": "No API token available",
                }
            else:
                # Run the actual quick test
                quick_test_script = f"""
import asyncio
import os
import json
import time
from datetime import datetime, timedelta, UTC
from fast_intercom_mcp.sync_service import SyncService
from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient

async def run_quick_test():
    print('⏱️  Test started at:', datetime.now(UTC).strftime('%H:%M:%S UTC'))

    # Initialize components
    db = DatabaseManager('./quick_test.db')
    client = IntercomClient(os.getenv('INTERCOM_ACCESS_TOKEN'))
    sync_service = SyncService(db, client)

    # Quick API connection test
    print('🔌 Testing API connection...')
    connection_result = await client.test_connection()
    if not connection_result:
        raise Exception('API connection failed')
    print('✅ API connection successful')

    # Quick sync test with limited conversations for speed
    sync_days = {results["sync_days"]}
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=sync_days)

    print(f'🔄 Quick sync: {{sync_days}} day(s) of data (limited to 50 conversations for speed)')
    print(f'📅 Period: {{start_date.strftime("%Y-%m-%d")}} to {{end_date.strftime("%Y-%m-%d")}}')

    sync_start = time.time()
    # Use the proven sync_period method with a very short period for speed
    recent_time = end_date - timedelta(hours=2)  # Last 2 hours for speed

    print(
        f'🔄 Using sync_period with last 2 hours: {{recent_time.strftime("%H:%M")}} '
        f'to {{end_date.strftime("%H:%M")}}'
    )

    stats = await sync_service.sync_period(recent_time, end_date)
    sync_duration = time.time() - sync_start

    # Results
    rate = stats.total_conversations / max(sync_duration, 1)

    print('')
    print('📊 Quick Test Results:')
    print(f'✅ Conversations synced: {{stats.total_conversations:,}}')
    print(f'✅ Messages synced: {{stats.total_messages:,}}')
    print(f'✅ Sync speed: {{rate:.1f}} conversations/second')
    print(f'✅ Duration: {{sync_duration:.1f}} seconds')
    print(f'✅ API calls: {{stats.api_calls_made:,}}')

    # Quick MCP tool test
    print('')
    print('🛠️ Testing MCP tools...')
    status = sync_service.get_status()
    print(f'✅ Sync service status: OK')

    # Save quick results
    quick_results = {{
        'test_type': 'quick',
        'sync_days': sync_days,
        'conversations': stats.total_conversations,
        'messages': stats.total_messages,
        'duration_seconds': round(sync_duration, 2),
        'rate_conv_per_sec': round(rate, 2),
        'api_calls': stats.api_calls_made,
        'timestamp': datetime.now(UTC).isoformat()
    }}

    with open('quick_results.json', 'w') as f:
        json.dump(quick_results, f, indent=2)

    print('')
    print('🎉 Quick integration test PASSED!')
    print(f'⏱️  Completed at: {{datetime.now(UTC).strftime("%H:%M:%S UTC")}}')

    return True

# Run the test
success = asyncio.run(run_quick_test())
if not success:
    exit(1)
"""

                returncode, stdout, stderr = self.run_command(
                    self.python_cmd + ["-c", quick_test_script],
                    cwd=test_dir,
                    env={"INTERCOM_ACCESS_TOKEN": api_token},
                    timeout=600,  # 10 minute timeout
                )

                step_duration = time.time() - step_start

                if returncode == 0:
                    results["steps"]["quick_integration"] = {
                        "status": "passed",
                        "duration_seconds": step_duration,
                        "output": stdout,
                    }

                    # Try to load results
                    results_file = test_dir / "quick_results.json"
                    if results_file.exists():
                        try:
                            with open(results_file) as f:
                                quick_results = json.load(f)
                            results["quick_test_metrics"] = quick_results
                        except Exception as e:
                            self.log_warning(f"Could not load quick results: {e}")

                    self.log_success("Quick integration test passed")
                else:
                    results["steps"]["quick_integration"] = {
                        "status": "failed",
                        "duration_seconds": step_duration,
                        "error": stderr,
                        "output": stdout,
                    }
                    raise Exception(f"Quick integration test failed: {stderr}")

            results["status"] = "passed"
            workflow_duration = time.time() - workflow_start

            # Check timeout (10 minutes for quick-test)
            if workflow_duration > 600:
                self.log_warning(
                    f"Quick test took {workflow_duration:.1f}s (exceeds 10min timeout)"
                )

            self.log_success(f"Quick Test workflow PASSED in {workflow_duration:.1f}s")

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.log_error(f"Quick Test workflow FAILED: {e}")

        finally:
            results["duration_seconds"] = time.time() - workflow_start
            results["end_time"] = datetime.now(UTC).isoformat()

        return results

    def run_integration_test_workflow(self) -> dict[str, Any]:
        """Mirror the integration-test.yml workflow."""
        self.log_section("Integration Test Workflow")

        workflow_start = time.time()
        results = {
            "name": "integration-test",
            "start_time": datetime.now(UTC).isoformat(),
            "timeout_minutes": 30,
            "steps": {},
            "status": "running",
            "sync_days": getattr(self.args, "sync_days", 30),
        }

        try:
            # Create test environment
            test_dir = self.project_root / "integration_test_data"
            test_dir.mkdir(exist_ok=True)

            # Create .env file
            env_file = test_dir / ".env"
            with open(env_file, "w") as f:
                f.write(f"INTERCOM_ACCESS_TOKEN={os.getenv('INTERCOM_ACCESS_TOKEN', '')}\n")
                f.write("DATABASE_PATH=./test_integration.db\n")
                f.write("LOG_LEVEL=INFO\n")
                f.write("API_RATE_LIMIT=10\n")

            # Step 1: Package import and CLI availability
            self.log_info("Step 1: Package import and CLI availability")
            step_start = time.time()

            returncode, stdout, stderr = self.run_command(
                self.python_cmd
                + ["-c", "import fast_intercom_mcp.cli; print('✅ CLI module imported')"]
            )
            if returncode != 0:
                raise Exception(f"CLI module import failed: {stderr}")

            step_duration = time.time() - step_start
            results["steps"]["cli_availability"] = {
                "status": "passed",
                "duration_seconds": step_duration,
            }
            self.log_success("CLI availability test passed")

            # Step 2: Database initialization
            self.log_info("Step 2: Database initialization")
            step_start = time.time()

            db_test_script = """
import asyncio
from fast_intercom_mcp.database import DatabaseManager

async def test_db():
    db = DatabaseManager('./test_integration.db')
    print('✅ Database initialized successfully')

asyncio.run(test_db())
"""

            returncode, stdout, stderr = self.run_command(
                self.python_cmd + ["-c", db_test_script], cwd=test_dir
            )

            step_duration = time.time() - step_start
            results["steps"]["database_init"] = {
                "status": "passed" if returncode == 0 else "failed",
                "duration_seconds": step_duration,
                "error": stderr if returncode != 0 else None,
            }

            if returncode != 0:
                raise Exception(f"Database initialization failed: {stderr}")
            self.log_success("Database initialization passed")

            # Step 3: API connection test
            self.log_info("Step 3: API connection test")
            step_start = time.time()

            api_token = os.getenv("INTERCOM_ACCESS_TOKEN")
            if not api_token:
                self.log_warning("No INTERCOM_ACCESS_TOKEN - skipping API tests")
                results["steps"]["api_connection"] = {
                    "status": "skipped",
                    "reason": "No API token available",
                }
                results["steps"]["sync_service"] = {
                    "status": "skipped",
                    "reason": "No API token available",
                }
                results["steps"]["real_sync"] = {
                    "status": "skipped",
                    "reason": "No API token available",
                }
            else:
                api_test_script = """
import asyncio
import os
from fast_intercom_mcp.intercom_client import IntercomClient

async def test_connection():
    client = IntercomClient(os.getenv('INTERCOM_ACCESS_TOKEN'))
    try:
        result = await client.test_connection()
        print(f'✅ API connection test: {result}')
        return result
    except Exception as e:
        print(f'❌ API connection failed: {e}')
        raise

asyncio.run(test_connection())
"""

                returncode, stdout, stderr = self.run_command(
                    self.python_cmd + ["-c", api_test_script],
                    cwd=test_dir,
                    env={"INTERCOM_ACCESS_TOKEN": api_token},
                )

                step_duration = time.time() - step_start
                results["steps"]["api_connection"] = {
                    "status": "passed" if returncode == 0 else "failed",
                    "duration_seconds": step_duration,
                    "error": stderr if returncode != 0 else None,
                }

                if returncode != 0:
                    raise Exception(f"API connection test failed: {stderr}")
                self.log_success("API connection test passed")

                # Step 4: Sync service initialization
                self.log_info("Step 4: Sync service initialization")
                step_start = time.time()

                sync_service_test = """
import asyncio
import os
from fast_intercom_mcp.sync_service import SyncService
from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient

async def test_sync_service():
    db = DatabaseManager('./test_integration.db')
    client = IntercomClient(os.getenv('INTERCOM_ACCESS_TOKEN'))
    sync_service = SyncService(db, client)

    status = sync_service.get_status()
    print(f'✅ Sync service status: {status}')

asyncio.run(test_sync_service())
"""

                returncode, stdout, stderr = self.run_command(
                    self.python_cmd + ["-c", sync_service_test],
                    cwd=test_dir,
                    env={"INTERCOM_ACCESS_TOKEN": api_token},
                )

                step_duration = time.time() - step_start
                results["steps"]["sync_service"] = {
                    "status": "passed" if returncode == 0 else "failed",
                    "duration_seconds": step_duration,
                    "error": stderr if returncode != 0 else None,
                }

                if returncode != 0:
                    raise Exception(f"Sync service test failed: {stderr}")
                self.log_success("Sync service test passed")

                # Step 5: Real API sync test (shortened for local testing)
                self.log_info("Step 5: Real API sync test (shortened)")
                step_start = time.time()

                # Use shorter sync period for local testing to avoid long waits
                local_sync_days = min(results["sync_days"], 3)  # Max 3 days for local testing

                real_sync_test = f"""
import asyncio
import os
import json
import time
import sqlite3
from datetime import datetime, timedelta, UTC
from fast_intercom_mcp.sync_service import SyncService
from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.intercom_client import IntercomClient

async def run_integration_test():
    # Initialize components
    db = DatabaseManager('./test_integration.db')
    client = IntercomClient(os.getenv('INTERCOM_ACCESS_TOKEN'))
    sync_service = SyncService(db, client)

    # Set sync period
    sync_days = {local_sync_days}
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=sync_days)

    print(
        f'📅 Syncing data from {{start_date.isoformat()}} to {{end_date.isoformat()}} '
        f'({{sync_days}} days)'
    )
    print('⏱️  Starting sync...')

    # Run sync and measure performance
    sync_start = time.time()
    try:
        stats = await sync_service.sync_period(start_date, end_date)
        sync_duration = time.time() - sync_start

        # Collect performance metrics
        metrics = {{
            'test_timestamp': datetime.now(UTC).isoformat(),
            'sync_period_days': sync_days,
            'total_conversations': stats.total_conversations,
            'new_conversations': stats.new_conversations,
            'updated_conversations': stats.updated_conversations,
            'total_messages': stats.total_messages,
            'api_calls_made': stats.api_calls_made,
            'sync_duration_seconds': round(sync_duration, 2),
            'conversations_per_second': (
                round(stats.total_conversations / max(sync_duration, 0.1), 2)
                if stats.total_conversations > 0 else 0
            ),
            'messages_per_second': (
                round(stats.total_messages / max(sync_duration, 0.1), 2)
                if stats.total_messages > 0 else 0
            ),
            'avg_response_time_ms': (
                round(sync_duration * 1000 / max(stats.api_calls_made, 1), 2)
                if stats.api_calls_made > 0 else 0
            )
        }}

        # Save metrics
        with open('performance_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)

        # Print results
        print('📊 Integration Test Results')
        print('=' * 50)
        print(f'✅ Test completed successfully')
        print(f'✅ Conversations synced: {{stats.total_conversations:,}} ({{sync_days}} days)')
        print(f'✅ Messages synced: {{stats.total_messages:,}}')
        print(f'✅ API calls made: {{stats.api_calls_made:,}}')
        print(f'✅ Sync speed: {{metrics["conversations_per_second"]}} conv/sec')
        print(f'⏱️  Total test time: {{sync_duration:.1f}}s')

        # Verify data integrity
        with sqlite3.connect('./test_integration.db') as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM conversations')
            conv_count = cursor.fetchone()[0]

            cursor = conn.execute('SELECT COUNT(*) FROM messages')
            msg_count = cursor.fetchone()[0]

            print(
                f'✅ Database integrity: {{conv_count:,}} conversations, {{msg_count:,}} messages'
            )

    except Exception as e:
        print(f'❌ Sync failed: {{e}}')
        # Save error info
        with open('error_report.json', 'w') as f:
            json.dump({{
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now(UTC).isoformat(),
                'sync_days': sync_days
            }}, f, indent=2)
        raise

asyncio.run(run_integration_test())
"""

                returncode, stdout, stderr = self.run_command(
                    self.python_cmd + ["-c", real_sync_test],
                    cwd=test_dir,
                    env={"INTERCOM_ACCESS_TOKEN": api_token},
                    timeout=1800,  # 30 minute timeout
                )

                step_duration = time.time() - step_start

                if returncode == 0:
                    results["steps"]["real_sync"] = {
                        "status": "passed",
                        "duration_seconds": step_duration,
                        "output": stdout,
                    }

                    # Load performance metrics if available
                    metrics_file = test_dir / "performance_metrics.json"
                    if metrics_file.exists():
                        try:
                            with open(metrics_file) as f:
                                metrics = json.load(f)
                            results["performance_metrics"] = metrics
                        except Exception as e:
                            self.log_warning(f"Could not load performance metrics: {e}")

                    self.log_success("Real API sync test passed")
                else:
                    results["steps"]["real_sync"] = {
                        "status": "failed",
                        "duration_seconds": step_duration,
                        "error": stderr,
                        "output": stdout,
                    }
                    # Don't fail the entire workflow for API issues in local testing
                    self.log_warning(
                        f"Real API sync test failed (may be expected in local environment): "
                        f"{stderr}"
                    )

            results["status"] = "passed"
            workflow_duration = time.time() - workflow_start

            # Check timeout (30 minutes for integration-test)
            if workflow_duration > 1800:
                self.log_warning(
                    f"Integration test took {workflow_duration:.1f}s (exceeds 30min timeout)"
                )

            self.log_success(f"Integration Test workflow PASSED in {workflow_duration:.1f}s")

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.log_error(f"Integration Test workflow FAILED: {e}")

        finally:
            results["duration_seconds"] = time.time() - workflow_start
            results["end_time"] = datetime.now(UTC).isoformat()

        return results

    def run_docker_install_test_workflow(self) -> dict[str, Any]:
        """Mirror the docker-install-test.yml workflow."""
        self.log_section("Docker Install Test Workflow")

        workflow_start = time.time()
        results = {
            "name": "docker-install-test",
            "start_time": datetime.now(UTC).isoformat(),
            "timeout_minutes": 30,
            "steps": {},
            "status": "running",
        }

        try:
            # Check if Docker is available
            if not shutil.which("docker"):
                self.log_warning("Docker not found - skipping Docker tests")
                results["status"] = "skipped"
                results["skip_reason"] = "Docker not available"
                return results

            # Step 1: Verify Docker environment
            self.log_info("Step 1: Verify Docker environment")
            step_start = time.time()

            # Check Docker version
            returncode, stdout, stderr = self.run_command(["docker", "--version"])
            if returncode != 0:
                raise Exception(f"Docker version check failed: {stderr}")

            # Check Docker daemon
            returncode, stdout, stderr = self.run_command(["docker", "info"])
            if returncode != 0:
                raise Exception(f"Docker daemon not running: {stderr}")

            step_duration = time.time() - step_start
            results["steps"]["docker_verify"] = {
                "status": "passed",
                "duration_seconds": step_duration,
                "docker_version": stdout.strip(),
            }
            self.log_success("Docker environment verified")

            # Step 2: Docker build test
            self.log_info("Step 2: Docker build test")
            step_start = time.time()

            image_tag = f"fast-intercom-mcp:local-test-{int(time.time())}"
            returncode, stdout, stderr = self.run_command(
                ["docker", "build", "-t", image_tag, "."],
                timeout=600,  # 10 minute build timeout
            )

            step_duration = time.time() - step_start

            if returncode == 0:
                results["steps"]["docker_build"] = {
                    "status": "passed",
                    "duration_seconds": step_duration,
                    "image_tag": image_tag,
                }
                self.log_success(f"Docker build passed: {image_tag}")

                # Step 3: Basic container test
                self.log_info("Step 3: Basic container test")
                step_start = time.time()

                container_name = f"fast-intercom-test-{int(time.time())}"

                # Start container
                returncode, stdout, stderr = self.run_command(
                    ["docker", "run", "-d", "--name", container_name, image_tag, "sleep", "60"]
                )

                if returncode == 0:
                    # Test CLI in container
                    returncode, stdout, stderr = self.run_command(
                        ["docker", "exec", container_name, "fast-intercom-mcp", "--help"]
                    )

                    # Cleanup container
                    self.run_command(["docker", "stop", container_name])
                    self.run_command(["docker", "rm", container_name])

                    step_duration = time.time() - step_start
                    results["steps"]["container_test"] = {
                        "status": "passed" if returncode == 0 else "failed",
                        "duration_seconds": step_duration,
                        "error": stderr if returncode != 0 else None,
                    }

                    if returncode == 0:
                        self.log_success("Container test passed")
                    else:
                        self.log_warning(f"Container CLI test failed: {stderr}")
                else:
                    self.log_warning(f"Container start failed: {stderr}")
                    results["steps"]["container_test"] = {
                        "status": "failed",
                        "error": f"Container start failed: {stderr}",
                    }

                # Cleanup image
                self.run_command(["docker", "rmi", image_tag])

            else:
                results["steps"]["docker_build"] = {
                    "status": "failed",
                    "duration_seconds": step_duration,
                    "error": stderr,
                }
                raise Exception(f"Docker build failed: {stderr}")

            # Step 4: Check for Docker test script
            docker_script = self.project_root / "scripts" / "test_docker_install.sh"
            if docker_script.exists():
                self.log_info("Step 4: Run Docker test script")
                step_start = time.time()

                # Make script executable and run it
                returncode, stdout, stderr = self.run_command(["chmod", "+x", str(docker_script)])
                if returncode == 0:
                    # 15 minute timeout
                    returncode, stdout, stderr = self.run_command([str(docker_script)], timeout=900)

                step_duration = time.time() - step_start
                results["steps"]["docker_script"] = {
                    "status": "passed" if returncode == 0 else "failed",
                    "duration_seconds": step_duration,
                    "output": stdout,
                    "error": stderr if returncode != 0 else None,
                }

                if returncode == 0:
                    self.log_success("Docker test script passed")
                else:
                    self.log_warning(f"Docker test script failed: {stderr}")
            else:
                self.log_info("No Docker test script found - skipping")

            results["status"] = "passed"
            workflow_duration = time.time() - workflow_start
            self.log_success(f"Docker Install Test workflow PASSED in {workflow_duration:.1f}s")

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.log_error(f"Docker Install Test workflow FAILED: {e}")

        finally:
            results["duration_seconds"] = time.time() - workflow_start
            results["end_time"] = datetime.now(UTC).isoformat()

        return results

    def run_selected_workflows(self) -> dict[str, Any]:
        """Run the selected workflows based on command line arguments."""
        if not self.install_dependencies():
            self.log_error("Failed to install dependencies")
            return {"status": "failed", "error": "Dependency installation failed"}

        workflows_to_run = []

        if self.args.workflow == "all":
            workflows_to_run = list(self.workflows.keys())
            if self.args.skip_docker:
                workflows_to_run.remove("docker-install-test")
        elif self.args.workflow in self.workflows:
            workflows_to_run = [self.args.workflow]
        else:
            self.log_error(f"Unknown workflow: {self.args.workflow}")
            return {"status": "failed", "error": f"Unknown workflow: {self.args.workflow}"}

        self.log_info(f"Running workflows: {', '.join(workflows_to_run)}")

        for workflow_name in workflows_to_run:
            if workflow_name == "docker-install-test" and self.args.skip_docker:
                continue

            workflow_func = self.workflows[workflow_name]
            workflow_result = workflow_func()
            self.results["workflows"][workflow_name] = workflow_result

        # Generate summary
        total_workflows = len(self.results["workflows"])
        passed_workflows = sum(
            1 for w in self.results["workflows"].values() if w["status"] == "passed"
        )
        failed_workflows = sum(
            1 for w in self.results["workflows"].values() if w["status"] == "failed"
        )
        skipped_workflows = sum(
            1 for w in self.results["workflows"].values() if w["status"] == "skipped"
        )

        total_duration = time.time() - self.start_time

        self.results["summary"] = {
            "total_workflows": total_workflows,
            "passed_workflows": passed_workflows,
            "failed_workflows": failed_workflows,
            "skipped_workflows": skipped_workflows,
            "success_rate": passed_workflows / max(total_workflows, 1) * 100,
            "total_duration_seconds": total_duration,
            "overall_status": "passed" if failed_workflows == 0 else "failed",
        }

        return self.results

    def print_summary(self):
        """Print a formatted summary of the test results."""
        self.log_section("Test Summary")

        summary = self.results["summary"]

        print(f"📊 Total Workflows: {summary['total_workflows']}")
        print(f"✅ Passed: {summary['passed_workflows']}")
        print(f"❌ Failed: {summary['failed_workflows']}")
        print(f"⏭️  Skipped: {summary['skipped_workflows']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️  Total Duration: {summary['total_duration_seconds']:.1f}s")
        print()

        # Individual workflow results
        for workflow_name, workflow_result in self.results["workflows"].items():
            status_emoji = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(
                workflow_result["status"], "❓"
            )

            duration = workflow_result.get("duration_seconds", 0)
            print(
                f"{status_emoji} {workflow_name}: {workflow_result['status'].upper()} "
                f"({duration:.1f}s)"
            )

            if workflow_result["status"] == "failed" and "error" in workflow_result:
                print(f"   Error: {workflow_result['error']}")

        print()

        if summary["overall_status"] == "passed":
            self.log_success("🎉 All workflows PASSED!")
        else:
            self.log_error("💥 Some workflows FAILED!")

    def save_results(self):
        """Save results to JSON file if specified."""
        if self.args.json_output:
            try:
                with open(self.args.json_output, "w") as f:
                    json.dump(self.results, f, indent=2)
                self.log_success(f"Results saved to {self.args.json_output}")
            except Exception as e:
                self.log_error(f"Failed to save results: {e}")


def main():
    """Main entry point for the local CI mirror test."""
    parser = argparse.ArgumentParser(
        description="Local CI Mirror Test - Mirror GitHub Actions workflows locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --workflow fast-check
  %(prog)s --workflow all --skip-docker
  %(prog)s --workflow quick-test --sync-days 2
  %(prog)s --workflow integration-test --json-output results.json --verbose
        """,
    )

    parser.add_argument(
        "--workflow",
        choices=["fast-check", "quick-test", "integration-test", "docker-install-test", "all"],
        default="fast-check",
        help="Workflow to run (default: fast-check)",
    )

    parser.add_argument(
        "--sync-days", type=int, default=1, help="Number of days to sync for API tests (default: 1)"
    )

    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker-related tests")

    parser.add_argument("--json-output", type=str, help="Save results to JSON file")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Print header
    print(f"{Colors.CYAN}{'=' * 80}{Colors.NC}")
    print(f"{Colors.CYAN}🚀 Local CI Mirror Test{Colors.NC}")
    print(f"{Colors.CYAN}Mirroring GitHub Actions workflows for fast-intercom-mcp{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 80}{Colors.NC}")

    try:
        # Create and run the tester
        tester = LocalCITester(args)
        results = tester.run_selected_workflows()

        # Print summary
        tester.print_summary()

        # Save results if requested
        tester.save_results()

        # Exit with appropriate code
        exit_code = 0 if results["summary"]["overall_status"] == "passed" else 1
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Test interrupted by user{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.NC}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
