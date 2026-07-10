import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

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
tracking_active = False
tracking_after_id = None
tracking_total_seconds = 0
tracking_seconds_remaining = 0

def enable_refresh():
    refresh_button.config(state="normal")
    manual_status_label.config(text="Manual Refresh: Ready")


def countdown_refresh(seconds_remaining):
    if seconds_remaining > 0:
        manual_status_label.config(
            text=f"Manual Refresh: Ready in {seconds_remaining} sec"
        )
        root.after(
            1000,
            countdown_refresh,
            seconds_remaining - 1
        )
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
            values=(
                snapshot_id,
                symbol,
                timestamp,
                f"${price:,.2f}"
            )
        )


def refresh_prices():
    refresh_button.config(state="disabled")
    manual_status_label.config(text="Manual Refresh: Running...")
    root.update_idletasks()

    try:
        fetch_and_save_prices()
        load_snapshots()

        manual_status_label.config(
            text=(
                "Manual Refresh: Cooling down for "
                f"{REFRESH_COOLDOWN_SECONDS} sec"
            )
        )

    except Exception as e:
        messagebox.showerror(
            "Refresh Error",
            f"Failed to refresh prices:\n{e}"
        )

        manual_status_label.config(
            text="Manual Refresh: Error"
        )

    finally:
        countdown_refresh(REFRESH_COOLDOWN_SECONDS)

def format_tracking_time(total_seconds):
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def update_tracking_countdown():
    global tracking_active
    global tracking_after_id
    global tracking_seconds_remaining

    if not tracking_active:
        return

    elapsed_seconds = (
        tracking_total_seconds - tracking_seconds_remaining
    )

    progress_percent = (
        elapsed_seconds / tracking_total_seconds
    ) * 100

    tracking_progress.config(value=progress_percent)

    formatted_time = format_tracking_time(
        tracking_seconds_remaining
    )

    tracking_status_label.config(
        text=(
            "Tracking Progress: Running — "
            f"next market scan in {formatted_time}"
        )
    )

    if tracking_seconds_remaining > 0:
        tracking_seconds_remaining -= 1

        tracking_after_id = root.after(
            1000,
            update_tracking_countdown
        )

        return

    tracking_status_label.config(
        text="Tracking Progress: Fetching market prices..."
    )
    tracking_progress.config(value=100)
    root.update_idletasks()

    try:
        fetch_and_save_prices()
        load_snapshots()

    except Exception as e:
        messagebox.showerror(
            "Automatic Tracking Error",
            f"Failed to fetch market prices:\n{e}"
        )

        stop_tracking()

        tracking_status_label.config(
            text="Tracking Progress: Stopped after error"
        )

        return

    if not tracking_active:
        return

    tracking_seconds_remaining = tracking_total_seconds
    tracking_progress.config(value=0)

    tracking_status_label.config(
        text="Tracking Progress: Market snapshot saved"
    )

    tracking_after_id = root.after(
        1000,
        update_tracking_countdown
    )

def start_tracking():
    global tracking_active
    global tracking_total_seconds
    global tracking_seconds_remaining

    selected_interval = interval_choice.get()

    tracking_total_seconds = (
        REFRESH_INTERVAL_OPTIONS[selected_interval]
    )

    tracking_seconds_remaining = tracking_total_seconds
    tracking_active = True

    start_tracking_button.config(state="disabled")
    stop_tracking_button.config(state="normal")
    interval_dropdown.config(state="disabled")

    tracking_progress.config(value=0)

    update_tracking_countdown()


def stop_tracking():
    global tracking_active
    global tracking_after_id
    global tracking_seconds_remaining

    tracking_active = False
    tracking_seconds_remaining = 0

    if tracking_after_id is not None:
        root.after_cancel(tracking_after_id)
        tracking_after_id = None

    start_tracking_button.config(state="normal")
    stop_tracking_button.config(state="disabled")
    interval_dropdown.config(state="readonly")

    tracking_progress.config(value=0)

    tracking_status_label.config(
        text="Tracking Progress: Currently Idle"
    )


root = tk.Tk()
root.title("MarketTracker")
root.geometry("950x720")


# --------------------------------------------------
# Application title and version
# --------------------------------------------------

header_frame = ttk.Frame(root)
header_frame.pack(fill="x", padx=20, pady=(15, 5))

title = ttk.Label(
    header_frame,
    text="MarketTracker",
    font=("Segoe UI", 22)
)
title.pack()

version_label = ttk.Label(
    header_frame,
    text="Ver 0.6  |  7/10/2026",
    font=("Segoe UI", 10)
)
version_label.pack(pady=(2, 5))

header_separator = ttk.Separator(
    root,
    orient="horizontal"
)
header_separator.pack(fill="x", padx=20, pady=(5, 10))


# --------------------------------------------------
# Tracking controls
# --------------------------------------------------

tracking_controls_frame = ttk.Frame(root)
tracking_controls_frame.pack(fill="x", padx=20, pady=5)

interval_label = ttk.Label(
    tracking_controls_frame,
    text="Check market every:"
)
interval_label.pack(side="left")

interval_choice = tk.StringVar(value="30 sec")

interval_dropdown = ttk.Combobox(
    tracking_controls_frame,
    textvariable=interval_choice,
    values=list(REFRESH_INTERVAL_OPTIONS.keys()),
    state="readonly",
    width=10
)
interval_dropdown.pack(side="left", padx=8)

start_tracking_button = ttk.Button(
    tracking_controls_frame,
    text="Start Tracking",
    command=start_tracking
)
start_tracking_button.pack(side="left", padx=(15, 5))

stop_tracking_button = ttk.Button(
    tracking_controls_frame,
    text="Stop Tracking",
    command=stop_tracking,
    state="disabled"
)
stop_tracking_button.pack(side="left", padx=5)

refresh_button = ttk.Button(
    tracking_controls_frame,
    text="Refresh Now",
    command=refresh_prices
)
refresh_button.pack(side="left", padx=(15, 5))


# --------------------------------------------------
# Tracking progress
# --------------------------------------------------

tracking_progress_frame = ttk.LabelFrame(
    root,
    text="Automatic Tracking"
)
tracking_progress_frame.pack(
    fill="x",
    padx=20,
    pady=(10, 5)
)

tracking_status_label = ttk.Label(
    tracking_progress_frame,
    text="Tracking Progress: Currently Idle"
)
tracking_status_label.pack(pady=(10, 5))

tracking_progress = ttk.Progressbar(
    tracking_progress_frame,
    orient="horizontal",
    length=700,
    mode="determinate",
    maximum=100,
    value=0
)
tracking_progress.pack(
    fill="x",
    padx=20,
    pady=(5, 15)
)


# --------------------------------------------------
# Planned reporting features
# --------------------------------------------------

reports_frame = ttk.LabelFrame(
    root,
    text="Reports: Planned"
)
reports_frame.pack(
    fill="x",
    padx=20,
    pady=10
)

report_format_label = ttk.Label(
    reports_frame,
    text="Report Format:"
)
report_format_label.pack(
    side="left",
    padx=(10, 5),
    pady=10
)

graph_button = ttk.Button(
    reports_frame,
    text="Graph",
    state="disabled"
)
graph_button.pack(side="left", padx=5)

spreadsheet_button = ttk.Button(
    reports_frame,
    text="Spreadsheet",
    state="disabled"
)
spreadsheet_button.pack(side="left", padx=5)

print_button = ttk.Button(
    reports_frame,
    text="Print",
    state="disabled"
)
print_button.pack(side="left", padx=(20, 5))

save_as_button = ttk.Button(
    reports_frame,
    text="Save As",
    state="disabled"
)
save_as_button.pack(side="left", padx=5)


# --------------------------------------------------
# Manual refresh status
# --------------------------------------------------

manual_status_label = ttk.Label(
    root,
    text="Manual Refresh: Ready"
)
manual_status_label.pack(pady=(5, 10))

snapshot_separator = ttk.Separator(
    root,
    orient="horizontal"
)
snapshot_separator.pack(
    fill="x",
    padx=20,
    pady=(0, 8)
)


# --------------------------------------------------
# Snapshot table
# --------------------------------------------------

snapshots_label = ttk.Label(
    root,
    text="Snapshots",
    font=("Segoe UI", 12)
)
snapshots_label.pack(pady=(0, 5))

columns = (
    "ID",
    "Symbol",
    "Timestamp",
    "Price"
)

snapshot_table = ttk.Treeview(
    root,
    columns=columns,
    show="headings"
)

for column in columns:
    snapshot_table.heading(
        column,
        text=column
    )

    snapshot_table.column(
        column,
        width=180
    )

snapshot_table.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=(0, 15)
)


load_snapshots()

root.mainloop()