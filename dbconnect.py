import sqlite3
import os

initString1 = '''CREATE TABLE users (
    id INTEGER PRIMARY KEY
);'''
initString2 = '''
CREATE TABLE routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bus_number TEXT,
    bus_stop TEXT,
    direction TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);'''

dbName = 'bus.db'

def initialize():
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()

    cursor.execute(initString1)
    cursor.execute(initString2)

    conn.commit()
    conn.close()

if not os.path.exists(dbName):
    initialize()

def add_user(user_id):
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    existing_user = cursor.fetchone()

    if existing_user is None:
        cursor.execute("INSERT INTO users (id) VALUES (?)", (user_id,))

    conn.commit()
    conn.close()

def add_route(user_id, bus_number, bus_stop, direction):
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM routes WHERE bus_number=? AND bus_stop=? AND direction=?", (bus_number, bus_stop, direction))
    existing_route = cursor.fetchone()

    if existing_route is None:
        cursor.execute("INSERT INTO routes (user_id, bus_number, bus_stop, direction) VALUES (?, ?, ?, ?)", (user_id, bus_number, bus_stop, direction))
    else:
        return False

    conn.commit()
    conn.close()
    return True

def get_routes_by_user(user_id):
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM routes WHERE user_id=?", (user_id,))
    routes = cursor.fetchall()

    conn.close()

    return routes

def get_routes_by_id(id):
    conn = sqlite3.connect(dbName)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM routes WHERE id=?", (id,))
    routes = cursor.fetchall()

    conn.close()

    return routes