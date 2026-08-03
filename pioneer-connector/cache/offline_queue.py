import sqlite3
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger("pioneer_connector.queue")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "connector_cache.db")

def init_queue_db():
    """Initializes the offline_queue SQLite table if it does not exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing offline queue DB: {e}")

# Initialize on import
init_queue_db()

def enqueue_payload(payload_type: str, payload_data: Dict[str, Any]) -> bool:
    """Enqueues a canonical JSON payload to local SQLite storage when network is offline."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now_str = datetime.utcnow().isoformat() + "Z"
        cursor.execute(
            "INSERT INTO offline_queue (payload_type, payload_json, created_at) VALUES (?, ?, ?)",
            (payload_type, json.dumps(payload_data), now_str)
        )
        conn.commit()
        conn.close()
        logger.info(f"Queued offline payload ({payload_type}) to SQLite.")
        return True
    except Exception as e:
        logger.error(f"Failed to enqueue payload: {e}")
        return False

def get_offline_queue_size() -> int:
    """Returns the total number of pending offline payloads."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM offline_queue")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def fetch_and_clear_queue() -> List[Dict[str, Any]]:
    """Fetches all pending payloads and clears the queue."""
    items = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, payload_type, payload_json, created_at FROM offline_queue ORDER BY id ASC")
        rows = cursor.fetchall()
        for r in rows:
            items.append({
                "id": r[0],
                "payload_type": r[1],
                "payload_data": json.loads(r[2]),
                "created_at": r[3]
            })
        if rows:
            cursor.execute("DELETE FROM offline_queue")
            conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to fetch/clear offline queue: {e}")
    return items
