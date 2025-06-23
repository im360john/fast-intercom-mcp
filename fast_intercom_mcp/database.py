"""SQLite database manager for FastIntercom MCP server."""

import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple, Literal
from pathlib import Path

from .models import Conversation, Message, SyncPeriod


class DatabaseManager:
    """Manages SQLite database operations for conversation storage and sync tracking."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses ~/.fastintercom/data.db
        """
        if db_path is None:
            # Default to user's home directory
            home_dir = Path.home()
            self.db_dir = home_dir / ".fastintercom"
            self.db_dir.mkdir(exist_ok=True)
            self.db_path = self.db_dir / "data.db"
        else:
            self.db_path = Path(db_path)
            self.db_dir = self.db_path.parent
            self.db_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Check if this is an existing database that needs migration
            self._run_migrations(conn)
            
            # Conversations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    customer_email TEXT,
                    tags TEXT, -- JSON array
                    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    author_type TEXT NOT NULL, -- 'user' | 'admin'
                    body TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    part_type TEXT, -- 'comment' | 'note' | 'message'
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                )
            """)
            
            # Sync periods tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_timestamp TIMESTAMP NOT NULL,
                    end_timestamp TIMESTAMP NOT NULL,
                    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    conversation_count INTEGER DEFAULT 0,
                    new_conversations INTEGER DEFAULT 0,
                    updated_conversations INTEGER DEFAULT 0
                )
            """)
            
            # Sync metadata table for tracking sync operations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_started_at TIMESTAMP NOT NULL,
                    sync_completed_at TIMESTAMP,
                    sync_status TEXT NOT NULL, -- 'in_progress', 'completed', 'failed'
                    coverage_start_date DATE,
                    coverage_end_date DATE,
                    total_conversations INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    sync_type TEXT, -- 'full', 'incremental'
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for quick lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_metadata_completed ON sync_metadata(sync_completed_at DESC)")
            
            # Request tracking for intelligent sync triggers
            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timeframe_start TIMESTAMP NOT NULL,
                    timeframe_end TIMESTAMP NOT NULL,
                    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_freshness_seconds INTEGER, -- How old the data was when served
                    sync_triggered BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations (created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_customer_email ON conversations (customer_email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_periods_timestamps ON sync_periods (start_timestamp, end_timestamp)")
            
            conn.commit()
    
    def _run_migrations(self, conn: sqlite3.Connection):
        """Run database migrations for existing databases."""
        # Check if the old sync_metadata table exists (key-value style)
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sync_metadata'
        """)
        
        old_table_exists = cursor.fetchone() is not None
        
        if old_table_exists:
            # Check if it's the old format by looking at the schema
            cursor = conn.execute("PRAGMA table_info(sync_metadata)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # If it has 'key' column, it's the old format
            if 'key' in columns and 'id' not in columns:
                # Rename old table and migrate data
                conn.execute("ALTER TABLE sync_metadata RENAME TO sync_metadata_old")
                
                # Create new sync_metadata table
                conn.execute("""
                    CREATE TABLE sync_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_started_at TIMESTAMP NOT NULL,
                        sync_completed_at TIMESTAMP,
                        sync_status TEXT NOT NULL, -- 'in_progress', 'completed', 'failed'
                        coverage_start_date DATE,
                        coverage_end_date DATE,
                        total_conversations INTEGER DEFAULT 0,
                        total_messages INTEGER DEFAULT 0,
                        sync_type TEXT, -- 'full', 'incremental'
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create initial migration record if conversations exist
                cursor = conn.execute("SELECT COUNT(*) FROM conversations")
                conversation_count = cursor.fetchone()[0]
                
                if conversation_count > 0:
                    conn.execute("""
                        INSERT INTO sync_metadata (
                            sync_started_at,
                            sync_completed_at, 
                            sync_status,
                            coverage_start_date,
                            coverage_end_date,
                            total_conversations,
                            sync_type
                        )
                        VALUES (?, ?, 'completed', ?, ?, ?, 'migration')
                    """, [
                        (datetime.now() - timedelta(hours=1)).isoformat(),
                        datetime.now().isoformat(),
                        (datetime.now() - timedelta(days=7)).date().isoformat(),
                        datetime.now().date().isoformat(),
                        conversation_count
                    ])
                
                # Drop old table
                conn.execute("DROP TABLE sync_metadata_old")
                
                conn.commit()
    
    def store_conversations(self, conversations: List[Conversation]) -> int:
        """Store or update conversations in database.
        
        Args:
            conversations: List of conversations to store
            
        Returns:
            Number of conversations actually stored/updated
        """
        if not conversations:
            return 0
            
        stored_count = 0
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            for conv in conversations:
                # Check if conversation exists
                cursor = conn.execute(
                    "SELECT id, updated_at, message_count FROM conversations WHERE id = ?",
                    (conv.id,)
                )
                existing = cursor.fetchone()
                
                # Convert tags to JSON
                tags_json = json.dumps(conv.tags) if conv.tags else "[]"
                
                if existing:
                    # Update if conversation has new messages or updates
                    existing_id, existing_updated_at, existing_msg_count = existing
                    existing_updated = datetime.fromisoformat(existing_updated_at.replace('Z', '+00:00'))
                    
                    if (conv.updated_at > existing_updated or 
                        len(conv.messages) != existing_msg_count):
                        
                        # Update conversation
                        conn.execute("""
                            UPDATE conversations 
                            SET updated_at = ?, customer_email = ?, tags = ?, 
                                last_synced = CURRENT_TIMESTAMP, message_count = ?
                            WHERE id = ?
                        """, (
                            conv.updated_at.isoformat(),
                            conv.customer_email,
                            tags_json,
                            len(conv.messages),
                            conv.id
                        ))
                        
                        # Delete old messages and insert new ones
                        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv.id,))
                        self._store_messages(conn, conv.messages, conv.id)
                        stored_count += 1
                else:
                    # Insert new conversation
                    conn.execute("""
                        INSERT INTO conversations 
                        (id, created_at, updated_at, customer_email, tags, message_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        conv.id,
                        conv.created_at.isoformat(),
                        conv.updated_at.isoformat(),
                        conv.customer_email,
                        tags_json,
                        len(conv.messages)
                    ))
                    
                    # Insert messages
                    self._store_messages(conn, conv.messages, conv.id)
                    stored_count += 1
            
            conn.commit()
        
        return stored_count
    
    def _store_messages(self, conn: sqlite3.Connection, messages: List[Message], conversation_id: str):
        """Store messages for a conversation."""
        for msg in messages:
            conn.execute("""
                INSERT OR REPLACE INTO messages 
                (id, conversation_id, author_type, body, created_at, part_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                msg.id,
                conversation_id,
                msg.author_type,
                msg.body,
                msg.created_at.isoformat(),
                getattr(msg, 'part_type', None)
            ))
    
    def search_conversations(
        self, 
        query: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        customer_email: Optional[str] = None,
        limit: int = 100
    ) -> List[Conversation]:
        """Search conversations with filters.
        
        Args:
            query: Text search in message bodies
            start_date: Filter conversations created after this date
            end_date: Filter conversations created before this date
            customer_email: Filter by customer email
            limit: Maximum number of conversations to return
            
        Returns:
            List of matching conversations with messages
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query conditions
            conditions = []
            params = []
            
            if start_date:
                conditions.append("c.created_at >= ?")
                params.append(start_date.isoformat())
            
            if end_date:
                conditions.append("c.created_at <= ?")
                params.append(end_date.isoformat())
            
            if customer_email:
                conditions.append("c.customer_email = ?")
                params.append(customer_email)
            
            if query:
                # Search in message bodies
                conditions.append("""
                    c.id IN (
                        SELECT DISTINCT conversation_id 
                        FROM messages 
                        WHERE body LIKE ?
                    )
                """)
                params.append(f"%{query}%")
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Get conversations
            conv_query = f"""
                SELECT c.* FROM conversations c 
                {where_clause}
                ORDER BY c.created_at DESC 
                LIMIT ?
            """
            params.append(limit)
            
            conversations = []
            for row in conn.execute(conv_query, params):
                # Get messages for this conversation
                messages = []
                msg_cursor = conn.execute("""
                    SELECT * FROM messages 
                    WHERE conversation_id = ? 
                    ORDER BY created_at ASC
                """, (row['id'],))
                
                for msg_row in msg_cursor:
                    messages.append(Message(
                        id=msg_row['id'],
                        author_type=msg_row['author_type'],
                        body=msg_row['body'],
                        created_at=datetime.fromisoformat(msg_row['created_at']),
                        part_type=msg_row['part_type']
                    ))
                
                # Parse tags from JSON
                tags = json.loads(row['tags']) if row['tags'] else []
                
                conversations.append(Conversation(
                    id=row['id'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    messages=messages,
                    customer_email=row['customer_email'],
                    tags=tags
                ))
            
            return conversations
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get conversation counts
            cursor = conn.execute("SELECT COUNT(*) as total FROM conversations")
            total_conversations = cursor.fetchone()['total']
            
            cursor = conn.execute("SELECT COUNT(*) as total FROM messages")
            total_messages = cursor.fetchone()['total']
            
            # Get last sync time
            cursor = conn.execute("""
                SELECT MAX(last_synced) as last_sync 
                FROM conversations
            """)
            last_sync_row = cursor.fetchone()
            last_sync = last_sync_row['last_sync'] if last_sync_row['last_sync'] else None
            
            # Get recent sync activity
            cursor = conn.execute("""
                SELECT * FROM sync_periods 
                ORDER BY last_synced DESC 
                LIMIT 5
            """)
            recent_syncs = [dict(row) for row in cursor.fetchall()]
            
            # Get database file size
            db_size_bytes = os.path.getsize(self.db_path)
            db_size_mb = db_size_bytes / (1024 * 1024)
            
            return {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'last_sync': last_sync,
                'recent_syncs': recent_syncs,
                'database_size_mb': round(db_size_mb, 2),
                'database_path': str(self.db_path)
            }
    
    def record_sync_period(self, start_time: datetime, end_time: datetime, 
                          conversation_count: int, new_count: int = 0, 
                          updated_count: int = 0) -> int:
        """Record a sync period for tracking.
        
        Args:
            start_time: Start of the sync period
            end_time: End of the sync period  
            conversation_count: Total conversations in this period
            new_count: Number of new conversations added
            updated_count: Number of existing conversations updated
            
        Returns:
            ID of the created sync period record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sync_periods 
                (start_timestamp, end_timestamp, conversation_count, 
                 new_conversations, updated_conversations)
                VALUES (?, ?, ?, ?, ?)
            """, (
                start_time.isoformat(),
                end_time.isoformat(),
                conversation_count,
                new_count,
                updated_count
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_periods_needing_sync(self, max_age_minutes: int = 5) -> List[Tuple[datetime, datetime]]:
        """Get time periods that need syncing based on last sync time.
        
        Args:
            max_age_minutes: Maximum age in minutes before considering data stale
            
        Returns:
            List of (start_time, end_time) tuples that need syncing
        """
        cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None)  # Remove timezone for SQLite
        cutoff_time = cutoff_time.replace(minute=cutoff_time.minute - max_age_minutes)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Find periods that haven't been synced recently
            cursor = conn.execute("""
                SELECT start_timestamp, end_timestamp 
                FROM sync_periods 
                WHERE last_synced < ?
                ORDER BY start_timestamp DESC
                LIMIT 10
            """, (cutoff_time.isoformat(),))
            
            periods = []
            for row in cursor.fetchall():
                start = datetime.fromisoformat(row['start_timestamp'])
                end = datetime.fromisoformat(row['end_timestamp'])
                periods.append((start, end))
            
            return periods
    
    def record_request_pattern(self, start_time: datetime, end_time: datetime, 
                              data_freshness_seconds: int, sync_triggered: bool = False) -> int:
        """Record a request pattern for intelligent sync analysis.
        
        Args:
            start_time: Start of the requested timeframe
            end_time: End of the requested timeframe
            data_freshness_seconds: How old the data was when served
            sync_triggered: Whether this request triggered a background sync
            
        Returns:
            ID of the created request pattern record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO request_patterns 
                (timeframe_start, timeframe_end, data_freshness_seconds, sync_triggered)
                VALUES (?, ?, ?, ?)
            """, (
                start_time.isoformat(),
                end_time.isoformat(),
                data_freshness_seconds,
                sync_triggered
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_stale_timeframes(self, staleness_threshold_minutes: int = 5) -> List[Tuple[datetime, datetime]]:
        """Get timeframes that have been requested recently but may have stale data.
        
        Args:
            staleness_threshold_minutes: Consider data stale if older than this
            
        Returns:
            List of (start_time, end_time) tuples that need refreshing
        """
        cutoff_time = datetime.now()
        recent_requests_since = cutoff_time - timedelta(hours=1)  # Look at last hour of requests
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Find recent requests where data was stale or sync wasn't triggered
            cursor = conn.execute("""
                SELECT DISTINCT timeframe_start, timeframe_end, data_freshness_seconds
                FROM request_patterns 
                WHERE request_timestamp >= ? 
                  AND (data_freshness_seconds > ? OR sync_triggered = FALSE)
                ORDER BY request_timestamp DESC
                LIMIT 10
            """, (
                recent_requests_since.isoformat(),
                staleness_threshold_minutes * 60
            ))
            
            timeframes = []
            for row in cursor.fetchall():
                start = datetime.fromisoformat(row['timeframe_start'])
                end = datetime.fromisoformat(row['timeframe_end'])
                timeframes.append((start, end))
            
            return timeframes
    
    def get_data_freshness_for_timeframe(self, start_time: datetime, end_time: datetime) -> int:
        """Calculate how old the data is for a given timeframe.
        
        Args:
            start_time: Start of timeframe
            end_time: End of timeframe
            
        Returns:
            Age of data in seconds (0 if no data exists)
        """
        with sqlite3.connect(self.db_path) as conn:
            # Find the most recent conversation in this timeframe
            cursor = conn.execute("""
                SELECT MAX(last_synced) as latest_sync
                FROM conversations 
                WHERE created_at >= ? AND created_at <= ?
            """, (start_time.isoformat(), end_time.isoformat()))
            
            result = cursor.fetchone()
            if result and result[0]:
                latest_sync = datetime.fromisoformat(result[0])
                freshness = (datetime.now() - latest_sync).total_seconds()
                return int(freshness)
            
            return 0  # No data means "fresh" (will trigger initial sync)

    def check_sync_state(
        self, 
        start_date: Optional[datetime], 
        end_date: Optional[datetime],
        freshness_threshold_minutes: int = 5
    ) -> Dict[str, Any]:
        """
        Check sync state relative to requested timeframe.
        
        Returns sync state ('stale', 'partial', 'fresh') with metadata.
        
        Args:
            start_date: Start of requested timeframe  
            end_date: End of requested timeframe
            freshness_threshold_minutes: Minutes before data considered stale
            
        Returns:
            Dict with sync_state, last_sync, message, and should_sync fields
        """
        sync_status = self.get_sync_status()
        last_sync_str = sync_status.get("last_sync")
        
        if not last_sync_str:
            return {
                "sync_state": "stale",
                "last_sync": None,
                "message": "No sync data available - database needs initial sync",
                "should_sync": True,
                "data_complete": False
            }
        
        try:
            # Parse last sync time (handle various ISO formats)
            last_sync = datetime.fromisoformat(last_sync_str.replace("Z", "+00:00"))
            if last_sync.tzinfo:
                last_sync = last_sync.replace(tzinfo=None)  # Make naive for comparison
        except (ValueError, AttributeError):
            return {
                "sync_state": "stale", 
                "last_sync": None,
                "message": f"Invalid sync timestamp: {last_sync_str}",
                "should_sync": True,
                "data_complete": False
            }
        
        # If no timeframe specified, check general freshness
        if not start_date or not end_date:
            recent_threshold = datetime.now() - timedelta(minutes=freshness_threshold_minutes)
            if last_sync >= recent_threshold:
                return {
                    "sync_state": "fresh", 
                    "last_sync": last_sync,
                    "data_complete": True
                }
            else:
                return {
                    "sync_state": "partial",
                    "last_sync": last_sync,
                    "message": f"Data may be stale - last sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}",
                    "data_complete": False
                }
        
        # State 1: Stale - last sync before requested period
        if last_sync < start_date:
            return {
                "sync_state": "stale",
                "last_sync": last_sync,
                "message": f"Data is stale - last sync {last_sync.strftime('%Y-%m-%d %H:%M:%S')} is before requested period {start_date.strftime('%Y-%m-%d %H:%M:%S')}",
                "should_sync": True,
                "data_complete": False
            }
        
        # State 2: Partial - last sync within requested period  
        if start_date <= last_sync < end_date:
            return {
                "sync_state": "partial",
                "last_sync": last_sync,
                "message": f"Analysis includes conversations up to {last_sync.strftime('%Y-%m-%d %H:%M:%S')} - may be missing recent conversations",
                "should_sync": False,
                "data_complete": False
            }
        
        # State 3: Fresh - last sync recent relative to end time
        freshness_threshold_dt = end_date - timedelta(minutes=freshness_threshold_minutes)
        if last_sync >= freshness_threshold_dt:
            return {
                "sync_state": "fresh",
                "last_sync": last_sync,
                "should_sync": False,
                "data_complete": True
            }
        else:
            # Slightly stale but within acceptable range
            return {
                "sync_state": "partial", 
                "last_sync": last_sync,
                "message": f"Analysis includes conversations up to {last_sync.strftime('%Y-%m-%d %H:%M:%S')} - may be missing very recent conversations",
                "should_sync": False,
                "data_complete": False
            }

    def close(self):
        """Close database connections (for cleanup)."""
        # SQLite connections are closed automatically when using context managers
        pass