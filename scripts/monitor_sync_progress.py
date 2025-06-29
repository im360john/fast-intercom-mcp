#!/usr/bin/env python3
"""
Monitor sync progress in real time
"""

import os
import sqlite3
import time
from pathlib import Path


def get_test_workspace() -> Path:
    """Get the test workspace directory with organized subdirectories."""
    # Check environment variable first
    if workspace_env := os.environ.get("FASTINTERCOM_TEST_WORKSPACE"):
        workspace = Path(workspace_env)
    else:
        # Find project root (look for pyproject.toml)
        current_dir = Path.cwd()
        project_root = current_dir

        # Search up the directory tree for pyproject.toml
        while current_dir != current_dir.parent:
            if (current_dir / "pyproject.toml").exists():
                project_root = current_dir
                break
            current_dir = current_dir.parent

        workspace = project_root / ".test-workspace"

    # Create organized subdirectories
    workspace.mkdir(exist_ok=True)
    (workspace / "data").mkdir(exist_ok=True)
    (workspace / "logs").mkdir(exist_ok=True)
    (workspace / "results").mkdir(exist_ok=True)

    return workspace


def get_db_stats(db_path):
    if not Path(db_path).exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversations = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM messages")
        messages = cursor.fetchone()[0]

        conn.close()

        size_mb = Path(db_path).stat().st_size / 1024 / 1024

        return {
            "conversations": conversations,
            "messages": messages,
            "size_mb": size_mb,
        }
    except Exception:
        return None


def main():
    # Use standardized workspace, then fall back to common locations
    workspace = get_test_workspace()
    possible_paths = [
        workspace / "data" / "data.db",
        Path.home() / ".fast-intercom-mcp" / "data.db",
        Path.home() / ".fast-intercom-mcp-test" / "data.db",
        Path.home() / ".fast-intercom-mcp-full-test" / "data.db",
    ]

    # Find the first existing database
    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        print("❌ No database found in any of the expected locations:")
        for path in possible_paths:
            print(f"  - {path}")
        return

    print(f"📊 Monitoring database: {db_path}")
    print("📊 Monitoring sync progress...")
    print("Press Ctrl+C to stop monitoring")
    print("-" * 60)

    start_time = time.time()

    try:
        while True:
            stats = get_db_stats(db_path)
            elapsed = time.time() - start_time

            if stats:
                conversations = stats["conversations"]
                messages = stats["messages"]
                size_mb = stats["size_mb"]

                # Calculate rate
                conversations_per_sec = conversations / max(elapsed, 1)

                # Show progress
                print(
                    f"⏱️ {elapsed:5.0f}s | 💬 {conversations:6,} conv | "
                    f"✉️ {messages:7,} msg | 💾 {size_mb:6.1f}MB | "
                    f"🚀 {conversations_per_sec:5.1f}/sec"
                )

                # Track the last count for potential future use
                _ = conversations  # last_conversations variable removed as unused
            else:
                print(f"⏱️ {elapsed:5.0f}s | ⌛ Waiting for database...")

            time.sleep(10)  # Update every 10 seconds

    except KeyboardInterrupt:
        print("\n📊 Monitoring stopped")
        if stats:
            print(
                f"Final stats: {stats['conversations']:,} conversations, "
                f"{stats['messages']:,} messages, {stats['size_mb']:.1f}MB"
            )


if __name__ == "__main__":
    main()
