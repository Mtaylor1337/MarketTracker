import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from database import get_connection
from market_service import fetch_and_save_prices

REFRESH_COOLDOWN_SECONDS = 30
REFRESH_INTERVAL_OPTIONS = {
    "30 sec": 30,
    "1 min": 60,
    "5 min": 300,
    "30 min": 1800,
    "1 hr": 3600,
}

def enable_refresh():
    refresh_button.config(state="normal")
    manual_status_label.config(text="Manual Refresh: Ready")

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


def refresh_prices():
    refresh_button.config(state="disabled")
    manual_status_label.config(text="Manual refresh running...")
    root.update_idletasks()

    try:
        fetch_and_save_prices()
        load_snapshots()
        manual_status_label.config(
            text=f"Manual refresh cooling down: {REFRESH_COOLDOWN_SECONDS} sec"
        )
    except Exception as e:
        messagebox.showerror(
            "Refresh Error",
            f"Failed to refresh prices:\n{e}"
        )
        manual_status_label.config(text="Manual Refresh: Error")
    finally:
        countdown_refresh(REFRESH_COOLDOWN_SECONDS)

def start_tracking():
    start_tracking_button.config(state="disabled")
    stop_tracking_button.config(state="normal")
    tracking_status_label.config(text="Tracking: Running")


def stop_tracking():
    start_tracking_button.config(state="normal")
    stop_tracking_button.config(state="disabled")
    tracking_status_label.config(text="Tracking: Idle")

root = tk.Tk()
root.title("MarketTracker")
root.geometry("900x550")

title = ttk.Label(root, text="MarketTracker", font=("Segoe UI", 22))
title.pack(pady=15)

toolbar = ttk.Frame(root)
toolbar.pack(fill="x", padx=20, pady=5)

interval_label = ttk.Label(toolbar, text="Check market every:")
interval_label.pack(side="left")

interval_choice = tk.StringVar(value="30 sec")

interval_dropdown = ttk.Combobox(
    toolbar,
    textvariable=interval_choice,
    values=list(REFRESH_INTERVAL_OPTIONS.keys()),
    state="readonly",
    width=10
)
interval_dropdown.pack(side="left", padx=8)

start_tracking_button = ttk.Button(
    toolbar,
    text="Start Tracking",
    command=start_tracking
)
start_tracking_button.pack(side="left", padx=10)

stop_tracking_button = ttk.Button(
    toolbar,
    text="Stop Tracking",
    command=stop_tracking,
    state="disabled"
)
stop_tracking_button.pack(side="left", padx=5)

refresh_button = ttk.Button(
    toolbar,
    text="Refresh Now",
    command=refresh_prices
)
refresh_button.pack(side="left", padx=10)

tracking_status_label = ttk.Label(toolbar, text="Tracking: Idle")
tracking_status_label.pack(side="left", padx=15)

manual_status_label = ttk.Label(toolbar, text="Manual Refresh: Ready")
manual_status_label.pack(side="left", padx=15)

columns = ("ID", "Symbol", "Timestamp", "Price")

snapshot_table = ttk.Treeview(root, columns=columns, show="headings")

for column in columns:
    snapshot_table.heading(column, text=column)
    snapshot_table.column(column, width=180)

snapshot_table.pack(fill="both", expand=True, padx=20, pady=15)

load_snapshots()

root.mainloop()
