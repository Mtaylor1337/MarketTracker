from database import get_connection


def main():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            snapshots.id,
            assets.symbol,
            snapshots.timestamp,
            snapshots.price
        FROM snapshots
        JOIN assets ON snapshots.asset_id = assets.id
        ORDER BY snapshots.timestamp DESC
        LIMIT 25
    """)

    rows = cursor.fetchall()

    print("Recent snapshots:")
    print("-----------------")

    for row in rows:
        snapshot_id, symbol, timestamp, price = row
        print(f"{snapshot_id} | {symbol} | {timestamp} | ${price:,.2f}")

    conn.close()


if __name__ == "__main__":
    main()