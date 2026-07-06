from datetime import datetime
import tkinter as tk
from tkinter import ttk
from urllib import response
from database import get_connection
from tkinter import messagebox
import requests

REFRESH_COOLDOWN_SECONDS = 10

def enable_refresh():
    refresh_button.config(state="normal")
    status_label.config(text="Ready")

def countdown_refresh(seconds_remaining):
    if seconds_remaining > 0:
        status_label.config(text=f"Ready in {seconds_remaining}...")
        root.after(1000, countdown_refresh, seconds_remaining - 1)
    else:
        enable_refresh()

def load_snapshots():
    for row in snapshot_table.get_children():
        snapshot_table.delete(row)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            snapshots.id,
            assets.symbol,
            snapshots.timestamp,
            snapshots.price
        FROM snapshots
        JOIN assets ON snapshots.asset_id = assets.id
        ORDER BY snapshots.timestamp DESC
        LIMIT 25
    """)

    rows = cursor.fetchall()
    conn.close()

    for snapshot_id, symbol, timestamp, price in rows:
        snapshot_table.insert(
            "",
            "end",
            values=(snapshot_id, symbol, timestamp, f"${price:,.2f}")
        )

def fetch_and_save_prices():
    coin_ids = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "DOGE": "dogecoin",
    }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, symbol FROM assets")
    assets = cursor.fetchall()

    valid_assets = []
    for asset_id, symbol in assets:
        coin_id = coin_ids.get(symbol.upper())

        if coin_id is not None:
            valid_assets.append((asset_id, symbol, coin_id))

    ids = ",".join([coin_id for asset_id, symbol, coin_id in valid_assets])

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ids,
        "vs_currencies": "usd"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    timestamp = datetime.now().isoformat(timespec="seconds")

    for asset_id, symbol, coin_id in valid_assets:
        price = data[coin_id]["usd"]

        cursor.execute("""
            INSERT INTO snapshots (asset_id, timestamp, price)
            VALUES (?, ?, ?)
        """, (asset_id, timestamp, price))

    conn.commit()
    conn.close()

def refresh_prices():
    refresh_button.config(state="disabled")
    status_label.config(text="Refreshing...")
    root.update_idletasks()

    try:
        fetch_and_save_prices()
        load_snapshots()
        status_label.config(
            text=f"Prices refreshed. Waiting {REFRESH_COOLDOWN_SECONDS} seconds...")
    except Exception as e:
        messagebox.showerror("Refresh Error", f"Failed to refresh prices:\n{e}")
        status_label.config(text="Error refreshing")
    finally:
        countdown_refresh(REFRESH_COOLDOWN_SECONDS)

root = tk.Tk()
root.title("MarketTracker")
root.geometry("900x550")

title = ttk.Label(root, text="MarketTracker", font=("Segoe UI", 22))
title.pack(pady=15)

toolbar = ttk.Frame(root)
toolbar.pack(fill="x", padx=20, pady=5)

refresh_button = ttk.Button(
    toolbar,
    text="Refresh Prices",
    command=refresh_prices
)
refresh_button.pack(side="left")

status_label = ttk.Label(toolbar, text="Ready")
status_label.pack(side="left", padx=15)

columns = ("ID", "Symbol", "Timestamp", "Price")

snapshot_table = ttk.Treeview(root, columns=columns, show="headings")

for column in columns:
    snapshot_table.heading(column, text=column)
    snapshot_table.column(column, width=180)

snapshot_table.pack(fill="both", expand=True, padx=20, pady=15)

load_snapshots()

root.mainloop()