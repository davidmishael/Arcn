import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path


# -------------------------
# Config
# -------------------------
DB_DIR  = Path(__file__).parent
DB_PATH = DB_DIR / "arcn_memory.db"


# -------------------------
# Connection
# -------------------------
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # safer concurrent writes
    return conn


# -------------------------
# Schema creation
# -------------------------
def init_db():

    conn = get_connection()

    conn.executescript("""

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TEXT NOT NULL,
            ended_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   INTEGER NOT NULL,
            timestamp    TEXT NOT NULL,
            raw_text     TEXT,
            intent       TEXT,
            confidence   REAL,
            entities     TEXT,
            response     TEXT,
            context_used INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS preferences (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            count      INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL
        );
                       
        CREATE INDEX IF NOT EXISTS idx_conversations_id 
        ON conversations(id DESC);

        CREATE TABLE IF NOT EXISTS state (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
                       
        CREATE TABLE IF NOT EXISTS notes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT NOT NULL,
            content        TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL,
            exported_to_mac INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_notes_created
        ON notes(created_at DESC);

    """)

    conn.commit()
    conn.close()


# -------------------------
# Session management
# -------------------------
def start_session() -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO sessions (started_at) VALUES (?)",
        (datetime.now().isoformat(),)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_session(session_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET ended_at = ? WHERE id = ?",
        (datetime.now().isoformat(), session_id)
    )
    conn.commit()
    conn.close()


# -------------------------
# Write a conversation turn
# -------------------------
def save_turn(session_id: int, packet: dict, response: str):
    conn = get_connection()

    # strip runtime-only keys before saving — these cause recursive bloat
    entities_to_save = {
        k: v for k, v in packet.get("entities", {}).items()
        if k not in ("memory_context", "semantic_context")
    }

    cursor = conn.execute(
        """
        INSERT INTO conversations
            (session_id, timestamp, raw_text, intent, confidence,
             entities, response, context_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            datetime.now().isoformat(),
            packet.get("entities", {}).get("raw_text", ""),
            packet.get("intent", ""),
            packet.get("confidence", 0.0),
            json.dumps(entities_to_save),
            response,
            int(packet.get("context_used", False))
        )
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id

# -------------------------
# Notes — SQLite is the
# source of truth. Apple Notes
# export is opt-in, one-way.
# -------------------------
def create_note(title: str, content: str) -> int:
    conn = get_connection()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """
        INSERT INTO notes (title, content, created_at, updated_at, exported_to_mac)
        VALUES (?, ?, ?, ?, 0)
        """,
        (title, content, now, now)
    )
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_note(note_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_notes(n: int = 10) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notes ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_notes_by_title(query: str) -> list:
    """Plain substring match — semantic search is a future item, not this pass."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notes WHERE title LIKE ? ORDER BY id DESC",
        (f"%{query}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_note_exported(note_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE notes SET exported_to_mac = 1, updated_at = ? WHERE id = ?",
        (datetime.now().isoformat(), note_id)
    )
    conn.commit()
    conn.close()


def delete_note(note_id: int) -> bool:
    conn = get_connection()
    cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

# -------------------------
# Preference tracking
# -------------------------
def update_preference(key: str, value: str):
    """
    Upsert a preference. If the key already exists,
    increment count and update value + timestamp.
    Only meaningful preferences should be passed here —
    filtering happens in memory_manager.py.
    """
    conn = get_connection()
    existing = conn.execute(
        "SELECT count FROM preferences WHERE key = ?", (key,)
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE preferences
            SET value = ?, count = count + 1, updated_at = ?
            WHERE key = ?
            """,
            (value, datetime.now().isoformat(), key)
        )
    else:
        conn.execute(
            """
            INSERT INTO preferences (key, value, count, updated_at)
            VALUES (?, ?, 1, ?)
            """,
            (key, value, datetime.now().isoformat())
        )

    conn.commit()
    conn.close()


def get_preference(key: str, min_count: int = 2):
    """
    Return a preference value only if it has been
    seen at least min_count times. This stops a one-off
    entity from overwriting a real preference.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT value, count FROM preferences WHERE key = ?", (key,)
    ).fetchone()
    conn.close()

    if row and row["count"] >= min_count:
        return row["value"]
    return None


def get_all_preferences() -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT key, value, count FROM preferences WHERE count >= 2"
    ).fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


# -------------------------
# Read recent history
# -------------------------
def get_recent_turns(n: int = 10) -> list:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT timestamp, raw_text, intent, entities, response
        FROM conversations
        ORDER BY id DESC
        LIMIT ?
        """,
        (n,)
    ).fetchall()
    conn.close()

    turns = []
    for row in rows:
        turns.append({
            "timestamp" : row["timestamp"],
            "raw_text"  : row["raw_text"],
            "intent"    : row["intent"],
            "entities"  : json.loads(row["entities"]) if row["entities"] else {},
            "response"  : row["response"]
        })

    return list(reversed(turns))  # oldest first

# -------------------------
# Count total conversation turns —
# powers the UI's "memory turns" stat
# -------------------------
def get_conversation_count() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as count FROM conversations").fetchone()
    conn.close()
    return row["count"] if row else 0

# -------------------------
# State management
# -------------------------
def get_state_value(key: str, default=None):
    """Read a single state value by key."""
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM state WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row["value"] if row else default


def set_state_value(key: str, value: str):
    """Write a state value — inserts or updates."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO state (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value      = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, str(value), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def delete_state_value(key: str):
    """Remove a state key entirely."""
    conn = get_connection()
    conn.execute("DELETE FROM state WHERE key = ?", (key,))
    conn.commit()
    conn.close()

def get_briefing_date() -> str:
    return get_state_value("last_briefing_date", "")

def set_briefing_date(date_str: str):
    set_state_value("last_briefing_date", date_str)

if __name__ == "__main__":
    init_db()
    print(f"Database initialised at: {DB_PATH}")