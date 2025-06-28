#!/usr/bin/env python3
"""
Generate test data for FastIntercom MCP testing
Creates realistic conversation and message data for testing purposes
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from typing import Any

# Realistic test data templates
CUSTOMER_NAMES = [
    "Alice Johnson",
    "Bob Smith",
    "Carol Davis",
    "David Wilson",
    "Emma Brown",
    "Frank Miller",
    "Grace Lee",
    "Henry Garcia",
    "Isabel Martinez",
    "Jack Anderson",
    "Karen Taylor",
    "Liam Moore",
    "Maria Rodriguez",
    "Nathan Clark",
    "Olivia Walker",
    "Peter Hall",
]

CUSTOMER_EMAILS = [
    "alice@example.com",
    "bob@techcorp.io",
    "carol@startup.co",
    "david@enterprise.net",
    "emma@consulting.org",
    "frank@agency.com",
    "grace@product.io",
    "henry@service.co",
    "isabel@platform.com",
    "jack@solutions.net",
    "karen@digital.io",
    "liam@creative.co",
    "maria@global.com",
    "nathan@local.net",
    "olivia@mobile.io",
    "peter@cloud.co",
]

ADMIN_NAMES = [
    "Support Agent 1",
    "Support Agent 2",
    "Support Agent 3",
    "Customer Success Manager",
    "Technical Support Lead",
]

CONVERSATION_SUBJECTS = [
    "How do I reset my password?",
    "Billing question about my subscription",
    "Feature request: Dark mode",
    "Bug report: Login issues",
    "How to integrate with API?",
    "Upgrade plan inquiry",
    "Account deletion request",
    "Performance issues with dashboard",
    "Mobile app not syncing",
    "Export data question",
    "Team collaboration features",
    "Security and compliance inquiry",
    "Onboarding assistance needed",
    "Webhook configuration help",
    "Custom integration support",
]

MESSAGE_TEMPLATES = {
    "customer_initial": [
        "Hi, I'm having trouble with {issue}. Can you help?",
        "Hello, I need assistance with {issue}.",
        "I'm experiencing issues with {issue}. This started {timeframe}.",
        "Quick question about {issue}.",
        "Can someone help me understand {issue}?",
    ],
    "admin_response": [
        "Hi {customer_name}, I'd be happy to help you with that.",
        "Thank you for reaching out. Let me look into this for you.",
        "I understand your concern about {issue}. Let me help.",
        "Thanks for contacting us. I can definitely assist with this.",
        "Hello {customer_name}, I'll help you resolve this issue.",
    ],
    "customer_followup": [
        "Thanks for the quick response!",
        "That makes sense. What should I do next?",
        "I tried that but still having issues.",
        "Perfect, that solved my problem. Thank you!",
        "One more question about this...",
    ],
    "admin_resolution": [
        "Great! I'm glad that resolved your issue. Is there anything else I can help with?",
        "Perfect! I'll mark this as resolved. Feel free to reach out if you need anything else.",
        "Excellent! Don't hesitate to contact us if you have any other questions.",
        "I'm happy I could help. Have a great day!",
        "Wonderful! I'll close this ticket now. Take care!",
    ],
}

TAGS = ["billing", "technical", "feature-request", "bug", "urgent", "vip", "new-customer"]
PRIORITIES = ["low", "medium", "high", "urgent"]
CHANNELS = ["email", "messenger", "chat", "social"]


def generate_conversation_id():
    """Generate a unique conversation ID"""
    return f"conv_{random.randint(100000, 999999)}"


def generate_message_id():
    """Generate a unique message ID"""
    return f"msg_{random.randint(1000000, 9999999)}"


def generate_contact_id():
    """Generate a unique contact ID"""
    return f"contact_{random.randint(10000, 99999)}"


def generate_admin_id():
    """Generate a unique admin ID"""
    return f"admin_{random.randint(100, 999)}"


def generate_timestamp(base_time: datetime, offset_hours: int = 0) -> int:
    """Generate a Unix timestamp with optional offset"""
    target_time = base_time + timedelta(hours=offset_hours)
    return int(target_time.timestamp())


def generate_message(
    message_type: str,
    author_type: str,
    author_id: str,
    author_name: str,
    timestamp: int,
    conversation_context: dict[str, Any],
) -> dict[str, Any]:
    """Generate a single message"""
    templates = MESSAGE_TEMPLATES.get(message_type, ["Generic message content"])
    body = random.choice(templates).format(
        issue=conversation_context.get("issue", "an issue"),
        customer_name=conversation_context.get("customer_name", "there"),
        timeframe=random.choice(["yesterday", "this morning", "last week", "a few days ago"]),
    )

    return {
        "id": generate_message_id(),
        "type": "conversation_message",
        "created_at": timestamp,
        "body": body,
        "author": {
            "id": author_id,
            "type": author_type,
            "name": author_name,
            "email": author_name.lower().replace(" ", ".") + "@support.com"
            if author_type == "admin"
            else None,
        },
        "attachments": [],
    }


def generate_conversation(
    base_time: datetime,
    conversation_index: int,  # noqa: ARG001
    include_messages: bool = True,
) -> dict[str, Any]:
    """Generate a complete conversation with messages"""
    # Random time offset for conversation creation (0-30 days ago)
    days_ago = random.randint(0, 30)
    created_at = base_time - timedelta(days=days_ago)

    # Customer details
    customer_index = random.randint(0, len(CUSTOMER_NAMES) - 1)
    customer_name = CUSTOMER_NAMES[customer_index]
    customer_email = CUSTOMER_EMAILS[customer_index]
    customer_id = generate_contact_id()

    # Admin details
    admin_name = random.choice(ADMIN_NAMES)
    admin_id = generate_admin_id()

    # Conversation details
    subject = random.choice(CONVERSATION_SUBJECTS)
    conversation_id = generate_conversation_id()

    # Build conversation structure
    conversation = {
        "id": conversation_id,
        "created_at": generate_timestamp(created_at),
        "updated_at": generate_timestamp(created_at, random.randint(1, 48)),
        "waiting_since": None,
        "snoozed_until": None,
        "type": "conversation",
        "contacts": {
            "type": "contact.list",
            "contacts": [
                {
                    "id": customer_id,
                    "type": "contact",
                    "name": customer_name,
                    "email": customer_email,
                }
            ],
        },
        "first_contact_reply": {
            "created_at": generate_timestamp(created_at, 1),
            "type": "conversation_part",
        },
        "admin_assignee_id": admin_id,
        "team_assignee_id": None,
        "open": random.choice([True, False]),
        "state": random.choice(["open", "closed", "snoozed"]),
        "read": True,
        "tags": {"type": "tag.list", "tags": random.sample(TAGS, random.randint(0, 3))},
        "priority": random.choice(PRIORITIES),
        "source": {
            "type": "conversation",
            "delivered_as": random.choice(["customer_initiated", "admin_initiated"]),
            "subject": subject,
            "body": f"<p>{subject}</p>",
            "author": {
                "id": customer_id,
                "type": "user",
                "name": customer_name,
                "email": customer_email,
            },
            "attachments": [],
        },
        "conversation_message": {
            "type": "conversation_message",
            "subject": subject,
            "body": f"<p>{subject}</p>",
            "author": {
                "id": customer_id,
                "type": "user",
                "name": customer_name,
                "email": customer_email,
            },
            "attachments": [],
        },
        "statistics": {
            "time_to_assignment": random.randint(60, 3600),
            "time_to_admin_reply": random.randint(300, 7200),
            "time_to_first_close": random.randint(3600, 86400),
            "time_to_last_close": random.randint(3600, 86400),
            "median_time_to_reply": random.randint(600, 3600),
            "first_contact_reply_at": generate_timestamp(created_at, 1),
            "first_assignment_at": generate_timestamp(created_at, 0.5),
            "first_admin_reply_at": generate_timestamp(created_at, 2),
            "first_close_at": generate_timestamp(created_at, 24),
            "last_assignment_at": generate_timestamp(created_at, 0.5),
            "last_assignment_admin_reply_at": generate_timestamp(created_at, 2),
            "last_contact_reply_at": generate_timestamp(created_at, 3),
            "last_admin_reply_at": generate_timestamp(created_at, 4),
            "last_close_at": generate_timestamp(created_at, 24),
            "count_assignments": 1,
            "count_reopens": 0,
            "count_conversation_parts": random.randint(2, 10),
        },
    }

    # Generate conversation parts (messages) if requested
    if include_messages:
        conversation_parts = []
        context = {"issue": subject, "customer_name": customer_name.split()[0]}

        # Initial customer message
        conversation_parts.append(
            generate_message(
                "customer_initial",
                "user",
                customer_id,
                customer_name,
                generate_timestamp(created_at, 0),
                context,
            )
        )

        # Admin response
        conversation_parts.append(
            generate_message(
                "admin_response",
                "admin",
                admin_id,
                admin_name,
                generate_timestamp(created_at, 2),
                context,
            )
        )

        # Random number of follow-up messages
        num_followups = random.randint(0, 3)
        for i in range(num_followups):
            if i % 2 == 0:
                conversation_parts.append(
                    generate_message(
                        "customer_followup",
                        "user",
                        customer_id,
                        customer_name,
                        generate_timestamp(created_at, 3 + i * 2),
                        context,
                    )
                )
            else:
                conversation_parts.append(
                    generate_message(
                        "admin_response",
                        "admin",
                        admin_id,
                        admin_name,
                        generate_timestamp(created_at, 4 + i * 2),
                        context,
                    )
                )

        # Final resolution message
        if conversation["state"] == "closed":
            conversation_parts.append(
                generate_message(
                    "admin_resolution",
                    "admin",
                    admin_id,
                    admin_name,
                    generate_timestamp(created_at, 24),
                    context,
                )
            )

        conversation["conversation_parts"] = {
            "type": "conversation_part.list",
            "conversation_parts": conversation_parts,
            "total_count": len(conversation_parts),
        }

    return conversation


def generate_test_dataset(
    num_conversations: int, include_messages: bool = True, base_time: datetime = None
) -> list[dict[str, Any]]:
    """Generate a complete test dataset"""
    if base_time is None:
        base_time = datetime.now()

    conversations = []
    for i in range(num_conversations):
        conversation = generate_conversation(base_time, i, include_messages)
        conversations.append(conversation)

        if (i + 1) % 100 == 0:
            print(f"Generated {i + 1}/{num_conversations} conversations...")

    return conversations


def main():
    parser = argparse.ArgumentParser(description="Generate test data for FastIntercom MCP")
    parser.add_argument(
        "--conversations",
        type=int,
        default=100,
        help="Number of conversations to generate (default: 100)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_data.json",
        help="Output file path (default: test_data.json)",
    )
    parser.add_argument(
        "--no-messages", action="store_true", help="Generate conversations without message details"
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")

    args = parser.parse_args()

    print(f"Generating {args.conversations} test conversations...")

    # Generate test data
    test_data = generate_test_dataset(
        num_conversations=args.conversations, include_messages=not args.no_messages
    )

    # Calculate statistics
    total_messages = sum(
        conv.get("conversation_parts", {}).get("total_count", 0) for conv in test_data
    )

    # Create output structure
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_conversations": len(test_data),
            "total_messages": total_messages,
            "includes_messages": not args.no_messages,
        },
        "conversations": test_data,
    }

    # Write to file
    with open(args.output, "w") as f:
        if args.pretty:
            json.dump(output, f, indent=2)
        else:
            json.dump(output, f)

    print("\nTest data generated successfully!")
    print(f"  Conversations: {len(test_data)}")
    print(f"  Messages: {total_messages}")
    print(f"  Output file: {args.output}")
    print(f"  File size: {os.path.getsize(args.output) / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    import os

    main()
