import sqlite3
import time

DATABASE = "database.db"


def create_user(id, created, lastlogin, firstname, lastname, email, password, company, super_user_id, timezone):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (id, firstname, lastname, email, password, company, super_user_id, created, lastlogin, timezone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(id, firstname, lastname, email, password, company, super_user_id, created, lastlogin, timezone) )
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


def get_user_rooms(user_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM rooms WHERE user_id = ?",(user_id, ))
        rows = cur.fetchall()
        rows_dict = [dict(row) for row in rows]
        return rows_dict


def delete_user_rooms(user_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("DELETE FROM rooms WHERE user_id = ? AND isDefault=0",(user_id, ))


def create_room(room_id, name, description, capacity, timecreated, building, location, allowconflicts, user_id, isDefault):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO rooms (room_id, name, description, capacity, timecreated, building, location, allowconflicts, user_id, isDefault) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(room_id, name, description, capacity, timecreated, building, location, allowconflicts, user_id, isDefault) )
        conn.commit()


def get_room(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM rooms WHERE id= ?",(id, ))
        rows = cur.fetchall()
        rows_dict = [dict(row) for row in rows]
        return rows_dict


def create_custom_field(field_id, name, type, data, paramdatavalue, user_id, isDefault):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO customfields (field_id, name, type, data, paramdatavalue, user_id, isDefault) VALUES (?, ?, ?, ?, ?, ?, ?)",(field_id, name, type, data, paramdatavalue, user_id, isDefault) )
        conn.commit()


def get_user_custom_fields(user_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM customfields WHERE user_id= ? ",(user_id, ))
        rows = cur.fetchall()
        rows_dict = [dict(row) for row in rows]
        return rows_dict


def delete_user_custom_fields(user_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("DELETE FROM customfields WHERE user_id = ? AND isDefault=0",(user_id, ))


def get_custom_field(id):
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM customfields WHERE id= ?",(id, ))
        rows = cur.fetchall()
        rows_dict = [dict(row) for row in rows]
        return rows_dict


#TEST CODE

# conn = sqlite3.connect('database.db')
# print("Opened database successfully")

# conn.execute('CREATE TABLE users (id TEXT, firstname TEXT, lastname TEXT, email TEXT, password TEXT, company TEXT, created INTEGER, lastlogin INTEGER, super_user_id TEXT)')

# conn.execute('CREATE TABLE rooms (id INTEGER PRIMARY KEY, room_id TEXT, name TEXT, description TEXT, capacity INTEGER, timecreated INTEGER, building TEXT, location TEXT, allowconflicts TEXT, user_id TEXT, isDefault INTEGER)')



# conn.execute('ALTER TABLE customfields ADD isDefault INTEGER')

# conn.execute('DROP TABLE customfields')

# conn.execute('CREATE TABLE customfields (id INTEGER PRIMARY KEY, field_id TEXT, name TEXT, type TEXT, data TEXT, paramdatavalue TEXT, user_id TEXT, isDefault INTEGER)')
# conn.execute('CREATE TABLE rooms (id INTEGER PRIMARY KEY, room_id TEXT, name TEXT, description TEXT, capacity INTEGER, timecreated INTEGER, building TEXT, location TEXT, allowconflicts TEXT, user_id TEXT, isDefault INTEGER)')

# print("Table created successfully")

# conn.close()



# with sqlite3.connect("database.db") as con:
#     cur = con.cursor()
#     cur.execute("INSERT INTO users (id,firstname) VALUES ('nfwjkfnwkej','Olexiy')")
#     # cur.execute("DELETE FROM students")
#     con.commit()



# with sqlite3.connect(DATABASE) as conn:
#         conn.row_factory = sqlite3.Row
#         cur = conn.cursor()
#         cursor = cur.execute("UPDATE users set email='ust@email.com' WHERE id='ust'")
#         # cur.execute("DELETE FROM customfields")
#         rows = [dict(row) for row in cursor.fetchall()]
#         # rows = dict(zip([c[0] for c in cursor.description], rows))
#         # names = list(map(lambda x: x[0], cursor.description))
#         # print(names)
#         print(f'Total records: {len(rows)}')
#         # print(f'{rows}')
#         # for row in rows:
#         #     print(row["id"])
#         #     print(f'created: {row["created"]}')
#         #     print(f'lastlogin: {row["lastlogin"]}')
