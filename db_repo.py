# db_repo.py
import sqlite3
from typing import Any, Dict, List, Optional
from config import DB_PATH

def connect():
    # fresh connection each call is safest in Streamlit
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS help_support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            student_id TEXT,
            student_name TEXT,
            week INTEGER,
            category TEXT,
            subject TEXT,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            admin_reply TEXT
        );
        """)
        conn.commit()

def create_ticket(student_id: str, student_name: str, week: int, category: str, subject: str, message: str) -> int:
    init_db()
    with connect() as conn:
        cur = conn.execute("""
            INSERT INTO help_support_tickets (student_id, student_name, week, category, subject, message, status)
            VALUES (?, ?, ?, ?, ?, ?, 'open')
        """, (student_id, student_name, week, category, subject, message))
        conn.commit()
        return int(cur.lastrowid)

def list_tickets(status: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    init_db()
    with connect() as conn:
        if status:
            rows = conn.execute("""
                SELECT * FROM help_support_tickets
                WHERE status = ?
                ORDER BY datetime(created_at) DESC
                LIMIT ?
            """, (status, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM help_support_tickets
                ORDER BY datetime(created_at) DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def update_ticket(ticket_id: int, status: str, admin_reply: Optional[str] = None) -> None:
    init_db()
    with connect() as conn:
        if admin_reply is None:
            conn.execute("UPDATE help_support_tickets SET status = ? WHERE id = ?", (status, ticket_id))
        else:
            conn.execute("UPDATE help_support_tickets SET status = ?, admin_reply = ? WHERE id = ?", (status, admin_reply, ticket_id))
        conn.commit()
