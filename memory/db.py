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
    conn.execute(
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
            json.dumps(packet.get("entities", {})),
            response,
            int(packet.get("context_used", False))
        )
    )
    conn.commit()
    conn.close()


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


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at: {DB_PATH}")