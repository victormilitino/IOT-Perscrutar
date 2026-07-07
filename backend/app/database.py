import sqlite3
DB_PATH = 'backend.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('\n        CREATE TABLE IF NOT EXISTS people (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            name TEXT NOT NULL,\n            tag TEXT NOT NULL UNIQUE,\n            image_path TEXT\n        )\n    ')
    conn.commit()
    conn.close()