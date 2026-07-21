import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox
from tkinter import ttk

from config_version import APP_VERSION, BUILD_DATE
from market_service import (
    fetch_and_save_prices,
    get_latest_market_snapshots,
)

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

def format_large_currency(value):
    if value is None:
        return "--"

    absolute_value = abs(value)

    if absolute_value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if absolute_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if absolute_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if absolute_value >= 1_000:
        return f"${value / 1_000:.2f}K"

    return f"${value:,.2f}"


def format_snapshot_time(timestamp):
    if not timestamp:
        return "--"

    parsed_timestamp = datetime.fromisoformat(timestamp)

    local_timestamp = parsed_timestamp.astimezone()

    return local_timestamp.strftime("%m/%d/%Y %I:%M:%S %p")

def load_snapshots():
    for row in snapshot_table.get_children():
        snapshot_table.delete(row)

    snapshots = get_latest_market_snapshots(limit=25)

    for snapshot in snapshots:
        percentage_change = snapshot[
            "price_change_percentage_24h"
        ]

        if percentage_change is None:
            formatted_percentage = "--"
        else:
            formatted_percentage = (
                f"{percentage_change:+.2f}%"
            )

        rank = snapshot["market_cap_rank"]

        if rank is None:
            formatted_rank = "--"
        else:
            formatted_rank = f"#{rank}"

        snapshot_table.insert(
            "",
            "end",
            values=(
                snapshot["symbol"],
                f"${snapshot['price']:,.4f}",
                formatted_percentage,
                formatted_rank,
                format_large_currency(
                    snapshot["market_cap"]
                ),
                format_large_currency(
                    snapshot["total_volume_24h"]
                ),
                format_snapshot_time(
                    snapshot["collected_at_utc"]
                ),
            ),
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
        text="Status: Running"
    )

    countdown_label.config(
        text=f"{formatted_time} Remaining"
    )

    if tracking_seconds_remaining > 0:
        tracking_seconds_remaining -= 1

        tracking_after_id = root.after(
            1000,
            update_tracking_countdown
        )

        return

    tracking_status_label.config(
        text="Status: Fetching Market Data"
    )

    countdown_label.config(
        text="Collecting latest prices..."
    )

    tracking_progress.config(value=100)
    root.update_idletasks()

    try:
        fetch_and_save_prices()
        load_snapshots()

        scan_time = datetime.now()

        last_scan_label.config(
            text=f"Last Scan: {scan_time.strftime('%I:%M:%S %p')}"
        )

        next_scan_time = (
            scan_time
            + timedelta(seconds=tracking_total_seconds)
        )

        next_scan_label.config(
            text=f"Next Scan: {next_scan_time.strftime('%I:%M:%S %p')}"
        )

    except Exception as e:
        messagebox.showerror(
            "Automatic Tracking Error",
            f"Failed to fetch market prices:\n{e}"
        )

        stop_tracking()

        tracking_status_label.config(
            text="Status: Error"
        )

        return

    if not tracking_active:
        return

    tracking_seconds_remaining = tracking_total_seconds
    tracking_progress.config(value=0)

    tracking_status_label.config(
        text="Status: Running"
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

    tracking_status_label.config(
        text="Status: Running"
    )

    countdown_label.config(
        text=(
            f"{format_tracking_time(tracking_seconds_remaining)} "
            "Remaining"
        )
    )

    next_scan_time = (
        datetime.now()
        + timedelta(seconds=tracking_total_seconds)
    )

    next_scan_label.config(
        text=f"Next Scan: {next_scan_time.strftime('%I:%M:%S %p')}"
    )

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
        text="Status: Idle"
    )

    next_scan_label.config(
        text="Next Scan: --:--:--"
    )

    countdown_label.config(
        text="Ready"
    )

root = tk.Tk()
root.title("MarketTracker")
root.geometry("1100x760")
root.minsize(950, 700)

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
    text=f"Ver {APP_VERSION}   |   {BUILD_DATE}",
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

tracking_controls_frame = ttk.LabelFrame(
    root,
    text="Tracking Controls",
)

tracking_controls_frame.pack(
    fill="x",
    padx=20,
    pady=(5, 8),
)

controls_inner_frame = ttk.Frame(
    tracking_controls_frame,
)

controls_inner_frame.pack(
    fill="x",
    padx=15,
    pady=12,
)

interval_label = ttk.Label(
    controls_inner_frame,
    text="Collection Interval:",
    font=("Segoe UI", 10, "bold"),
)

interval_label.grid(
    row=0,
    column=0,
    sticky="w",
)

interval_choice = tk.StringVar(
    value="30 sec",
)

interval_dropdown = ttk.Combobox(
    controls_inner_frame,
    textvariable=interval_choice,
    values=list(REFRESH_INTERVAL_OPTIONS.keys()),
    state="readonly",
    width=12,
)

interval_dropdown.grid(
    row=0,
    column=1,
    padx=(10, 25),
    sticky="w",
)

start_tracking_button = ttk.Button(
    controls_inner_frame,
    text="Start Tracking",
    command=start_tracking,
    width=15,
)

start_tracking_button.grid(
    row=0,
    column=2,
    padx=5,
)

stop_tracking_button = ttk.Button(
    controls_inner_frame,
    text="Stop Tracking",
    command=stop_tracking,
    state="disabled",
    width=15,
)

stop_tracking_button.grid(
    row=0,
    column=3,
    padx=5,
)

refresh_button = ttk.Button(
    controls_inner_frame,
    text="Refresh Now",
    command=refresh_prices,
    width=15,
)

refresh_button.grid(
    row=0,
    column=4,
    padx=(20, 5),
)

controls_inner_frame.columnconfigure(
    5,
    weight=1,
)


# --------------------------------------------------
# Tracking progress
# --------------------------------------------------

tracking_progress_frame = ttk.LabelFrame(
    root,
    text="Automatic Tracking",
)

tracking_progress_frame.pack(
    fill="x",
    padx=20,
    pady=(10, 5),
)

tracking_info_frame = ttk.Frame(
    tracking_progress_frame,
)

tracking_info_frame.pack(
    fill="x",
    padx=20,
    pady=(12, 8),
)

tracking_status_label = ttk.Label(
    tracking_info_frame,
    text="Status: Idle",
    font=("Segoe UI", 11, "bold"),
)

tracking_status_label.grid(
    row=0,
    column=0,
    sticky="w",
)

last_scan_label = ttk.Label(
    tracking_info_frame,
    text="Last Scan: --:--:--",
)

last_scan_label.grid(
    row=1,
    column=0,
    sticky="w",
    pady=(8, 0),
)

next_scan_label = ttk.Label(
    tracking_info_frame,
    text="Next Scan: --:--:--",
)

next_scan_label.grid(
    row=1,
    column=1,
    sticky="w",
    padx=(60, 0),
    pady=(8, 0),
)

countdown_label = ttk.Label(
    tracking_info_frame,
    text="Ready",
    font=("Segoe UI", 11, "bold"),
)

countdown_label.grid(
    row=0,
    column=1,
    sticky="e",
    padx=(60, 0),
)

tracking_info_frame.columnconfigure(
    0,
    weight=1,
)

tracking_info_frame.columnconfigure(
    1,
    weight=1,
)

tracking_progress = ttk.Progressbar(
    tracking_progress_frame,
    orient="horizontal",
    mode="determinate",
    maximum=100,
    value=0,
)

tracking_progress.pack(
    fill="x",
    padx=20,
    pady=(4, 16),
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
    "Symbol",
    "Price",
    "24h Change",
    "Rank",
    "Market Cap",
    "24h Volume",
    "Collected",
)

snapshot_table = ttk.Treeview(
    root,
    columns=columns,
    show="headings",
)

snapshot_table.heading(
    "Symbol",
    text="Symbol",
)

snapshot_table.heading(
    "Price",
    text="Price",
)

snapshot_table.heading(
    "24h Change",
    text="24h Change",
)

snapshot_table.heading(
    "Rank",
    text="Rank",
)

snapshot_table.heading(
    "Market Cap",
    text="Market Cap",
)

snapshot_table.heading(
    "24h Volume",
    text="24h Volume",
)

snapshot_table.heading(
    "Collected",
    text="Collected",
)

snapshot_table.column(
    "Symbol",
    width=80,
    anchor="center",
)

snapshot_table.column(
    "Price",
    width=130,
    anchor="e",
)

snapshot_table.column(
    "24h Change",
    width=100,
    anchor="e",
)

snapshot_table.column(
    "Rank",
    width=70,
    anchor="center",
)

snapshot_table.column(
    "Market Cap",
    width=130,
    anchor="e",
)

snapshot_table.column(
    "24h Volume",
    width=130,
    anchor="e",
)

snapshot_table.column(
    "Collected",
    width=210,
    anchor="center",
)

snapshot_table.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=(0, 15)
)


load_snapshots()

root.mainloop()