from database import get_connection, get_utc_timestamp


ASSET_METADATA = {
    "BTC": {
        "name": "Bitcoin",
        "api_id": "bitcoin",
    },
    "ETH": {
        "name": "Ethereum",
        "api_id": "ethereum",
    },
    "SOL": {
        "name": "Solana",
        "api_id": "solana",
    },
    "XRP": {
        "name": "XRP",
        "api_id": "ripple",
    },
    "DOGE": {
        "name": "Dogecoin",
        "api_id": "dogecoin",
    },
}


def upgrade_asset_metadata():
    conn = get_connection()
    cursor = conn.cursor()

    updated_count = 0
    missing_symbols = []

    for symbol, metadata in ASSET_METADATA.items():
        cursor.execute(
            """
            SELECT id
            FROM assets
            WHERE UPPER(symbol) = ?
            """,
            (symbol,)
        )

        asset = cursor.fetchone()

        if asset is None:
            missing_symbols.append(symbol)
            continue

        cursor.execute(
            """
            UPDATE assets
            SET name = ?,
                api_id = ?,
                quote_currency = ?,
                is_active = ?,
                created_at_utc = COALESCE(
                    created_at_utc,
                    ?
                )
            WHERE id = ?
            """,
            (
                metadata["name"],
                metadata["api_id"],
                "usd",
                1,
                get_utc_timestamp(),
                asset[0],
            )
        )

        updated_count += 1

    conn.commit()
    conn.close()

    return updated_count, missing_symbols


def print_asset_metadata():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            symbol,
            name,
            api_id,
            quote_currency,
            is_active,
            created_at_utc
        FROM assets
        ORDER BY id
        """
    )

    assets = cursor.fetchall()
    conn.close()

    print("\nAsset metadata:")

    for asset in assets:
        (
            asset_id,
            symbol,
            name,
            api_id,
            quote_currency,
            is_active,
            created_at_utc,
        ) = asset

        print(
            f"  {asset_id}: "
            f"{symbol} | "
            f"{name} | "
            f"{api_id} | "
            f"{quote_currency} | "
            f"active={is_active} | "
            f"{created_at_utc}"
        )


def main():
    updated_count, missing_symbols = upgrade_asset_metadata()

    print(
        f"Asset metadata upgrade complete. "
        f"Updated {updated_count} assets."
    )

    if missing_symbols:
        print(
            "Assets not found in the database: "
            + ", ".join(missing_symbols)
        )

    print_asset_metadata()


if __name__ == "__main__":
    main()
    