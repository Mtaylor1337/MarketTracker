import time
from collector import run_collection


INTERVAL_SECONDS = 10


def main():
    print("MarketTracker automatic tracker started.")
    print(f"Taking snapshots every {INTERVAL_SECONDS} seconds.")
    print("Press CTRL + C to stop.\n")

    try:
        while True:
            run_collection()
            print(f"Waiting {INTERVAL_SECONDS} seconds...\n")
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nTracker stopped by user.")


if __name__ == "__main__":
    main()