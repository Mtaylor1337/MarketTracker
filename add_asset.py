from database import create_tables, get_connection


def main():
    create_tables()

    conn = get_connection()
    cursor = conn.cursor()

    assets = [
        ("BTC", "crypto", 15, 120000, 90000),
        ("ETH", "crypto", 15, 5000, 1000),
        ("SOL", "crypto", 15, 300, 50),
        ("XRP", "crypto", 15, 5, 0.50),
        ("DOGE", "crypto", 15, 1, 0.05),
    ]

    for asset in assets:
        cursor.execute("""
            SELECT id FROM assets WHERE symbol = ?
        """, (asset[0],))

        existing_asset = cursor.fetchone()

        if existing_asset:
            print(f"{asset[0]} already exists. Skipping.")
            continue

        cursor.execute("""
            INSERT INTO assets
            (symbol, asset_type, interval_minutes, alert_high, alert_low)
            VALUES (?, ?, ?, ?, ?)
        """, asset)

        print(f"{asset[0]} added.")

    conn.commit()

    cursor.execute("SELECT * FROM assets")
    rows = cursor.fetchall()

    print("\nAssets in database:")
    for row in rows:
        print(row)

    conn.close()


if __name__ == "__main__":
    main()