-- Initial schema for Fast Intercom MCP with PostgreSQL

-- Conversations table (migrated from SQLite)
CREATE TABLE conversations (
    id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    customer_email VARCHAR,
    customer_name VARCHAR,
    customer_id VARCHAR,
    assignee_id VARCHAR,
    assignee_name VARCHAR,
    state VARCHAR NOT NULL,
    read BOOLEAN DEFAULT FALSE,
    priority VARCHAR,
    snoozed_until TIMESTAMP,
    tags TEXT[],
    conversation_rating_value INTEGER,
    conversation_rating_remark TEXT,
    source_type VARCHAR,
    source_id VARCHAR,
    source_delivered_as VARCHAR,
    source_subject TEXT,
    source_body TEXT,
    source_author_type VARCHAR,
    source_author_id VARCHAR,
    source_author_name VARCHAR,
    source_author_email VARCHAR,
    statistics_first_contact_reply_at TIMESTAMP,
    statistics_first_admin_reply_at TIMESTAMP,
    statistics_last_contact_reply_at TIMESTAMP,
    statistics_last_admin_reply_at TIMESTAMP,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(customer_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(customer_email, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(source_subject, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(source_body, '')), 'C')
    ) STORED
);

CREATE INDEX conversations_search_idx ON conversations USING GIN (search_vector);
CREATE INDEX conversations_updated_at_idx ON conversations(updated_at DESC);
CREATE INDEX conversations_customer_email_idx ON conversations(customer_email);

-- Articles table
CREATE TABLE articles (
    id VARCHAR PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    body TEXT,
    author_id VARCHAR,
    state VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    parent_id VARCHAR,
    parent_type VARCHAR,
    statistics_views INTEGER DEFAULT 0,
    statistics_reactions INTEGER DEFAULT 0,
    statistics_happy_reactions_percentage FLOAT,
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(body, '')), 'C')
    ) STORED
);

CREATE INDEX articles_search_idx ON articles USING GIN (search_vector);
CREATE INDEX articles_updated_at_idx ON articles(updated_at DESC);
CREATE INDEX articles_state_idx ON articles(state);

-- Sync metadata table
CREATE TABLE sync_metadata (
    entity_type VARCHAR PRIMARY KEY,
    last_sync_at TIMESTAMP,
    sync_status VARCHAR,
    items_synced INTEGER,
    error_message TEXT
);