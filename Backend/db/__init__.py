import os
import logging
from pathlib import Path

log = logging.getLogger("db")

# PostgreSQL Configuration
# Update these with your PostgreSQL credentials
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mental_health")

# For local dev, fall back to SQLite
USE_SQLITE = os.getenv("USE_SQLITE", "true").lower() == "true"

if USE_SQLITE:
    # Use SQLite for local development
    from .sqlite_db import (
        save_message,
        get_chat_history,
        get_recent_context,
        clear_session,
        get_total_messages,
        init_db as init_sqlite,
    )

    def init_db():
        """Initialize database"""
        return init_sqlite()

    log.info("Using SQLite for chat history (USE_SQLITE=true)")

else:
    # Use PostgreSQL
    import sqlite3
    import asyncpg
    import uuid
    from datetime import datetime
    from typing import List, Optional

    DB_PATH = Path(__file__).parent / "chat_history.db"

    # Synchronous PostgreSQL connection pool (for sync operations)
    _pool = None

    async def get_pool():
        """Get async PostgreSQL connection pool"""
        global _pool
        if _pool is None:
            _pool = await asyncpg.create_pool(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                min_size=2,
                max_size=10,
            )
        return _pool

    async def init_db():
        """Initialize PostgreSQL database and tables"""
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    message_type VARCHAR(20) NOT NULL CHECK(message_type IN ('user', 'ai')),
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_session 
                ON chat_messages(session_id, created_at)
            """)

            log.info("PostgreSQL database initialized")

    def save_message(
        session_id: str, message_type: str, content: str, metadata: dict = None
    ) -> int:
        """Save a chat message (sync wrapper for async)"""
        import asyncio

        async def _save():
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    INSERT INTO chat_messages (session_id, message_type, content, metadata)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """,
                    session_id,
                    message_type,
                    content,
                    metadata or {},
                )
                return result

        return asyncio.run(_save())

    def get_chat_history(session_id: str, limit: int = 50) -> List[dict]:
        """Get chat history for a session"""
        import asyncio

        async def _get():
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, message_type, content, created_at 
                    FROM chat_messages 
                    WHERE session_id = $1
                    ORDER BY created_at DESC 
                    LIMIT $2
                """,
                    session_id,
                    limit,
                )

                return [
                    {
                        "id": row["id"],
                        "role": row["message_type"],
                        "content": row["content"],
                        "created_at": row["created_at"],
                    }
                    for row in reversed(rows)
                ]

        return asyncio.run(_get())

    def get_recent_context(session_id: str, limit: int = 10) -> str:
        """Get recent conversation context for follow-up"""
        messages = get_chat_history(session_id, limit)

        if not messages:
            return ""

        context_lines = []
        for msg in messages:
            role_label = "User" if msg["role"] == "user" else "AI"
            content = (
                msg["content"][:200] + "..."
                if len(msg["content"]) > 200
                else msg["content"]
            )
            context_lines.append(f"{role_label}: {content}")

        return "\n".join(context_lines)

    def clear_session(session_id: str) -> int:
        """Clear all messages for a session"""
        import asyncio

        async def _clear():
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    DELETE FROM chat_messages 
                    WHERE session_id = $1
                    RETURNING COUNT(*)
                """,
                    session_id,
                )
                return result

        return asyncio.run(_clear())

    def get_total_messages() -> int:
        """Get total message count"""
        import asyncio

        async def _count():
            pool = await get_pool()
            async with pool.acquire() as conn:
                return await conn.fetchval("SELECT COUNT(*) FROM chat_messages")

        return asyncio.run(_count())

    log.info(f"PostgreSQL configured: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")


# Initialize database on import
try:
    init_db()
except Exception as e:
    log.warning(f"Could not initialize database: {e}")
    log.info("Set USE_SQLITE=false in environment to use PostgreSQL")
