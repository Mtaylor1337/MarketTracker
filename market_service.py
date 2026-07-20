from datetime import datetime, timezone

import requests

from config import (
    COINGECKO_MARKETS_URL,
    DATA_SOURCE,
    DEFAULT_CURRENCY,
    REQUEST_TIMEOUT_SECONDS,
)
from database import (
    complete_collection_run,
    create_collection_run,
    fail_collection_run,
    get_connection,
    save_market_snapshot,
)


def convert_coingecko_timestamp(timestamp):
    if not timestamp:
        return None

    parsed_timestamp = datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

    return parsed_timestamp.astimezone(
        timezone.utc
    ).isoformat(timespec="seconds")


def get_active_assets():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            symbol,
            api_id
        FROM assets
        WHERE is_active = 1
          AND api_id IS NOT NULL
          AND TRIM(api_id) != ''
        ORDER BY id
        """
    )

    assets = cursor.fetchall()
    conn.close()

    return assets


def fetch_and_save_prices(
    requested_interval_seconds=None
):
    assets = get_active_assets()

    if not assets:
        raise RuntimeError(
            "No active assets with API IDs were found."
        )

    collection_run_id = create_collection_run(
        requested_interval_seconds=requested_interval_seconds,
        source=DATA_SOURCE,
        assets_requested=len(assets),
    )

    assets_saved = 0

    try:
        asset_by_api_id = {
            api_id: {
                "asset_id": asset_id,
                "symbol": symbol,
            }
            for asset_id, symbol, api_id in assets
        }

        params = {
            "ids": ",".join(asset_by_api_id.keys()),
            "vs_currency": DEFAULT_CURRENCY,
            "order": "market_cap_desc",
            "sparkline": "false",
        }

        response = requests.get(
            COINGECKO_MARKETS_URL,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()
        market_data = response.json()

        if not isinstance(market_data, list):
            raise RuntimeError(
                "CoinGecko returned an unexpected response."
            )

        returned_api_ids = set()

        for coin in market_data:
            api_id = coin.get("id")

            if api_id not in asset_by_api_id:
                continue

            returned_api_ids.add(api_id)

            asset = asset_by_api_id[api_id]
            price = coin.get("current_price")

            if price is None:
                raise RuntimeError(
                    "CoinGecko did not return a price for "
                    f"{asset['symbol']}."
                )

            save_market_snapshot(
                collection_run_id=collection_run_id,
                asset_id=asset["asset_id"],
                price=price,
                source=DATA_SOURCE,
                source_updated_at_utc=(
                    convert_coingecko_timestamp(
                        coin.get("last_updated")
                    )
                ),
                market_cap=coin.get("market_cap"),
                market_cap_rank=coin.get(
                    "market_cap_rank"
                ),
                total_volume_24h=coin.get(
                    "total_volume"
                ),
                high_24h=coin.get("high_24h"),
                low_24h=coin.get("low_24h"),
                price_change_24h=coin.get(
                    "price_change_24h"
                ),
                price_change_percentage_24h=(
                    coin.get(
                        "price_change_percentage_24h"
                    )
                ),
                circulating_supply=coin.get(
                    "circulating_supply"
                ),
                total_supply=coin.get(
                    "total_supply"
                ),
                max_supply=coin.get("max_supply"),
            )

            assets_saved += 1

        missing_api_ids = (
            set(asset_by_api_id.keys())
            - returned_api_ids
        )

        if missing_api_ids:
            missing_symbols = [
                asset_by_api_id[api_id]["symbol"]
                for api_id in missing_api_ids
            ]

            raise RuntimeError(
                "CoinGecko returned no market data for: "
                + ", ".join(sorted(missing_symbols))
            )

        complete_collection_run(
            collection_run_id,
            assets_saved,
        )

        return assets_saved

    except Exception as error:
        fail_collection_run(
            collection_run_id,
            error,
            assets_saved,
        )

        raise


def print_latest_market_snapshots():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            market_snapshots.id,
            assets.symbol,
            market_snapshots.collected_at_utc,
            market_snapshots.price,
            market_snapshots.market_cap,
            market_snapshots.market_cap_rank,
            market_snapshots.total_volume_24h,
            market_snapshots.high_24h,
            market_snapshots.low_24h,
            market_snapshots.price_change_percentage_24h
        FROM market_snapshots
        JOIN assets
            ON market_snapshots.asset_id = assets.id
        ORDER BY market_snapshots.id DESC
        LIMIT 5
        """
    )

    snapshots = cursor.fetchall()
    conn.close()

    print("\nLatest rich market snapshots:")

    for snapshot in reversed(snapshots):
        (
            snapshot_id,
            symbol,
            collected_at_utc,
            price,
            market_cap,
            market_cap_rank,
            total_volume_24h,
            high_24h,
            low_24h,
            price_change_percentage_24h,
        ) = snapshot

        print(
            f"  {snapshot_id}: "
            f"{symbol} | "
            f"price=${price:,.4f} | "
            f"rank={market_cap_rank} | "
            f"market cap={market_cap} | "
            f"volume={total_volume_24h} | "
            f"high={high_24h} | "
            f"low={low_24h} | "
            f"24h={price_change_percentage_24h}% | "
            f"{collected_at_utc}"
        )


def main():
    assets_saved = fetch_and_save_prices()

    print(
        "Rich market collection complete. "
        f"Saved {assets_saved} assets."
    )

    print_latest_market_snapshots()


if __name__ == "__main__":
    main()