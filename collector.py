import requests
from config import COINGECKO_URL, DEFAULT_CURRENCY
from database import (
    create_tables,
    save_snapshot,
    get_asset_id
)


CRYPTO_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "DOGE": "dogecoin",
}


def get_crypto_prices():
    params = {
        "ids": ",".join(CRYPTO_MAP.values()),
        "vs_currencies": DEFAULT_CURRENCY
    }

    response = requests.get(COINGECKO_URL, params=params)
    response.raise_for_status()

    data = response.json()

    prices = {}

    for symbol, coingecko_id in CRYPTO_MAP.items():
        prices[symbol] = data[coingecko_id][DEFAULT_CURRENCY]

    return prices


def run_collection():
    create_tables()

    prices = get_crypto_prices()

    for symbol, price in prices.items():
        print(f"{symbol} Price: ${price:,.2f}")

        asset_id = get_asset_id(symbol)

        if asset_id is None:
            print(f"{symbol} has not been added to the assets table.")
            continue

        save_snapshot(asset_id, price)