import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row
cursor = conn.execute("PRAGMA table_info(history)")
for r in cursor.fetchall():
    print(dict(r))