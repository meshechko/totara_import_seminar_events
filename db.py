import sqlite3
import time

conn = sqlite3.connect('database.db')
# print("Opened database successfully")

# conn.execute('CREATE TABLE users (id TEXT, firstname TEXT, lastname TEXT, email TEXT, password TEXT, company TEXT, created INTEGER, lastlogin INTEGER, super_user_id TEXT)')
# conn.execute('ALTER TABLE users ADD timezone TEXT')

# print("Table created successfully")

# conn.close()



# with sqlite3.connect("database.db") as con:
#     cur = con.cursor()
#     cur.execute("INSERT INTO users (id,firstname) VALUES ('nfwjkfnwkej','Olexiy')")
#     # cur.execute("DELETE FROM students")
#     con.commit()






DATABASE = "database.db"

def create_user(id, created, lastlogin, firstname, lastname, email, password, company, super_user_id, timezone):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (id, firstname, lastname, email, password, company, super_user_id, created, lastlogin, timezone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(id, firstname, lastname, email, password, company, super_user_id, created, lastlogin, timezone) )
        print('Creating user....')
        conn.commit()

def update_lastlogin(id):
    with sqlite3.connect(DATABASE) as conn:
        lastlogin = int(time.time())
        cur = conn.cursor()
        cur.execute("UPDATE users SET lastlogin = ? WHERE ID = ?",(lastlogin, id) )
        conn.commit()

def update_timezone(id, timezone):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET timezone = ? WHERE ID = ?",(timezone, id) )
        conn.commit()

def get_user(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?",(id, ))
        rows = cur.fetchone(); 
        return rows


# with sqlite3.connect(DATABASE) as conn:
#         conn.row_factory = sqlite3.Row
#         cur = conn.cursor()
#         cur.execute("SELECT * FROM users")
#         # cur.execute("DELETE FROM users")
#         rows = cur.fetchall(); 
#         print(f'Total records: {len(rows)}')
#         for row in rows:
#             print(row["id"])
#             print(f'created: {row["created"]}')
#             print(f'lastlogin: {row["lastlogin"]}')
