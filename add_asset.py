import sqlite3

conn = sqlite3.connect("market.db")
cursor = conn.cursor()

# Insert BTC as a tracked asset
cursor.execute("""
INSERT INTO assets (symbol, asset_type, interval_minutes, alert_high, alert_low)
VALUES (?, ?, ?, ?, ?)
""", ("BTC", "crypto", 15, 120000, 90000))

conn.commit()

# Read it back to confirm
cursor.execute("SELECT * FROM assets")
rows = cursor.fetchall()

print("Assets in database:")
for row in rows:
    print(row)

conn.close()