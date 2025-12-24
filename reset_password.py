from services.db import init_db, get_conn
import bcrypt

USERNAME = "Adekunle Adegbie"   # change if your username is different
NEW_PASSWORD = "1234"    # change to what you want

def main():
    init_db()
    conn = get_conn()
    cur = conn.cursor()

    pw_hash = bcrypt.hashpw(NEW_PASSWORD.encode("utf-8"), bcrypt.gensalt())

    cur.execute("UPDATE users SET password_hash=?, active=1 WHERE username=?", (pw_hash, USERNAME))
    conn.commit()

    if cur.rowcount == 0:
        print("User not found. Check the username exactly as stored in DB.")
    else:
        print("Password reset done for:", USERNAME)

    conn.close()

if __name__ == "__main__":
    main()
