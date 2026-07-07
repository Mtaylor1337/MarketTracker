from datetime import datetime
import requests

from config import COINGECKO_URL, DEFAULT_CURRENCY
from database import get_connection, save_snapshot

COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "DOGE": "dogecoin",
}


def fetch_and_save_prices():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, symbol FROM assets")
    assets = cursor.fetchall()

    conn.close()

    valid_assets = []

    for asset_id, symbol in assets:
        coin_id = COIN_IDS.get(symbol.upper())

        if coin_id is not None:
            valid_assets.append((asset_id, symbol, coin_id))

    ids = ",".join([coin_id for asset_id, symbol, coin_id in valid_assets])

    params = {
        "ids": ids,
        "vs_currencies": DEFAULT_CURRENCY
    }

    response = requests.get(COINGECKO_URL, params=params)
    response.raise_for_status()

    data = response.json()

    timestamp = datetime.now().isoformat(timespec="seconds")

    for asset_id, symbol, coin_id in valid_assets:
        price = data[coin_id][DEFAULT_CURRENCY]
        save_snapshot(asset_id, price, timestamp)