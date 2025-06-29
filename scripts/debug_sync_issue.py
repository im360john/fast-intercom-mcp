#!/usr/bin/env python3
"""Debug script to investigate why 1-day sync returns thousands of conversations."""

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from fast_intercom_mcp.intercom_client import IntercomClient

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)


async def main():
    """Run debug sync test."""
    # Get API token
    token = os.environ.get("INTERCOM_ACCESS_TOKEN")
    if not token:
        print("Error: INTERCOM_ACCESS_TOKEN environment variable not set")
        return

    # Create client
    client = IntercomClient(token)

    # Test connection
    if not await client.test_connection():
        print("Failed to connect to Intercom API")
        return

    print("Connected to Intercom API")

    # Set up date range for last 24 hours
    end_date = datetime.now(tz=UTC)
    start_date = end_date - timedelta(days=1)

    print("\nTesting sync for date range:")
    print(f"  Start: {start_date} (timestamp: {int(start_date.timestamp())})")
    print(f"  End: {end_date} (timestamp: {int(end_date.timestamp())})")

    # Fetch conversations
    print("\nFetching conversations...")
    conversations = await client.fetch_conversations_for_period(
        start_date=start_date,
        end_date=end_date,
        progress_callback=lambda msg: print(f"Progress: {msg}"),
    )

    print(f"\nTotal conversations returned: {len(conversations)}")

    # Analyze results
    if conversations:
        # Sample first 10 conversations
        print("\nSample of first 10 conversations:")
        for i, conv in enumerate(conversations[:10]):
            created_date = conv.created_at.date()
            days_old = (datetime.now(tz=UTC).date() - created_date).days

            print(f"\n{i+1}. Conversation {conv.id}:")
            print(f"   Created: {conv.created_at} ({days_old} days ago)")
            print(f"   Updated: {conv.updated_at}")
            print(f"   Messages: {len(conv.messages)}")
            print(f"   Is new: {start_date.date() <= created_date <= end_date.date()}")

        # Analyze age distribution
        age_distribution = {}
        new_conversations = 0

        for conv in conversations:
            created_date = conv.created_at.date()
            days_old = (datetime.now(tz=UTC).date() - created_date).days

            if days_old == 0:
                new_conversations += 1

            # Group by age ranges
            if days_old == 0:
                age_group = "Today"
            elif days_old == 1:
                age_group = "Yesterday"
            elif days_old <= 7:
                age_group = "This week"
            elif days_old <= 30:
                age_group = "This month"
            elif days_old <= 90:
                age_group = "Last 3 months"
            else:
                age_group = "Older than 3 months"

            age_distribution[age_group] = age_distribution.get(age_group, 0) + 1

        print("\n\nAge distribution of conversations:")
        print(f"  New conversations (created today): {new_conversations}")
        print(f"  Conversations with updates today: {len(conversations)}")
        print("\n  By creation age:")
        for age_group in [
            "Today",
            "Yesterday",
            "This week",
            "This month",
            "Last 3 months",
            "Older than 3 months",
        ]:
            if age_group in age_distribution:
                print(f"    {age_group}: {age_distribution[age_group]}")


if __name__ == "__main__":
    asyncio.run(main())
