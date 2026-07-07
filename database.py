import sqlite3
from datetime import datetime

DATABASE_PATH = "data/markettracker.db"


# -------------------------------------------
# Database Connection
# -------------------------------------------
def get_connection():
    return sqlite3.connect(DATABASE_PATH)


# -------------------------------------------
# Create tables if they don't exist
# -------------------------------------------
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        interval_minutes INTEGER,
        alert_high REAL,
        alert_low REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        price REAL NOT NULL,
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    )
    """)

    conn.commit()
    conn.close()


# -------------------------------------------
# Save a price snapshot
# -------------------------------------------
def save_snapshot(asset_id, price, timestamp=None):
    conn = get_connection()
    cursor = conn.cursor()

    if timestamp is None:
        timestamp = datetime.now().isoformat(timespec="seconds")

    cursor.execute("""
        INSERT INTO snapshots (asset_id, timestamp, price)
        VALUES (?, ?, ?)
    """, (asset_id, timestamp, price))

    conn.commit()
    conn.close()


def get_asset_id(symbol):
    conn: sqlite3.Connection = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM assets WHERE symbol = ?",
        (symbol,)
    )

    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]

    return None

if __name__ == "__main__":
    create_tables()
    print("Database tables ready!")
