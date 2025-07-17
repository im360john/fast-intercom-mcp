"""Sync conversations with full contact details."""
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from fast_intercom_mcp.db.connection import db_pool
from fast_intercom_mcp.api.client import IntercomAPIClient
from fast_intercom_mcp.config import Config

async def safe_str(value):
    """Safely convert value to string."""
    if value is None:
        return None
    return str(value)

async def safe_timestamp(value):
    """Safely convert timestamp to datetime."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value))
    except (ValueError, TypeError):
        return None

async def get_contact_details(client: IntercomAPIClient, contact_id: str) -> Optional[Dict]:
    """Fetch full contact details."""
    try:
        response = await client.make_request("GET", f"/contacts/{contact_id}")
        return response
    except Exception as e:
        # Don't print for each contact to avoid spam
        return None

async def upsert_conversation_with_contacts(conn, conv: Dict, client: IntercomAPIClient):
    """Upsert a conversation with full contact details."""
    # Extract contacts list
    contacts_data = conv.get('contacts', {}).get('contacts', [])
    
    # Initialize customer data
    customer_email = None
    customer_name = None
    customer_id = None
    
    # Fetch first contact's details if available
    if contacts_data:
        first_contact_ref = contacts_data[0]
        contact_id = first_contact_ref.get('id')
        
        if contact_id:
            # Fetch full contact details
            contact = await get_contact_details(client, contact_id)
            if contact:
                customer_email = contact.get('email')
                customer_name = contact.get('name')
                customer_id = contact_id
    
    # If no contact data, try source author as fallback
    if not customer_email:
        source = conv.get('source', {})
        author = source.get('author', {}) if source else {}
        if author:
            customer_email = author.get('email') if author.get('email') else None
            customer_name = author.get('name') if author.get('name') else None
    
    # Handle tags
    tags_obj = conv.get('tags', {})
    if isinstance(tags_obj, dict):
        tags_list = tags_obj.get('tags', [])
    else:
        tags_list = []
    tag_names = [tag['name'] for tag in tags_list if isinstance(tag, dict) and 'name' in tag]
    
    # Source info
    source = conv.get('source', {})
    author = source.get('author', {}) if source else {}
    
    # Statistics
    stats = conv.get('statistics', {})
    
    # Prepare values
    values = [
        await safe_str(conv['id']),  # $1
        await safe_timestamp(conv['created_at']),  # $2
        await safe_timestamp(conv['updated_at']),  # $3
        customer_email,  # $4
        customer_name,  # $5
        await safe_str(customer_id),  # $6
        await safe_str(conv.get('admin_assignee_id')),  # $7
        None,  # $8 assignee name
        conv.get('state', 'unknown'),  # $9
        conv.get('read', False),  # $10
        conv.get('priority'),  # $11
        await safe_timestamp(conv.get('snoozed_until')),  # $12
        tag_names,  # $13
        conv.get('conversation_rating', {}).get('rating') if conv.get('conversation_rating') else None,  # $14
        conv.get('conversation_rating', {}).get('remark') if conv.get('conversation_rating') else None,  # $15
        source.get('type'),  # $16
        await safe_str(source.get('id')),  # $17
        source.get('delivered_as'),  # $18
        source.get('subject'),  # $19
        source.get('body'),  # $20
        author.get('type') if author else None,  # $21
        await safe_str(author.get('id')),  # $22
        author.get('name') if author else None,  # $23
        author.get('email') if author else None,  # $24
        await safe_timestamp(stats.get('first_contact_reply_at')),  # $25
        await safe_timestamp(stats.get('first_admin_reply_at')),  # $26
        await safe_timestamp(stats.get('last_contact_reply_at')),  # $27
        await safe_timestamp(stats.get('last_admin_reply_at'))  # $28
    ]
    
    await conn.execute("""
        INSERT INTO conversations (
            id, created_at, updated_at, customer_email, customer_name, customer_id,
            assignee_id, assignee_name, state, read, priority, snoozed_until,
            tags, conversation_rating_value, conversation_rating_remark,
            source_type, source_id, source_delivered_as, source_subject, source_body,
            source_author_type, source_author_id, source_author_name, source_author_email,
            statistics_first_contact_reply_at, statistics_first_admin_reply_at,
            statistics_last_contact_reply_at, statistics_last_admin_reply_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                  $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28)
        ON CONFLICT (id) DO UPDATE SET
            updated_at = EXCLUDED.updated_at,
            customer_email = EXCLUDED.customer_email,
            customer_name = EXCLUDED.customer_name,
            state = EXCLUDED.state,
            read = EXCLUDED.read,
            assignee_id = EXCLUDED.assignee_id,
            priority = EXCLUDED.priority,
            snoozed_until = EXCLUDED.snoozed_until,
            tags = EXCLUDED.tags
    """, *values)
    
    return customer_email is not None

async def sync_conversations_with_contacts():
    """Sync conversations with full contact details."""
    config = Config.load()
    client = IntercomAPIClient(config.intercom_token)
    
    await db_pool.initialize()
    
    try:
        print("🔧 Syncing Conversations with Contact Details")
        print("=" * 50)
        
        # Update sync status
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sync_metadata SET sync_status = 'in_progress', last_sync_at = $1, error_message = NULL "
                "WHERE entity_type = 'conversations'",
                datetime.now()
            )
        
        # Get conversations from the last 30 days
        updated_since = datetime.now() - timedelta(days=30)
        total_synced = 0
        total_with_email = 0
        page = 1
        batch_size = 20  # Smaller batches since we're making extra API calls
        
        while True:
            try:
                search_query = {
                    "query": {
                        "field": "updated_at",
                        "operator": ">",
                        "value": int(updated_since.timestamp())
                    },
                    "pagination": {
                        "per_page": batch_size,
                        "page": page
                    }
                }
                
                print(f"\nFetching page {page} ({batch_size} per page)...")
                response = await client.search_conversations(search_query)
                conversations = response.get('conversations', response.get('data', []))
                
                if not conversations:
                    print("No more conversations to sync")
                    break
                
                # Check if we're getting duplicates (Intercom API issue)
                first_conv_id = conversations[0].get('id') if conversations else None
                if page > 1 and first_conv_id:
                    # Check if we've seen this conversation before
                    async with db_pool.acquire() as conn:
                        exists = await conn.fetchval(
                            "SELECT EXISTS(SELECT 1 FROM conversations WHERE id = $1)",
                            str(first_conv_id)
                        )
                        if exists and page > 10:  # After 10 pages, if still duplicates, stop
                            print("Detected duplicate conversations, stopping pagination")
                            break
                
                print(f"Processing {len(conversations)} conversations...")
                
                # Process each conversation
                for i, conv in enumerate(conversations):
                    try:
                        async with db_pool.acquire() as conn:
                            has_email = await upsert_conversation_with_contacts(conn, conv, client)
                            total_synced += 1
                            if has_email:
                                total_with_email += 1
                        
                        # Progress indicator
                        if (i + 1) % 5 == 0:
                            print(f"  ✓ Processed {i + 1}/{len(conversations)} in this batch...")
                            
                    except Exception as e:
                        print(f"  ⚠️  Error syncing conversation {conv.get('id')}: {e}")
                        continue
                
                print(f"✅ Page {page} complete. Total: {total_synced}, With email: {total_with_email}")
                page += 1
                
                # Rate limiting pause
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error on page {page}: {e}")
                break
        
        # Update final sync status
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sync_metadata SET sync_status = 'completed', items_synced = $1 "
                "WHERE entity_type = 'conversations'",
                total_synced
            )
            
            # Get final stats
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN customer_email IS NOT NULL THEN 1 END) as with_email,
                    COUNT(CASE WHEN customer_name IS NOT NULL THEN 1 END) as with_name
                FROM conversations
            """)
            
        print(f"\n✅ Sync completed!")
        print(f"   Total conversations synced: {total_synced}")
        print(f"   Conversations with email: {total_with_email}")
        print(f"   Database totals:")
        print(f"     - Total conversations: {stats['total']}")
        print(f"     - With email: {stats['with_email']}")
        print(f"     - With name: {stats['with_name']}")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE sync_metadata SET sync_status = 'failed', error_message = $1 "
                "WHERE entity_type = 'conversations'",
                str(e)
            )
    finally:
        await client.close()
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(sync_conversations_with_contacts())