import sqlite3

def get_connection():

    conn = sqlite3.connect("chumcred_lms.db", check_same_thread=False)

    conn.row_factory = sqlite3.Row

    return conn