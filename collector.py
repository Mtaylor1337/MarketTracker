import requests
from config import COINGECKO_URL, DEFAULT_CURRENCY


def get_bitcoin_price():
    params = {
        "ids": "bitcoin",
        "vs_currencies": DEFAULT_CURRENCY
    }

    response = requests.get(COINGECKO_URL, params=params)
    response.raise_for_status()

    data = response.json()

    return data["bitcoin"][DEFAULT_CURRENCY]