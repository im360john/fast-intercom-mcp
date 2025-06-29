#!/usr/bin/env python3
"""
Record performance baseline for FastIntercom MCP
Captures current performance metrics for future comparison
"""

import argparse
import json
import os
import platform
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    print("Warning: psutil not installed. Some metrics will be unavailable.")
    print("Install with: pip install psutil")
    psutil = None


class PerformanceBaseline:
    """Record and manage performance baselines"""

    def __init__(self, baseline_file: str = "performance_baselines.json"):
        self.baseline_file = baseline_file
        self.baselines = self.load_baselines()

    def load_baselines(self) -> dict[str, Any]:
        """Load existing baselines from file"""
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file) as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load baselines: {e}")
        return {}

    def save_baselines(self):
        """Save baselines to file"""
        with open(self.baseline_file, "w") as f:
            json.dump(self.baselines, f, indent=2)
        print(f"Baselines saved to: {self.baseline_file}")

    def get_system_info(self) -> dict[str, Any]:
        """Gather system information"""
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        }

        if psutil:
            info["total_memory_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)

        # Get SQLite version
        try:
            conn = sqlite3.connect(":memory:")
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            info["sqlite_version"] = cursor.fetchone()[0]
            conn.close()
        except Exception:
            info["sqlite_version"] = "unknown"

        return info

    def measure_import_performance(self) -> dict[str, float] | None:
        """Measure import and startup performance"""
        print("Measuring import performance...")

        # Measure import time
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import fast_intercom_mcp; print('imported')"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                print(f"Import failed: {result.stderr}")
                return None
            import_time = time.time() - start_time
        except Exception as e:
            print(f"Error measuring import: {e}")
            return None

        # Measure CLI startup
        start_time = time.time()
        try:
            result = subprocess.run(
                ["fast-intercom-mcp", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                # Try with python -m
                result = subprocess.run(
                    [sys.executable, "-m", "fast_intercom_mcp", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            cli_startup_time = time.time() - start_time
        except Exception as e:
            print(f"Error measuring CLI startup: {e}")
            cli_startup_time = None

        return {
            "import_time_seconds": round(import_time, 3),
            "cli_startup_seconds": round(cli_startup_time, 3) if cli_startup_time else None,
        }

    def measure_database_performance(self, db_path: str | None = None) -> dict[str, Any] | None:
        """Measure database query performance"""
        print("Measuring database performance...")

        if not db_path:
            # Try to find database
            default_path = Path.home() / ".fast-intercom-mcp" / "data.db"
            test_path = Path.home() / ".fast-intercom-mcp-test" / "data.db"

            if default_path.exists():
                db_path = str(default_path)
            elif test_path.exists():
                db_path = str(test_path)
            else:
                print("No database found for performance testing")
                return None

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Count data
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conv_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM messages")
            msg_count = cursor.fetchone()[0]

            if conv_count == 0:
                print("No data in database for performance testing")
                return None

            # Measure query performance
            queries = {
                "count_conversations": "SELECT COUNT(*) FROM conversations",
                "recent_conversations": """
                    SELECT id, customer_email, updated_at
                    FROM conversations
                    ORDER BY updated_at DESC
                    LIMIT 100
                """,
                "search_by_email": """
                    SELECT id, customer_email, state
                    FROM conversations
                    WHERE customer_email LIKE '%@example.com'
                    LIMIT 50
                """,
                "conversation_with_messages": """
                    SELECT c.*, m.*
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.id = (SELECT id FROM conversations LIMIT 1)
                """,
                "aggregate_stats": """
                    SELECT
                        COUNT(DISTINCT c.id) as conv_count,
                        COUNT(m.id) as msg_count,
                        AVG(json_array_length(c.tags)) as avg_tags
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                """,
            }

            query_times = {}
            for name, query in queries.items():
                start = time.time()
                cursor.execute(query)
                cursor.fetchall()  # Fetch all results
                query_times[name] = round((time.time() - start) * 1000, 2)  # ms

            # Get database size
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)

            conn.close()

            return {
                "conversation_count": conv_count,
                "message_count": msg_count,
                "database_size_mb": round(db_size_mb, 2),
                "query_times_ms": query_times,
                "avg_query_time_ms": round(sum(query_times.values()) / len(query_times), 2),
            }

        except Exception as e:
            print(f"Error measuring database performance: {e}")
            return None

    def run_integration_test_baseline(self) -> dict[str, Any] | None:
        """Run a quick integration test to measure sync performance"""
        print("Running integration test for baseline...")

        script_path = Path(__file__).parent / "run_integration_test.sh"
        if not script_path.exists():
            print("Integration test script not found")
            return None

        try:
            # Run quick integration test
            result = subprocess.run(
                [str(script_path), "--quick", "--output", "baseline_test.json"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                print(f"Integration test failed: {result.stderr}")
                return None

            # Load results
            if os.path.exists("baseline_test.json"):
                with open("baseline_test.json") as f:
                    test_data = json.load(f)

                # Extract key metrics
                metrics = test_data.get("performance_metrics", {})
                os.remove("baseline_test.json")  # Clean up

                return {
                    "sync_conversations_per_second": metrics.get("sync_speed"),
                    "sync_duration_seconds": metrics.get("sync_duration"),
                    "conversations_synced": metrics.get("conversations_synced"),
                    "messages_synced": metrics.get("messages_synced"),
                }

        except subprocess.TimeoutExpired:
            print("Integration test timed out")
        except Exception as e:
            print(f"Error running integration test: {e}")

        return None

    def measure_memory_usage(self) -> dict[str, float] | None:
        """Measure memory usage of key operations"""
        if not psutil:
            return None

        print("Measuring memory usage...")

        try:
            # Start server and measure memory
            process = subprocess.Popen(
                [sys.executable, "-m", "fast_intercom_mcp", "start", "--test-mode"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for startup
            time.sleep(3)

            if process.poll() is not None:
                print("Server failed to start")
                return None

            # Get memory usage
            proc_info = psutil.Process(process.pid)
            memory_mb = proc_info.memory_info().rss / (1024 * 1024)

            # Clean up
            process.terminate()
            process.wait(timeout=5)

            return {"server_startup_memory_mb": round(memory_mb, 2)}

        except Exception as e:
            print(f"Error measuring memory: {e}")
            return None

    def record_baseline(self, tag: str, description: str = "", run_integration: bool = False):
        """Record a complete performance baseline"""
        print(f"Recording performance baseline: {tag}")
        print("=" * 60)

        baseline = {
            "tag": tag,
            "description": description,
            "date": datetime.now().isoformat(),
            "system": self.get_system_info(),
            "metrics": {},
        }

        # Measure import/startup performance
        import_metrics = self.measure_import_performance()
        if import_metrics:
            baseline["metrics"].update(import_metrics)

        # Measure database performance
        db_metrics = self.measure_database_performance()
        if db_metrics:
            baseline["metrics"].update(db_metrics)

        # Measure memory usage
        memory_metrics = self.measure_memory_usage()
        if memory_metrics:
            baseline["metrics"].update(memory_metrics)

        # Run integration test if requested
        if run_integration:
            integration_metrics = self.run_integration_test_baseline()
            if integration_metrics:
                baseline["metrics"].update(integration_metrics)

        # Store baseline
        self.baselines[tag] = baseline
        self.save_baselines()

        # Display results
        print("\nBaseline recorded successfully!")
        print(f"Tag: {tag}")
        print(f"Date: {baseline['date']}")
        print("\nKey Metrics:")
        for key, value in baseline["metrics"].items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    def list_baselines(self):
        """List all recorded baselines"""
        if not self.baselines:
            print("No baselines recorded yet")
            return

        print("Recorded baselines:")
        print("=" * 60)

        for tag, baseline in sorted(self.baselines.items()):
            date = baseline.get("date", "unknown")
            desc = baseline.get("description", "")
            metrics = baseline.get("metrics", {})

            print(f"\nTag: {tag}")
            print(f"Date: {date}")
            if desc:
                print(f"Description: {desc}")
            print(f"Metrics recorded: {len(metrics)}")


def main():
    parser = argparse.ArgumentParser(description="Record performance baseline for FastIntercom MCP")
    parser.add_argument(
        "--tag",
        type=str,
        required=True,
        help="Tag for this baseline (e.g., 'v0.3.0', 'pre-optimization')",
    )
    parser.add_argument("--description", type=str, default="", help="Description of this baseline")
    parser.add_argument(
        "--run-integration",
        action="store_true",
        help="Run integration test for sync performance baseline",
    )
    parser.add_argument(
        "--baseline-file",
        type=str,
        default="performance_baselines.json",
        help="File to store baselines (default: performance_baselines.json)",
    )
    parser.add_argument("--list", action="store_true", help="List existing baselines")

    args = parser.parse_args()

    baseline = PerformanceBaseline(args.baseline_file)

    if args.list:
        baseline.list_baselines()
    else:
        baseline.record_baseline(args.tag, args.description, args.run_integration)


if __name__ == "__main__":
    main()
