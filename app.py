from collector import get_bitcoin_price


def main():
    btc_price = get_bitcoin_price()
    print(f"Live BTC Price: ${btc_price:,.2f}")


if __name__ == "__main__":
    main()