import sqlite3
from datetime import datetime, timezone

DATABASE_PATH = "data/markettracker.db"


# --------------------------------------------------
# Time helpers
# --------------------------------------------------
def get_utc_timestamp():
    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )


# --------------------------------------------------
# Database connection
# --------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# --------------------------------------------------
# Schema migration helpers
# --------------------------------------------------
def column_exists(cursor, table_name, column_name):
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()

    for column in columns:
        existing_column_name = column[1]

        if existing_column_name == column_name:
            return True

    return False


def add_column_if_missing(
    cursor,
    table_name,
    column_name,
    column_definition
):
    if column_exists(
        cursor,
        table_name,
        column_name
    ):
        return

    cursor.execute(
        f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name} {column_definition}
        """
    )


# --------------------------------------------------
# Create and upgrade database tables
# --------------------------------------------------
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # ----------------------------------------------
    # Existing assets table
    # ----------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            interval_minutes INTEGER,
            alert_high REAL,
            alert_low REAL
        )
    """)

    # ----------------------------------------------
    # Existing price-only snapshots table
    # This table remains untouched for compatibility.
    # ----------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(asset_id) REFERENCES assets(id)
        )
    """)

    # ----------------------------------------------
    # Add Version 0.8 asset metadata columns
    # ----------------------------------------------
    add_column_if_missing(
        cursor,
        "assets",
        "name",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "assets",
        "api_id",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "assets",
        "quote_currency",
        "TEXT DEFAULT 'usd'"
    )

    add_column_if_missing(
        cursor,
        "assets",
        "is_active",
        "INTEGER NOT NULL DEFAULT 1"
    )

    add_column_if_missing(
        cursor,
        "assets",
        "created_at_utc",
        "TEXT"
    )

    current_utc_time = get_utc_timestamp()

    cursor.execute("""
        UPDATE assets
        SET quote_currency = 'usd'
        WHERE quote_currency IS NULL
           OR TRIM(quote_currency) = ''
    """)

    cursor.execute("""
        UPDATE assets
        SET is_active = 1
        WHERE is_active IS NULL
    """)

    cursor.execute("""
        UPDATE assets
        SET created_at_utc = ?
        WHERE created_at_utc IS NULL
           OR TRIM(created_at_utc) = ''
    """, (current_utc_time,))

    # ----------------------------------------------
    # Version 0.8 collection run table
    # One record represents one complete market scan.
    # ----------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at_utc TEXT NOT NULL,
            completed_at_utc TEXT,
            requested_interval_seconds INTEGER,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            assets_requested INTEGER NOT NULL DEFAULT 0,
            assets_saved INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )
    """)

    # ----------------------------------------------
    # Version 0.8 rich market snapshot table
    # ----------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_run_id INTEGER NOT NULL,
            asset_id INTEGER NOT NULL,
            collected_at_utc TEXT NOT NULL,
            source_updated_at_utc TEXT,
            price REAL NOT NULL,
            market_cap REAL,
            market_cap_rank INTEGER,
            total_volume_24h REAL,
            high_24h REAL,
            low_24h REAL,
            price_change_24h REAL,
            price_change_percentage_24h REAL,
            circulating_supply REAL,
            total_supply REAL,
            max_supply REAL,
            source TEXT NOT NULL,
            FOREIGN KEY(collection_run_id)
                REFERENCES collection_runs(id),
            FOREIGN KEY(asset_id)
                REFERENCES assets(id)
        )
    """)

    # ----------------------------------------------
    # Helpful indexes for future reports and AI work
    # ----------------------------------------------
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_market_snapshots_asset_time
        ON market_snapshots (
            asset_id,
            collected_at_utc
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_market_snapshots_collection_run
        ON market_snapshots (
            collection_run_id
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_collection_runs_started_at
        ON collection_runs (
            started_at_utc
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# Existing Version 0.7 snapshot function
# Kept so the current UI continues working.
# --------------------------------------------------
def save_snapshot(
    asset_id,
    price,
    timestamp=None
):
    conn = get_connection()
    cursor = conn.cursor()

    if timestamp is None:
        timestamp = datetime.now().isoformat(
            timespec="seconds"
        )

    cursor.execute("""
        INSERT INTO snapshots (
            asset_id,
            timestamp,
            price
        )
        VALUES (?, ?, ?)
    """, (
        asset_id,
        timestamp,
        price
    ))

    conn.commit()
    conn.close()


# --------------------------------------------------
# Asset lookup
# --------------------------------------------------
def get_asset_id(symbol):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM assets
        WHERE symbol = ?
        """,
        (symbol,)
    )

    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]

    return None


# --------------------------------------------------
# Version 0.8 collection run functions
# These will be used by market_service.py later.
# --------------------------------------------------
def create_collection_run(
    requested_interval_seconds=None,
    source="CoinGecko",
    assets_requested=0
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO collection_runs (
            started_at_utc,
            requested_interval_seconds,
            source,
            status,
            assets_requested,
            assets_saved
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        get_utc_timestamp(),
        requested_interval_seconds,
        source,
        "running",
        assets_requested,
        0
    ))

    collection_run_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return collection_run_id


def complete_collection_run(
    collection_run_id,
    assets_saved
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE collection_runs
        SET completed_at_utc = ?,
            status = ?,
            assets_saved = ?,
            error_message = NULL
        WHERE id = ?
    """, (
        get_utc_timestamp(),
        "completed",
        assets_saved,
        collection_run_id
    ))

    conn.commit()
    conn.close()


def fail_collection_run(
    collection_run_id,
    error_message,
    assets_saved=0
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE collection_runs
        SET completed_at_utc = ?,
            status = ?,
            assets_saved = ?,
            error_message = ?
        WHERE id = ?
    """, (
        get_utc_timestamp(),
        "failed",
        assets_saved,
        str(error_message),
        collection_run_id
    ))

    conn.commit()
    conn.close()


# --------------------------------------------------
# Version 0.8 rich snapshot function
# This will be used by market_service.py later.
# --------------------------------------------------
def save_market_snapshot(
    collection_run_id,
    asset_id,
    price,
    source,
    collected_at_utc=None,
    source_updated_at_utc=None,
    market_cap=None,
    market_cap_rank=None,
    total_volume_24h=None,
    high_24h=None,
    low_24h=None,
    price_change_24h=None,
    price_change_percentage_24h=None,
    circulating_supply=None,
    total_supply=None,
    max_supply=None
):
    conn = get_connection()
    cursor = conn.cursor()

    if collected_at_utc is None:
        collected_at_utc = get_utc_timestamp()

    cursor.execute("""
        INSERT INTO market_snapshots (
            collection_run_id,
            asset_id,
            collected_at_utc,
            source_updated_at_utc,
            price,
            market_cap,
            market_cap_rank,
            total_volume_24h,
            high_24h,
            low_24h,
            price_change_24h,
            price_change_percentage_24h,
            circulating_supply,
            total_supply,
            max_supply,
            source
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        collection_run_id,
        asset_id,
        collected_at_utc,
        source_updated_at_utc,
        price,
        market_cap,
        market_cap_rank,
        total_volume_24h,
        high_24h,
        low_24h,
        price_change_24h,
        price_change_percentage_24h,
        circulating_supply,
        total_supply,
        max_supply,
        source
    ))

    snapshot_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return snapshot_id


# --------------------------------------------------
# Database verification
# --------------------------------------------------
def print_database_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)

    tables = cursor.fetchall()

    print("\nDatabase tables:")

    for table in tables:
        print(f"  - {table[0]}")

    cursor.execute(
        "PRAGMA table_info(assets)"
    )

    asset_columns = cursor.fetchall()

    print("\nAssets table columns:")

    for column in asset_columns:
        print(f"  - {column[1]}")

    conn.close()


if __name__ == "__main__":
    create_tables()

    print(
        "Database Version 0.8 foundation ready!"
    )

    print_database_summary()