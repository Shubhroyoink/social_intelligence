import sqlite3

conn = sqlite3.connect("social.db")

indexes = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'index'
""").fetchall()

print("Indexes:")
for index in indexes:
    print(index[0])

conn.close()