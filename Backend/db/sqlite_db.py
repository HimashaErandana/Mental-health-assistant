import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

log = logging.getLogger("chat_db")

DB_PATH = Path(__file__).parent / "chat_history.db"


def init_db():
    """Initialize the database and create tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # chat_messages table with message_type field (user/ai)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_type TEXT NOT NULL CHECK(message_type IN ('user', 'ai')),
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_session 
        ON chat_messages(session_id, created_at)
    """)

    conn.commit()
    conn.close()
    log.info(f"SQLite database initialized at {DB_PATH}")


def save_message(
    session_id: str, message_type: str, content: str, metadata: dict = None
) -> int:
    """Save a chat message and return its ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    import json

    metadata_json = json.dumps(metadata) if metadata else "{}"

    cursor.execute(
        "INSERT INTO chat_messages (session_id, message_type, content, metadata) VALUES (?, ?, ?, ?)",
        (session_id, message_type, content, metadata_json),
    )

    message_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log.info(f"Saved {message_type} message {message_id} for session {session_id}")
    return message_id


def get_chat_history(session_id: str, limit: int = 50) -> List[dict]:
    """Get chat history for a session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, message_type, content, created_at 
        FROM chat_messages 
        WHERE session_id = ?
        ORDER BY created_at DESC 
        LIMIT ?
    """,
        (session_id, limit),
    )

    rows = cursor.fetchall()
    conn.close()

    # Reverse to get chronological order
    messages = [
        {"id": row[0], "role": row[1], "content": row[2], "created_at": row[3]}
        for row in reversed(rows)
    ]

    return messages


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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    log.info(f"Cleared {deleted} messages for session {session_id}")
    return deleted


def get_total_messages() -> int:
    """Get total message count"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM chat_messages")
    count = cursor.fetchone()[0]
    conn.close()

    return count


# Initialize on import
if not DB_PATH.exists():
    init_db()
else:
    log.info(f"Database already exists at {DB_PATH}")
