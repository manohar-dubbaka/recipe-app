import sqlite3

conn = sqlite3.connect("recipes.db")
c = conn.cursor()

c.execute("SELECT id, username, password FROM users")
rows = c.fetchall()

print("Users in DB:")
for row in rows:
    print(row)

conn.close()
