import sqlite3
from datetime import datetime, timezone
from .config import DATA_DIR

DB = DATA_DIR / "friday.sqlite3"

def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def initialize():
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")

def add_message(conversation_id: str, role: str, content: str):
    with connect() as db:
        db.execute("INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                   (conversation_id, role, content, datetime.now(timezone.utc).isoformat()))

def get_messages(conversation_id: str, limit: int = 30):
    with connect() as db:
        rows = db.execute("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?", (conversation_id, limit)).fetchall()
    return [dict(row) for row in reversed(rows)]

def list_conversations(limit: int = 30):
    with connect() as db:
        rows = db.execute("SELECT conversation_id, MAX(created_at) AS updated, COUNT(*) AS count FROM messages GROUP BY conversation_id ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
