# Render Deployment Guide for Fast-Intercom-MCP

This guide covers deploying the Fast-Intercom-MCP service to Render with automatic daily syncing.

## Prerequisites

1. A Render account (https://render.com)
2. Your PostgreSQL database already deployed on Render (which you have)
3. Your Intercom Access Token

## Deployment Steps

### 1. Create a New Web Service

1. Log into your Render dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository containing this code
4. Configure the service:
   - **Name**: `fast-intercom-mcp`
   - **Environment**: `Python 3`
   - **Region**: Same as your PostgreSQL (Oregon)
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `fast-intercom-mcp` (if in a subdirectory)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn fast_intercom_mcp.server:app --host 0.0.0.0 --port $PORT`

### 2. Configure Environment Variables

Add these environment variables in the Render dashboard:

```bash
# Database (use your existing Render PostgreSQL internal URL)
DATABASE_URL=postgresql://user:password@dpg-YOUR-DATABASE-ID-a:5432/your_database_name

# Intercom
INTERCOM_ACCESS_TOKEN=your_intercom_access_token_here

# Optional configuration
FASTINTERCOM_LOG_LEVEL=INFO
MAX_CONTEXT_TOKENS=100000
```

**Important**: Use the internal database URL (ending with `-a:5432`) for services within Render.

### 3. Create a Background Worker for Daily Sync

Since Render doesn't have built-in cron jobs, we'll create a background worker:

1. In Render, create a new "Background Worker"
2. Use the same repository
3. Configure:
   - **Name**: `fast-intercom-sync-worker`
   - **Environment**: `Python 3`
   - **Start Command**: `python auto_sync_scheduler.py`
   - **Environment Variables**: Same as above

### 4. Initial Database Setup

After deployment, run these one-time setup commands using Render's Shell:

```bash
# Run database migrations
python -c "
import asyncio
from fast_intercom_mcp.db.migrations import run_migrations
asyncio.run(run_migrations())
"

# Run initial sync with contact details
python sync_with_contacts.py
```

### 5. Alternative: Using Render Cron Jobs (Paid Feature)

If you have a paid Render plan, you can use Cron Jobs instead:

1. Create a new "Cron Job" in Render
2. Configure:
   - **Name**: `fast-intercom-daily-sync`
   - **Command**: `python run_daily_sync.py`
   - **Schedule**: `0 5 * * *` (5 AM UTC = 9 PM PST)
   - **Environment Variables**: Same as above

Create the sync script:

```python
# run_daily_sync.py
import asyncio
from datetime import datetime, timedelta
from fast_intercom_mcp.db.connection import db_pool
from fast_intercom_mcp.tools.sync import sync_conversations, sync_articles

async def run_sync():
    print(f"Starting daily sync at {datetime.now()}")
    await db_pool.initialize()
    
    try:
        # Sync last 30 days of conversations with contacts
        print("Syncing conversations...")
        exec(open('sync_with_contacts.py').read())
        
        # Sync all articles
        print("Syncing articles...")
        await sync_articles(force=True)
        
        print("Daily sync completed")
    finally:
        await db_pool.close()

if __name__ == "__main__":
    asyncio.run(run_sync())
```

## Monitoring and Logs

### View Logs
- Web Service logs: Shows API requests and responses
- Background Worker logs: Shows sync progress and any errors
- Check logs daily to ensure sync is running at 9 PM PST

### Health Checks
Add a health check endpoint by creating:

```python
# fast_intercom_mcp/health.py
from fastmcp import FastMCP
from .server import mcp

@mcp.route("/health")
async def health_check():
    return {"status": "healthy", "service": "fast-intercom-mcp"}
```

Configure in Render:
- **Health Check Path**: `/health`

## Troubleshooting

### Sync Not Running
1. Check Background Worker logs for errors
2. Verify environment variables are set correctly
3. Ensure timezone is correct (PST)

### Database Connection Issues
1. Verify you're using the internal database URL
2. Check PostgreSQL is in the same region
3. Ensure connection pool settings are appropriate

### Memory Issues
If you encounter memory issues during sync:
1. Reduce batch size in sync scripts
2. Upgrade to a larger Render instance
3. Run sync during low-traffic hours

## Production Recommendations

1. **Enable Auto-Deploy**: Connect GitHub for automatic deployments on push
2. **Set Resource Limits**: Configure appropriate CPU and memory limits
3. **Add Monitoring**: Use Render's metrics or integrate with external monitoring
4. **Backup Strategy**: Enable PostgreSQL backups in Render
5. **Rate Limiting**: The code already implements rate limiting (900 req/min)

## Security Notes

- Never commit environment variables to Git
- Use Render's secret management for sensitive data
- Regularly rotate your Intercom Access Token
- Enable 2FA on your Render account

## Scaling

As your data grows:
1. Increase PostgreSQL plan for more storage/performance
2. Upgrade web service for more concurrent connections
3. Consider implementing caching for frequently accessed data
4. Monitor query performance and add indexes as needed

## Support

- Render Status: https://status.render.com
- Render Docs: https://render.com/docs
- Intercom API Docs: https://developers.intercom.com