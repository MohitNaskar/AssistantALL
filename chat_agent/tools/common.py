import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("chat-agent")
logger.setLevel(logging.INFO)

DB_PATH = Path(__file__).parent.parent / "contacts.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            phone_number TEXT    NOT NULL,
            email        TEXT    NOT NULL,
            message      TEXT    DEFAULT '',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn
