from datetime import datetime
import requests
from database import get_connection


def fetch_and_save_prices():
    coin_ids = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "DOGE": "dogecoin",
    }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, symbol FROM assets")
    assets = cursor.fetchall()

    valid_assets = []

    for asset_id, symbol in assets:
        coin_id = coin_ids.get(symbol.upper())

        if coin_id is not None:
            valid_assets.append((asset_id, symbol, coin_id))

    ids = ",".join([coin_id for asset_id, symbol, coin_id in valid_assets])

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ids,
        "vs_currencies": "usd"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    timestamp = datetime.now().isoformat(timespec="seconds")

    for asset_id, symbol, coin_id in valid_assets:
        price = data[coin_id]["usd"]

        cursor.execute("""
            INSERT INTO snapshots (asset_id, timestamp, price)
            VALUES (?, ?, ?)
        """, (asset_id, timestamp, price))

    conn.commit()
    conn.close()