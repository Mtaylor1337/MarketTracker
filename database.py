import sqlite3

# Create (or open) the database
conn = sqlite3.connect("market.db")

cursor = conn.cursor()

# Assets table
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

# Snapshots table
cursor.execute("""
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER,
    timestamp TEXT,
    price REAL,
    FOREIGN KEY(asset_id) REFERENCES assets(id)
)
""")

conn.commit()
conn.close()

print("Database created successfully!")
