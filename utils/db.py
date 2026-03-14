import sqlite3

def get_connection():

    conn = sqlite3.connect("chumcred_lms.db", check_same_thread=False)

    conn.row_factory = sqlite3.Row

    create_tables(conn)

    return conn


def create_tables(conn):

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_exam_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        exam_unlocked BOOLEAN DEFAULT 0,
        exam_reviewed BOOLEAN DEFAULT 0,
        last_score INTEGER DEFAULT 0,
        attempts INTEGER DEFAULT 0
    )
    """)

    conn.commit()