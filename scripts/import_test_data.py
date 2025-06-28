#!/usr/bin/env python3
"""
Import test data into FastIntercom MCP database
Loads generated test data for testing and development
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class TestDataImporter:
    """Import test data into FastIntercom MCP database"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """Connect to the database"""
        print(f"Connecting to database: {self.db_path}")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")

        # Check if tables exist
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
        )
        if not self.cursor.fetchone():
            print("Error: Database tables not found. Run 'fast-intercom-mcp init' first.")
            sys.exit(1)

    def import_conversation(self, conversation: dict[str, Any]) -> bool:
        """Import a single conversation"""
        try:
            # Extract contact information
            contacts = conversation.get("contacts", {}).get("contacts", [])
            customer_email = contacts[0].get("email", "") if contacts else ""
            customer_name = contacts[0].get("name", "") if contacts else ""

            # Insert conversation
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO conversations (
                    id, created_at, updated_at, customer_email, customer_name,
                    admin_assignee_id, state, priority, tags, source_type,
                    source_delivered_as, subject, conversation_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    conversation["id"],
                    conversation["created_at"],
                    conversation["updated_at"],
                    customer_email,
                    customer_name,
                    conversation.get("admin_assignee_id"),
                    conversation.get("state", "open"),
                    conversation.get("priority", "medium"),
                    json.dumps(conversation.get("tags", {}).get("tags", [])),
                    conversation.get("source", {}).get("type", "conversation"),
                    conversation.get("source", {}).get("delivered_as", "customer_initiated"),
                    conversation.get("source", {}).get("subject", ""),
                    json.dumps(conversation),
                ),
            )

            # Import messages if present
            conversation_parts = conversation.get("conversation_parts", {}).get(
                "conversation_parts", []
            )
            for message in conversation_parts:
                self.import_message(conversation["id"], message)

            return True

        except Exception as e:
            print(f"Error importing conversation {conversation.get('id', 'unknown')}: {e}")
            return False

    def import_message(self, conversation_id: str, message: dict[str, Any]) -> bool:
        """Import a single message"""
        try:
            author = message.get("author", {})

            self.cursor.execute(
                """
                INSERT OR REPLACE INTO messages (
                    id, conversation_id, created_at, author_type, author_id,
                    author_name, body, message_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    message["id"],
                    conversation_id,
                    message["created_at"],
                    author.get("type", "unknown"),
                    author.get("id", ""),
                    author.get("name", ""),
                    message.get("body", ""),
                    json.dumps(message),
                ),
            )

            return True

        except Exception as e:
            print(f"Error importing message {message.get('id', 'unknown')}: {e}")
            return False

    def import_dataset(self, data: dict[str, Any]) -> dict[str, int]:
        """Import complete test dataset"""
        conversations = data.get("conversations", [])
        total = len(conversations)

        print(f"\nImporting {total} conversations...")

        imported_conversations = 0
        imported_messages = 0
        failed_conversations = 0

        for i, conversation in enumerate(conversations):
            if self.import_conversation(conversation):
                imported_conversations += 1
                # Count messages
                parts = conversation.get("conversation_parts", {}).get("conversation_parts", [])
                imported_messages += len(parts)
            else:
                failed_conversations += 1

            # Progress indicator
            if (i + 1) % 100 == 0 or i == total - 1:
                progress = (i + 1) / total * 100
                print(f"Progress: {i + 1}/{total} ({progress:.1f}%)")

        # Commit all changes
        self.conn.commit()

        return {
            "imported_conversations": imported_conversations,
            "imported_messages": imported_messages,
            "failed_conversations": failed_conversations,
        }

    def verify_import(self) -> dict[str, int]:
        """Verify imported data"""
        # Count conversations
        self.cursor.execute("SELECT COUNT(*) FROM conversations")
        conversation_count = self.cursor.fetchone()[0]

        # Count messages
        self.cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = self.cursor.fetchone()[0]

        # Get date range
        self.cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM conversations")
        min_date, max_date = self.cursor.fetchone()

        return {
            "total_conversations": conversation_count,
            "total_messages": message_count,
            "min_date": min_date,
            "max_date": max_date,
        }

    def create_sync_period(self) -> None:
        """Create a sync period record for the imported data"""
        now = int(datetime.now().timestamp())

        # Get date range of imported data
        self.cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM conversations")
        start_date, end_date = self.cursor.fetchone()

        if start_date and end_date:
            self.cursor.execute(
                """
                INSERT INTO sync_periods (
                    start_date, end_date, conversations_synced,
                    messages_synced, sync_duration_seconds, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    start_date,
                    end_date,
                    self.verify_import()["total_conversations"],
                    self.verify_import()["total_messages"],
                    0,  # Instant import
                    now,
                ),
            )
            self.conn.commit()
            print("Created sync period record for imported data")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import test data into FastIntercom MCP database")
    parser.add_argument("input_file", help="Input JSON file containing test data")
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Database path (default: ~/.fast-intercom-mcp/data.db)",
    )
    parser.add_argument(
        "--create-sync-period",
        action="store_true",
        help="Create a sync period record for the imported data",
    )
    parser.add_argument(
        "--clear-existing", action="store_true", help="Clear existing data before import"
    )

    args = parser.parse_args()

    # Determine database path
    if args.db_path:
        db_path = args.db_path
    else:
        # Use default location
        db_path = Path.home() / ".fast-intercom-mcp" / "data.db"
        if not db_path.exists():
            # Try test location
            db_path = Path.home() / ".fast-intercom-mcp-test" / "data.db"
            if not db_path.exists():
                print("Error: No database found. Run 'fast-intercom-mcp init' first.")
                sys.exit(1)

    # Load test data
    print(f"Loading test data from: {args.input_file}")
    try:
        with open(args.input_file) as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading test data: {e}")
        sys.exit(1)

    # Create importer and import data
    importer = TestDataImporter(str(db_path))

    try:
        importer.connect()

        # Clear existing data if requested
        if args.clear_existing:
            print("Clearing existing data...")
            importer.cursor.execute("DELETE FROM messages")
            importer.cursor.execute("DELETE FROM conversations")
            importer.cursor.execute("DELETE FROM sync_periods")
            importer.conn.commit()

        # Import the dataset
        results = importer.import_dataset(data)

        print("\nImport completed!")
        print(f"  Imported conversations: {results['imported_conversations']}")
        print(f"  Imported messages: {results['imported_messages']}")
        print(f"  Failed conversations: {results['failed_conversations']}")

        # Verify import
        verification = importer.verify_import()
        print("\nDatabase verification:")
        print(f"  Total conversations: {verification['total_conversations']}")
        print(f"  Total messages: {verification['total_messages']}")

        if verification["min_date"] and verification["max_date"]:
            min_date = datetime.fromtimestamp(verification["min_date"])
            max_date = datetime.fromtimestamp(verification["max_date"])
            print(f"  Date range: {min_date.date()} to {max_date.date()}")

        # Create sync period if requested
        if args.create_sync_period:
            importer.create_sync_period()

    finally:
        importer.close()


if __name__ == "__main__":
    main()
