import time

from database import create_tables
from market_service import fetch_and_save_prices


INTERVAL_SECONDS = 10


def main():
    print("MarketTracker automatic tracker started.")
    print(f"Taking snapshots every {INTERVAL_SECONDS} seconds.")
    print("Press CTRL + C to stop.\n")

    create_tables()

    try:
        while True:
            fetch_and_save_prices()
            print("Market snapshot saved.")
            print(f"Waiting {INTERVAL_SECONDS} seconds...\n")
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nTracker stopped by user.")


if __name__ == "__main__":
    main()