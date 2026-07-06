import sqlite3
from typing import List, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime

@dataclass
class Contact_details:
    id: int
    name: str
    phone_number: str
    email: str
    message: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class DatabaseDriver:
    def __init__(self, db_path: str = "auto_db.sqlite"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create contact details table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contact_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone_number TEXT NOT NULL UNIQUE,
                    email TEXT,
                    message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_contact_details(self, details: Contact_details):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contact_details (name, phone_number, email, message, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (details.name, details.phone_number, details.email, details.message, details.created_at))
            conn.commit()
            return cursor.lastrowid
        
    def get_contact_by_phone(self, phone_number: str) -> Optional[Contact_details]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, phone_number, email, message, created_at
                FROM contact_details
                WHERE phone_number = ?
                LIMIT 1
                """,
                (phone_number,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return Contact_details(
                id=row["id"],
                name=row["name"],
                phone_number=row["phone_number"],
                email=row["email"],
                message=row["message"],
                created_at=row["created_at"],
            )

    def get_all_contacts(self) -> List[Contact_details]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, phone_number, email, message, created_at
                FROM contact_details
                ORDER BY id DESC
                """
            )
            rows = cursor.fetchall()

            return [
                Contact_details(
                    id=row["id"],
                    name=row["name"],
                    phone_number=row["phone_number"],
                    email=row["email"],
                    message=row["message"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]