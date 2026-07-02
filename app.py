from collector import get_crypto_prices
from database import (
    create_tables,
    save_snapshot,
    get_asset_id
)


def main():
    create_tables()

    prices = get_crypto_prices()

    for symbol, price in prices.items():
        print(f"{symbol} Price: ${price:,.2f}")

        asset_id = get_asset_id(symbol)

        if asset_id is None:
            print(f"{symbol} has not been added to the assets table.")
            continue

        save_snapshot(asset_id, price)


if __name__ == "__main__":
    main()
    