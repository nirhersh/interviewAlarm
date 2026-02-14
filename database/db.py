import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os


class Database:
    def __init__(self, db_path: str = "interview_alarm.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize the database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create tracked_urls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracked_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                company_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, url)
            )
        """)

        # Create time_slots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracked_url_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                is_notified BOOLEAN DEFAULT 0,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tracked_url_id) REFERENCES tracked_urls (id) ON DELETE CASCADE,
                UNIQUE(tracked_url_id, start_time)
            )
        """)

        conn.commit()
        conn.close()

    def add_tracked_url(self, user_id: int, url: str, company_name: str) -> Optional[int]:
        """
        Add a tracked URL to the database
        Returns the tracked_url_id if successful, None if already exists
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO tracked_urls (user_id, url, company_name)
                VALUES (?, ?, ?)
            """, (user_id, url, company_name))
            conn.commit()
            tracked_url_id = cursor.lastrowid
            conn.close()
            return tracked_url_id
        except sqlite3.IntegrityError:
            # URL already tracked by this user
            conn.close()
            return None

    def remove_tracked_url(self, user_id: int, url: str) -> bool:
        """
        Remove a tracked URL and all associated time slots
        Returns True if removed, False if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM tracked_urls
            WHERE user_id = ? AND url = ?
        """, (user_id, url))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        return rows_affected > 0

    def get_user_tracked_urls(self, user_id: int) -> List[Dict]:
        """Get all tracked URLs for a specific user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, url, company_name, created_at
            FROM tracked_urls
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "url": row[1],
                "company_name": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]

    def get_all_tracked_urls(self) -> List[Dict]:
        """Get all tracked URLs for monitoring"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, url, company_name
            FROM tracked_urls
        """)

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "url": row[2],
                "company_name": row[3]
            }
            for row in rows
        ]

    def save_time_slots(self, tracked_url_id: int, slots: List[Dict], is_notified: bool = False) -> int:
        """
        Save time slots to the database (INSERT new or UPDATE existing)
        Returns the number of new/updated slots
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        slots_saved = 0
        for slot in slots:
            # Use INSERT OR REPLACE to handle both new and modified slots
            # This will update the slot if it exists (same tracked_url_id + start_time)
            cursor.execute("""
                INSERT OR REPLACE INTO time_slots (tracked_url_id, start_time, end_time, is_notified)
                VALUES (?, ?, ?, ?)
            """, (tracked_url_id, slot['start_time'], slot['end_time'], is_notified))
            slots_saved += 1

        conn.commit()
        conn.close()

        return slots_saved

    def get_time_slots(self, tracked_url_id: int) -> List[Dict]:
        """Get all time slots for a tracked URL"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, start_time, end_time, is_notified, detected_at
            FROM time_slots
            WHERE tracked_url_id = ?
            ORDER BY start_time ASC
        """, (tracked_url_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "is_notified": row[3],
                "detected_at": row[4]
            }
            for row in rows
        ]

    def get_new_slots(self, tracked_url_id: int, current_slots: List[Dict]) -> List[Dict]:
        """
        Compare current slots with DB slots and return new or modified ones
        """
        # Get existing slots from DB
        db_slots = self.get_time_slots(tracked_url_id)

        # Create a set of (start_time, end_time) tuples for comparison
        db_slot_tuples = {
            (slot['start_time'], slot['end_time'])
            for slot in db_slots
        }

        # Find new or modified slots
        # A slot is considered new/modified if the (start_time, end_time) pair doesn't exist
        new_slots = [
            slot for slot in current_slots
            if (slot['start_time'], slot['end_time']) not in db_slot_tuples
        ]

        return new_slots

    def mark_slots_notified(self, tracked_url_id: int, start_times: List[str]):
        """Mark specific slots as notified"""
        if not start_times:
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(start_times))
        cursor.execute(f"""
            UPDATE time_slots
            SET is_notified = 1
            WHERE tracked_url_id = ? AND start_time IN ({placeholders})
        """, [tracked_url_id] + start_times)

        conn.commit()
        conn.close()
