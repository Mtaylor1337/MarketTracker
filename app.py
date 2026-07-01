from collector import get_bitcoin_price
from database import (
    create_tables,
    save_snapshot,
    get_asset_id
)


def main():

    # Make sure database exists
    create_tables()

    # Get live Bitcoin price
    btc_price = get_bitcoin_price()

    print(f"BTC Price: ${btc_price:,.2f}")

    # Find Bitcoin in the assets table
    asset_id = get_asset_id("BTC")

    if asset_id is None:
        print("Bitcoin has not been added to the Assets table.")
        return

    # Save price history
    save_snapshot(asset_id, btc_price)


if __name__ == "__main__":
    main()
    