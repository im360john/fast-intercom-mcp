"""Run database migrations."""
import asyncio
import asyncpg
import os
from pathlib import Path

async def run_migrations():
    """Execute SQL migration files."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        from fast_intercom_mcp.config import Config
        config = Config.load()
        database_url = config.database_url
    
    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Read and execute migration
        migration_file = Path("migrations/001_initial_schema.sql")
        if migration_file.exists():
            print(f"Running migration: {migration_file}")
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute the migration
            await conn.execute(sql)
            print("✓ Migration completed successfully")
        else:
            print(f"Migration file not found: {migration_file}")
            
    except Exception as e:
        print(f"✗ Migration failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migrations())