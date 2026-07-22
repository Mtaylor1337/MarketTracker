import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox
from tkinter import ttk

from config_version import APP_VERSION, BUILD_DATE
from database import create_tables
from market_service import (
    fetch_and_save_prices,
    get_latest_market_snapshots,
)
from reports import ReportsPage
from portfolio import PortfolioPage

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

session_refresh_count = 0
data_update_after_id = None


# --------------------------------------------------
# Colors
# --------------------------------------------------

COLOR_WINDOW = "#F3F6FA"
COLOR_SIDEBAR = "#16202A"
COLOR_SIDEBAR_BUTTON = "#223140"
COLOR_SIDEBAR_ACTIVE = "#2E86DE"
COLOR_SIDEBAR_INACTIVE_TEXT = "#859DB6"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#B125A6"
COLOR_TEXT = "#1F2933"
COLOR_MUTED = "#66788A"
COLOR_SUCCESS = "#1EB573"
COLOR_DANGER = "#C62626"
COLOR_TABLE_HEADER = "#2F7AC4"


# --------------------------------------------------
# Manual refresh
# --------------------------------------------------

def enable_refresh():
    refresh_button.config(state="normal")
    manual_status_label.config(
        text="Manual Refresh: Ready",
        foreground=COLOR_MUTED,
    )


def countdown_refresh(seconds_remaining):
    if seconds_remaining > 0:
        manual_status_label.config(
            text=f"Manual Refresh: Ready in {seconds_remaining} sec",
            foreground=COLOR_MUTED,
        )

        root.after(
            1000,
            countdown_refresh,
            seconds_remaining - 1,
        )
    else:
        enable_refresh()


# --------------------------------------------------
# Formatting helpers
# --------------------------------------------------

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


def format_tracking_time(total_seconds):
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def _build_snapshot_table_rows(snapshots, newer_than_id=None):
    rows = []

    for snapshot in snapshots:
        percentage_change = snapshot["price_change_percentage_24h"]

        if percentage_change is None:
            formatted_percentage = "--"
            row_tag = "neutral"
        else:
            formatted_percentage = f"{percentage_change:+.2f}%"

            if percentage_change > 0:
                row_tag = "positive"
            elif percentage_change < 0:
                row_tag = "negative"
            else:
                row_tag = "neutral"

        rank = snapshot["market_cap_rank"]

        if rank is None:
            formatted_rank = "--"
        else:
            formatted_rank = f"#{rank}"

        row_tags = [row_tag]

        if (
            newer_than_id is not None
            and snapshot["snapshot_id"] > newer_than_id
        ):
            row_tags.append("new")

        rows.append(
            {
                "values": (
                    snapshot["snapshot_id"],
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
                "tags": tuple(row_tags),
            }
        )

    return rows


class MarketSnapshotsPage(tk.Frame):
    def __init__(self, parent, colors=None):
        self.colors = {
            "window": COLOR_WINDOW,
            "card": COLOR_CARD,
            "border": COLOR_BORDER,
            "text": COLOR_TEXT,
            "muted": COLOR_MUTED,
            "primary": COLOR_SIDEBAR_ACTIVE,
            "success": COLOR_SUCCESS,
            "danger": COLOR_DANGER,
            "table_header": COLOR_TABLE_HEADER,
        }
        if colors:
            self.colors.update(colors)

        super().__init__(parent, background=self.colors["window"])

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._configure_styles()
        self._build_header()
        self._build_filters()
        self._build_table()
        self.load_snapshots()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.configure(
            "Snapshots.Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
            foreground="#ffffff",
            background=self.colors["primary"],
        )
        style.map(
            "Snapshots.Primary.TButton",
            background=[("active", "#1d4ed8")],
        )
        style.configure(
            "Snapshots.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
        )
        style.configure(
            "Snapshots.TCombobox",
            padding=6,
        )
        style.configure(
            "Snapshots.Treeview",
            background=self.colors["card"],
            fieldbackground=self.colors["card"],
            foreground=self.colors["text"],
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Snapshots.Treeview.Heading",
            background=self.colors["table_header"],
            foreground=self.colors["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(8, 8),
        )
        style.map(
            "Snapshots.Treeview.Heading",
            background=[("active", "#DCE5ED")],
        )

    def _build_header(self):
        header_frame = tk.Frame(
            self,
            background=self.colors["window"],
        )
        header_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=28,
            pady=(24, 16),
        )
        header_frame.columnconfigure(0, weight=1)

        tk.Label(
            header_frame,
            text="Market Snapshots",
            background=self.colors["window"],
            foreground=self.colors["text"],
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            header_frame,
            text="Review the latest market snapshot records collected by the tracker",
            background=self.colors["window"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.record_count_label = tk.Label(
            header_frame,
            text="0 latest records",
            background=self.colors["window"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        )
        self.record_count_label.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
        )

    def _build_filters(self):
        filters_card = tk.Frame(
            self,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        filters_card.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 14),
        )
        filters_card.columnconfigure(1, weight=1)
        filters_card.columnconfigure(3, weight=0)
        filters_card.columnconfigure(5, weight=1)

        tk.Label(
            filters_card,
            text="Search Symbol",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky="w", padx=(18, 8), pady=(16, 8))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            filters_card,
            textvariable=self.search_var,
            width=20,
        )
        self.search_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 18),
            pady=(16, 8),
        )

        tk.Label(
            filters_card,
            text="24h Change",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=(16, 8))

        self.change_filter_var = tk.StringVar(value="All")
        self.change_filter_dropdown = ttk.Combobox(
            filters_card,
            textvariable=self.change_filter_var,
            values=["All", "Positive", "Negative", "Neutral"],
            state="readonly",
            width=14,
            style="Snapshots.TCombobox",
        )
        self.change_filter_dropdown.grid(
            row=0,
            column=3,
            sticky="w",
            padx=(0, 18),
            pady=(16, 8),
        )

        tk.Label(
            filters_card,
            text="Sort",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", padx=(18, 8), pady=(8, 16))

        self.sort_var = tk.StringVar(value="Newest ↓")
        self.sort_dropdown = ttk.Combobox(
            filters_card,
            textvariable=self.sort_var,
            values=[
                "Newest ↓",
                "Newest ↑",
                "Oldest ↓",
                "Oldest ↑",
                "Highest Market Cap ↓",
                "Highest Market Cap ↑",
                "Lowest Market Cap ↓",
                "Lowest Market Cap ↑",
                "Largest 24h Volume ↓",
                "Largest 24h Volume ↑",
                "Biggest 24h Change ↓",
                "Biggest 24h Change ↑",
            ],
            state="readonly",
            width=26,
            style="Snapshots.TCombobox",
        )
        self.sort_dropdown.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 18),
            pady=(8, 16),
        )

        self.apply_filters_button = ttk.Button(
            filters_card,
            text="Apply Filters",
            command=self.apply_filters,
            style="Snapshots.Primary.TButton",
        )
        self.apply_filters_button.grid(
            row=1,
            column=2,
            padx=4,
            pady=(8, 16),
        )

        self.reset_filters_button = ttk.Button(
            filters_card,
            text="Reset",
            command=self.reset_filters,
            style="Snapshots.TButton",
        )
        self.reset_filters_button.grid(
            row=1,
            column=3,
            padx=(4, 18),
            pady=(8, 16),
        )

        self.current_sort_label = tk.Label(
            filters_card,
            text="Current Sort: Newest • ↓",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9, "bold"),
        )
        self.current_sort_label.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="w",
            padx=(18, 18),
            pady=(0, 14),
        )

    def _build_table(self):
        table_card = tk.Frame(
            self,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        table_card.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(0, 24),
        )
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(1, weight=1)

        columns = (
            "ID",
            "Symbol",
            "Price",
            "24h Change",
            "Rank",
            "Market Cap",
            "24h Volume",
            "Collected",
        )

        self.snapshot_table = ttk.Treeview(
            table_card,
            columns=columns,
            show="headings",
            style="Snapshots.Treeview",
        )

        self.snapshot_scrollbar = ttk.Scrollbar(
            table_card,
            orient="vertical",
            command=self.snapshot_table.yview,
        )
        self.snapshot_table.configure(
            yscrollcommand=self.snapshot_scrollbar.set,
        )

        self._header_sort_map = {
            "ID": "Newest",
            "Symbol": "Newest",
            "Price": "Newest",
            "24h Change": "Biggest 24h Change",
            "Rank": "Newest",
            "Market Cap": "Highest Market Cap",
            "24h Volume": "Largest 24h Volume",
            "Collected": "Newest",
        }

        for column_name in columns:
            self.snapshot_table.heading(
                column_name,
                text=column_name,
                command=lambda col=column_name: self._handle_header_click(col),
            )

        self.snapshot_table.column(
            "ID",
            width=55,
            minwidth=45,
            anchor="center",
            stretch=False,
        )
        self.snapshot_table.column(
            "Symbol",
            width=75,
            minwidth=65,
            anchor="center",
        )
        self.snapshot_table.column(
            "Price",
            width=115,
            minwidth=100,
            anchor="e",
        )
        self.snapshot_table.column(
            "24h Change",
            width=95,
            minwidth=85,
            anchor="e",
        )
        self.snapshot_table.column(
            "Rank",
            width=60,
            minwidth=55,
            anchor="center",
        )
        self.snapshot_table.column(
            "Market Cap",
            width=115,
            minwidth=100,
            anchor="e",
        )
        self.snapshot_table.column(
            "24h Volume",
            width=115,
            minwidth=100,
            anchor="e",
        )
        self.snapshot_table.column(
            "Collected",
            width=190,
            minwidth=175,
            anchor="center",
        )

        self.snapshot_table.tag_configure(
            "positive",
            foreground=self.colors["success"],
        )
        self.snapshot_table.tag_configure(
            "negative",
            foreground=self.colors["danger"],
        )
        self.snapshot_table.tag_configure(
            "neutral",
            foreground=self.colors["text"],
        )
        self.snapshot_table.tag_configure(
            "new",
            background="#DFF3E8",
        )

        self.empty_state_label = tk.Label(
            table_card,
            text="No matching market snapshots found",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 11, "bold"),
        )
        self.empty_state_label.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="n",
            padx=18,
            pady=(80, 0),
        )
        self.empty_state_label.grid_remove()

        self.snapshot_table.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(18, 0),
            pady=(0, 18),
        )
        self.snapshot_scrollbar.grid(
            row=1,
            column=1,
            sticky="ns",
            padx=(0, 18),
            pady=(0, 18),
        )

    def _handle_header_click(self, column_name):
        selected_sort_mode = self._header_sort_map.get(column_name, "Newest")
        current_sort_text = self.sort_var.get()
        current_sort_mode = current_sort_text.replace(" ↑", "").replace(" ↓", "")

        if current_sort_mode == selected_sort_mode:
            if current_sort_text.endswith("↓"):
                self.sort_var.set(f"{selected_sort_mode} ↑")
            else:
                self.sort_var.set(f"{selected_sort_mode} ↓")
        else:
            self.sort_var.set(f"{selected_sort_mode} ↓")

        self.load_snapshots()

    def _update_header_indicators(self):
        active_sort_text = self.sort_var.get()
        active_sort_mode = active_sort_text.replace(" ↑", "").replace(" ↓", "")
        direction_marker = "↓" if active_sort_text.endswith("↓") else "↑"

        active_sort_label = None
        if active_sort_mode in {"Newest", "Oldest"}:
            active_sort_label = "ID"
        elif active_sort_mode in {"Highest Market Cap", "Lowest Market Cap"}:
            active_sort_label = "Market Cap"
        elif active_sort_mode == "Largest 24h Volume":
            active_sort_label = "24h Volume"
        elif active_sort_mode == "Biggest 24h Change":
            active_sort_label = "24h Change"

        for column_name in self._header_sort_map:
            heading_text = column_name
            if column_name == active_sort_label:
                heading_text = f"{column_name} {direction_marker}"
            self.snapshot_table.heading(
                column_name,
                text=heading_text,
            )

        self.current_sort_label.config(
            text=f"Current Sort: {active_sort_mode} • {direction_marker}"
        )

    def _get_filtered_snapshots(self, snapshots):
        search_text = self.search_var.get().strip().lower()
        selected_change = self.change_filter_var.get()

        filtered_snapshots = []

        for snapshot in snapshots:
            symbol = (snapshot["symbol"] or "").lower()
            name = (snapshot["name"] or "").lower()

            if search_text and search_text not in symbol and search_text not in name:
                continue

            percentage_change = snapshot["price_change_percentage_24h"]
            if selected_change == "Positive":
                if percentage_change is None or percentage_change <= 0:
                    continue
            elif selected_change == "Negative":
                if percentage_change is None or percentage_change >= 0:
                    continue
            elif selected_change == "Neutral":
                if percentage_change is None or percentage_change != 0:
                    continue

            filtered_snapshots.append(snapshot)

        return self._sort_snapshots(filtered_snapshots)

    def _sort_snapshots(self, snapshots):
        sort_text = self.sort_var.get()
        sort_mode = sort_text.replace(" ↑", "").replace(" ↓", "")
        reverse = sort_text.endswith("↓")

        if sort_mode == "Oldest":
            return sorted(
                snapshots,
                key=lambda item: (
                    item["snapshot_id"]
                    if item["snapshot_id"] is not None
                    else 0
                ),
                reverse=reverse,
            )

        if sort_mode == "Highest Market Cap":
            return sorted(
                snapshots,
                key=lambda item: (
                    item["market_cap"]
                    if item["market_cap"] is not None
                    else -1
                ),
                reverse=reverse,
            )

        if sort_mode == "Lowest Market Cap":
            return sorted(
                snapshots,
                key=lambda item: (
                    item["market_cap"]
                    if item["market_cap"] is not None
                    else float("inf")
                ),
                reverse=reverse,
            )

        if sort_mode == "Largest 24h Volume":
            return sorted(
                snapshots,
                key=lambda item: (
                    item["total_volume_24h"]
                    if item["total_volume_24h"] is not None
                    else -1
                ),
                reverse=reverse,
            )

        if sort_mode == "Biggest 24h Change":
            return sorted(
                snapshots,
                key=lambda item: (
                    item["price_change_percentage_24h"]
                    if item["price_change_percentage_24h"] is not None
                    else float("-inf")
                ),
                reverse=reverse,
            )

        return sorted(
            snapshots,
            key=lambda item: (
                item["snapshot_id"]
                if item["snapshot_id"] is not None
                else 0
            ),
            reverse=reverse,
        )

    def apply_filters(self):
        self.load_snapshots()

    def reset_filters(self):
        self.search_var.set("")
        self.change_filter_var.set("All")
        self.sort_var.set("Newest ↓")
        self.load_snapshots()

    def load_snapshots(self):
        snapshots = get_latest_market_snapshots(limit=200)
        filtered_snapshots = self._get_filtered_snapshots(snapshots)
        snapshot_rows = _build_snapshot_table_rows(filtered_snapshots)

        for row in self.snapshot_table.get_children():
            self.snapshot_table.delete(row)

        if not snapshot_rows:
            self.snapshot_table.grid_remove()
            self.snapshot_scrollbar.grid_remove()
            self.empty_state_label.grid()
            self.record_count_label.config(text="0 matching records")
            return

        self.empty_state_label.grid_remove()
        self.snapshot_table.grid()
        self.snapshot_scrollbar.grid()

        for row in snapshot_rows:
            self.snapshot_table.insert(
                "",
                "end",
                values=row["values"],
                tags=row["tags"],
            )

        self.record_count_label.config(
            text=f"{len(snapshot_rows)} matching records"
        )
        self._update_header_indicators()


# --------------------------------------------------
# Snapshot table
# --------------------------------------------------

def get_latest_displayed_snapshot_id():
    rows = snapshot_table.get_children()

    if not rows:
        return 0

    first_row_values = snapshot_table.item(
        rows[0],
        "values",
    )

    if not first_row_values:
        return 0

    return int(first_row_values[0])


def clear_new_row_highlights():
    for row in snapshot_table.get_children():
        current_tags = snapshot_table.item(
            row,
            "tags",
        )

        updated_tags = tuple(
            tag
            for tag in current_tags
            if tag != "new"
        )

        snapshot_table.item(
            row,
            tags=updated_tags,
        )


def reset_data_update_indicator():
    global data_update_after_id

    data_update_indicator.config(
        foreground=COLOR_MUTED,
    )

    data_update_after_id = None
    clear_new_row_highlights()


def mark_data_updated():
    global session_refresh_count
    global data_update_after_id

    session_refresh_count += 1

    update_time = datetime.now().strftime(
        "%I:%M:%S %p"
    )

    data_update_indicator.config(
        text=(
            f"Data Updated: {update_time}  •  "
            f"Refresh #{session_refresh_count}"
        ),
        foreground=COLOR_SUCCESS,
    )

    if data_update_after_id is not None:
        root.after_cancel(data_update_after_id)

    data_update_after_id = root.after(
        2500,
        reset_data_update_indicator,
    )


def load_snapshots(newer_than_id=None):
    snapshots = get_latest_market_snapshots(limit=25)
    snapshot_rows = _build_snapshot_table_rows(
        snapshots,
        newer_than_id=newer_than_id,
    )

    for row in snapshot_table.get_children():
        snapshot_table.delete(row)

    for row in snapshot_rows:
        snapshot_table.insert(
            "",
            "end",
            values=row["values"],
            tags=row["tags"],
        )

    snapshot_count_label.config(
        text=f"{len(snapshots)} latest records"
    )

    if "snapshots_page" in globals():
        snapshots_page.load_snapshots()


def refresh_prices():
    refresh_button.config(state="disabled")

    manual_status_label.config(
        text="Manual Refresh: Running...",
        foreground=COLOR_SIDEBAR_ACTIVE,
    )

    root.update_idletasks()

    latest_snapshot_id = (
        get_latest_displayed_snapshot_id()
    )

    try:
        fetch_and_save_prices()

        load_snapshots(
            newer_than_id=latest_snapshot_id
        )

        scan_time = datetime.now()

        last_scan_label.config(
            text=scan_time.strftime("%I:%M:%S %p")
        )

        mark_data_updated()

        manual_status_label.config(
            text=(
                "Manual Refresh: Cooling down for "
                f"{REFRESH_COOLDOWN_SECONDS} sec"
            ),
            foreground=COLOR_SUCCESS,
        )

    except Exception as error:
        messagebox.showerror(
            "Refresh Error",
            f"Failed to refresh prices:\n{error}",
        )

        manual_status_label.config(
            text="Manual Refresh: Error",
            foreground=COLOR_DANGER,
        )

    finally:
        countdown_refresh(
            REFRESH_COOLDOWN_SECONDS
        )


# --------------------------------------------------
# Automatic tracking
# --------------------------------------------------

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
        text="Running",
        foreground=COLOR_SUCCESS,
    )

    countdown_label.config(
        text=f"{formatted_time} Remaining"
    )

    if tracking_seconds_remaining > 0:
        tracking_seconds_remaining -= 1

        tracking_after_id = root.after(
            1000,
            update_tracking_countdown,
        )

        return

    tracking_status_label.config(
        text="Fetching Market Data",
        foreground=COLOR_SIDEBAR_ACTIVE,
    )

    countdown_label.config(
        text="Collecting latest prices..."
    )

    tracking_progress.config(value=100)
    root.update_idletasks()

    latest_snapshot_id = (
        get_latest_displayed_snapshot_id()
    )

    try:
        fetch_and_save_prices()

        load_snapshots(
            newer_than_id=latest_snapshot_id
        )

        mark_data_updated()

        scan_time = datetime.now()

        last_scan_label.config(
            text=scan_time.strftime("%I:%M:%S %p")
        )

        next_scan_time = (
            scan_time
            + timedelta(seconds=tracking_total_seconds)
        )

        next_scan_label.config(
            text=next_scan_time.strftime("%I:%M:%S %p")
        )

    except Exception as error:
        messagebox.showerror(
            "Automatic Tracking Error",
            f"Failed to fetch market prices:\n{error}",
        )

        stop_tracking()

        tracking_status_label.config(
            text="Error",
            foreground=COLOR_DANGER,
        )

        return

    if not tracking_active:
        return

    tracking_seconds_remaining = tracking_total_seconds
    tracking_progress.config(value=0)

    tracking_status_label.config(
        text="Running",
        foreground=COLOR_SUCCESS,
    )

    tracking_after_id = root.after(
        1000,
        update_tracking_countdown,
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
        text="Running",
        foreground=COLOR_SUCCESS,
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
        text=next_scan_time.strftime("%I:%M:%S %p")
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
        text="Idle",
        foreground=COLOR_MUTED,
    )

    next_scan_label.config(text="--:--:--")
    countdown_label.config(text="Ready")


# --------------------------------------------------
# Main window
# --------------------------------------------------

def set_active_navigation(active_button):
    navigation_buttons = (
        dashboard_nav_button,
        snapshots_nav_button,
        reports_nav_button,
        portfolio_nav_button,
    )

    for button in navigation_buttons:
        button.config(
            background=COLOR_SIDEBAR_BUTTON,
            foreground=COLOR_SIDEBAR_INACTIVE_TEXT,
            activebackground=COLOR_SIDEBAR_BUTTON,
            activeforeground="white",
            font=("Segoe UI", 10),
        )

    active_button.config(
        background=COLOR_SIDEBAR_ACTIVE,
        foreground="white",
        activebackground=COLOR_SIDEBAR_ACTIVE,
        activeforeground="white",
        font=("Segoe UI", 10, "bold"),
    )


def show_dashboard_page():
    reports_page.grid_remove()
    snapshots_page.grid_remove()
    portfolio_page.grid_remove()
    main_frame.grid()
    set_active_navigation(dashboard_nav_button)


def show_reports_page():
    main_frame.grid_remove()
    snapshots_page.grid_remove()
    portfolio_page.grid_remove()
    reports_page.load_assets()
    reports_page.grid()
    set_active_navigation(reports_nav_button)


def show_snapshots_page():
    main_frame.grid_remove()
    reports_page.grid_remove()
    portfolio_page.grid_remove()
    snapshots_page.load_snapshots()
    snapshots_page.grid()
    set_active_navigation(snapshots_nav_button)


create_tables()


def show_portfolio_page():
    main_frame.grid_remove()
    reports_page.grid_remove()
    snapshots_page.grid_remove()
    portfolio_page.load_summary()
    portfolio_page.grid()
    set_active_navigation(portfolio_nav_button)

root = tk.Tk()
root.title(f"MarketTracker {APP_VERSION}")
root.geometry("1280x780")
root.minsize(1050, 700)
root.configure(background=COLOR_WINDOW)

root.columnconfigure(0, weight=0)
root.columnconfigure(1, weight=1)
root.rowconfigure(0, weight=1)


# --------------------------------------------------
# ttk styling
# --------------------------------------------------

style = ttk.Style(root)

try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure(
    "Dashboard.TButton",
    font=("Segoe UI", 10, "bold"),
    padding=(14, 9),
)

style.configure(
    "Primary.TButton",
    font=("Segoe UI", 10, "bold"),
    padding=(14, 9),
    foreground="#FFFFFF",
    background=COLOR_SIDEBAR_ACTIVE,
)

style.map(
    "Primary.TButton",
    background=[
        ("active", "#2375C5"),
        ("disabled", "#A9B8C5"),
    ],
)

style.configure(
    "Danger.TButton",
    font=("Segoe UI", 10, "bold"),
    padding=(14, 9),
    foreground="#FFFFFF",
    background=COLOR_DANGER,
)

style.map(
    "Danger.TButton",
    background=[
        ("active", "#AD3E3E"),
        ("disabled", "#C8CDD2"),
    ],
)

style.configure(
    "Dashboard.TCombobox",
    padding=6,
)

style.configure(
    "Dashboard.Horizontal.TProgressbar",
    troughcolor="#E4EAF0",
    background=COLOR_SIDEBAR_ACTIVE,
    bordercolor="#E4EAF0",
    lightcolor=COLOR_SIDEBAR_ACTIVE,
    darkcolor=COLOR_SIDEBAR_ACTIVE,
    thickness=12,
)

style.configure(
    "Dashboard.Treeview",
    background=COLOR_CARD,
    fieldbackground=COLOR_CARD,
    foreground=COLOR_TEXT,
    rowheight=30,
    borderwidth=0,
    font=("Segoe UI", 9),
)

style.configure(
    "Dashboard.Treeview.Heading",
    background=COLOR_TABLE_HEADER,
    foreground=COLOR_TEXT,
    font=("Segoe UI", 9, "bold"),
    relief="flat",
    padding=(8, 8),
)

style.map(
    "Dashboard.Treeview.Heading",
    background=[("active", "#DCE5ED")],
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

sidebar = tk.Frame(
    root,
    background=COLOR_SIDEBAR,
    width=215,
)

sidebar.grid(
    row=0,
    column=0,
    sticky="nsew",
)

sidebar.grid_propagate(False)
sidebar.columnconfigure(0, weight=1)
sidebar.rowconfigure(8, weight=1)

brand_label = tk.Label(
    sidebar,
    text="MARKET\nTRACKER",
    background=COLOR_SIDEBAR,
    foreground="#FFFFFF",
    font=("Segoe UI", 20, "bold"),
    justify="left",
)

brand_label.grid(
    row=0,
    column=0,
    sticky="w",
    padx=24,
    pady=(28, 30),
)

dashboard_nav_button = tk.Button(
    sidebar,
    text=" Dashboard",
    command=show_dashboard_page,
    anchor="w",
    background=COLOR_SIDEBAR_ACTIVE,
    foreground="white",
    activebackground=COLOR_SIDEBAR_ACTIVE,
    activeforeground="white",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10, "bold"),
    padx=18,
    pady=12,
)
dashboard_nav_button.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=12,
    pady=3,
)

dashboard_nav_button.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=12,
    pady=3,
)

snapshots_nav_button = tk.Button(
    sidebar,
    text="  Market Snapshots",
    command=show_snapshots_page,
    anchor="w",
    background=COLOR_SIDEBAR_BUTTON,
    foreground="#DCE4EC",
    activebackground=COLOR_SIDEBAR_BUTTON,
    activeforeground="#FFFFFF",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10),
    padx=18,
    pady=12,
)

snapshots_nav_button.grid(
    row=2,
    column=0,
    sticky="ew",
    padx=12,
    pady=3,
)

reports_nav_button = tk.Button(
    sidebar,
    text=" Reports",
    command=show_reports_page,
    anchor="w",
    background=COLOR_SIDEBAR_BUTTON,
    foreground=COLOR_SIDEBAR_INACTIVE_TEXT,
    activebackground=COLOR_SIDEBAR_BUTTON,
    activeforeground=COLOR_TEXT,
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10),
    padx=18,
    pady=12,
)
reports_nav_button.grid(
    row=3,
    column=0,
    sticky="ew",
    padx=12,
    pady=3,
)

reports_nav_button.grid(
    row=3,
    column=0,
    sticky="ew",
    padx=12,
    pady=3,
)

portfolio_nav_button = tk.Button(
    sidebar,
    text="  Portfolio",
    command=show_portfolio_page,
    anchor="w",
    background=COLOR_SIDEBAR_BUTTON,
    foreground=COLOR_SIDEBAR_INACTIVE_TEXT,
    activebackground=COLOR_SIDEBAR_BUTTON,
    activeforeground="white",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10),
    padx=18,
    pady=12,
)

portfolio_nav_button.grid(
    row=4,
    column=0,
    sticky="ew",
    padx=12,
    pady=3,
)

alerts_nav_button = tk.Button(
    sidebar,
    text="  Alerts  (Planned)",
    anchor="w",
    background=COLOR_SIDEBAR,
    foreground="#758493",
    relief="flat",
    borderwidth=0,
    font=("Segoe UI", 10),
    padx=18,
    pady=12,
    state="disabled",
    disabledforeground="#758493",
)

alerts_nav_button.grid(
    row=5,
    column=0,
    sticky="ew",
    padx=12,
    pady=3,
)

sidebar_version_label = tk.Label(
    sidebar,
    text=f"Version {APP_VERSION}\nBuild {BUILD_DATE}",
    background=COLOR_SIDEBAR,
    foreground="#81909E",
    font=("Segoe UI", 9),
    justify="left",
)

sidebar_version_label.grid(
    row=9,
    column=0,
    sticky="sw",
    padx=24,
    pady=24,
)


# --------------------------------------------------
# Main dashboard area
# --------------------------------------------------

main_frame = tk.Frame(
    root,
    background=COLOR_WINDOW,
)

main_frame.grid(
    row=0,
    column=1,
    sticky="nsew",
)

main_frame.columnconfigure(0, weight=1)
main_frame.rowconfigure(3, weight=1)

reports_page = ReportsPage(
    root,
    colors={
        "window": COLOR_WINDOW,
        "card": COLOR_CARD,
        "border": COLOR_BORDER,
        "text": COLOR_TEXT,
        "muted": COLOR_MUTED,
        "primary": COLOR_SIDEBAR_ACTIVE,
        "success": COLOR_SUCCESS,
        "danger": COLOR_DANGER,
        "table_header": COLOR_TABLE_HEADER,
    },
)
reports_page.grid(
    row=0,
    column=1,
    sticky="nsew",
)
reports_page.grid_remove()

snapshots_page = MarketSnapshotsPage(
    root,
    colors={
        "window": COLOR_WINDOW,
        "card": COLOR_CARD,
        "border": COLOR_BORDER,
        "text": COLOR_TEXT,
        "muted": COLOR_MUTED,
        "primary": COLOR_SIDEBAR_ACTIVE,
        "success": COLOR_SUCCESS,
        "danger": COLOR_DANGER,
        "table_header": COLOR_TABLE_HEADER,
    },
)
snapshots_page.grid(
    row=0,
    column=1,
    sticky="nsew",
)
snapshots_page.grid_remove()

portfolio_page = PortfolioPage(
    root,
    colors={
        "window": COLOR_WINDOW,
        "card": COLOR_CARD,
        "border": COLOR_BORDER,
        "text": COLOR_TEXT,
        "muted": COLOR_MUTED,
        "primary": COLOR_SIDEBAR_ACTIVE,
        "success": COLOR_SUCCESS,
        "danger": COLOR_DANGER,
        "table_header": COLOR_TABLE_HEADER,
    },
)
portfolio_page.grid(
    row=0,
    column=1,
    sticky="nsew",
)
portfolio_page.grid_remove()

# --------------------------------------------------
# Dashboard header
# --------------------------------------------------

header_frame = tk.Frame(
    main_frame,
    background=COLOR_WINDOW,
)

header_frame.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=28,
    pady=(24, 16),
)

header_frame.columnconfigure(0, weight=1)

title_label = tk.Label(
    header_frame,
    text="Market Dashboard",
    background=COLOR_WINDOW,
    foreground=COLOR_TEXT,
    font=("Segoe UI", 22, "bold"),
)

title_label.grid(
    row=0,
    column=0,
    sticky="w",
)

subtitle_label = tk.Label(
    header_frame,
    text="Monitor cryptocurrency prices and collection activity",
    background=COLOR_WINDOW,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 10),
)

subtitle_label.grid(
    row=1,
    column=0,
    sticky="w",
    pady=(3, 0),
)

manual_status_label = ttk.Label(
    header_frame,
    text="Manual Refresh: Ready",
    background=COLOR_WINDOW,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 9),
)

manual_status_label.grid(
    row=0,
    column=1,
    rowspan=2,
    sticky="e",
)


# --------------------------------------------------
# Tracking control card
# --------------------------------------------------

controls_card = tk.Frame(
    main_frame,
    background=COLOR_CARD,
    highlightbackground=COLOR_BORDER,
    highlightthickness=1,
)

controls_card.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=28,
    pady=(0, 14),
)

controls_card.columnconfigure(0, weight=1)

controls_title = tk.Label(
    controls_card,
    text="Tracking Controls",
    background=COLOR_CARD,
    foreground=COLOR_TEXT,
    font=("Segoe UI", 12, "bold"),
)

controls_title.grid(
    row=0,
    column=0,
    columnspan=6,
    sticky="w",
    padx=18,
    pady=(15, 12),
)

interval_label = tk.Label(
    controls_card,
    text="Collection Interval",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 9),
)

interval_label.grid(
    row=1,
    column=0,
    sticky="w",
    padx=(18, 8),
    pady=(0, 16),
)

interval_choice = tk.StringVar(value="30 sec")

interval_dropdown = ttk.Combobox(
    controls_card,
    textvariable=interval_choice,
    values=list(REFRESH_INTERVAL_OPTIONS.keys()),
    state="readonly",
    width=11,
    style="Dashboard.TCombobox",
)

interval_dropdown.grid(
    row=1,
    column=1,
    sticky="w",
    padx=(0, 18),
    pady=(0, 16),
)

start_tracking_button = ttk.Button(
    controls_card,
    text="Start Tracking",
    command=start_tracking,
    style="Primary.TButton",
)

start_tracking_button.grid(
    row=1,
    column=2,
    padx=5,
    pady=(0, 16),
)

stop_tracking_button = ttk.Button(
    controls_card,
    text="Stop Tracking",
    command=stop_tracking,
    state="disabled",
    style="Danger.TButton",
)

stop_tracking_button.grid(
    row=1,
    column=3,
    padx=5,
    pady=(0, 16),
)

refresh_button = ttk.Button(
    controls_card,
    text="Refresh Now",
    command=refresh_prices,
    style="Dashboard.TButton",
)

refresh_button.grid(
    row=1,
    column=4,
    padx=(18, 18),
    pady=(0, 16),
)


# --------------------------------------------------
# Automatic tracking status card
# --------------------------------------------------

tracking_card = tk.Frame(
    main_frame,
    background=COLOR_CARD,
    highlightbackground=COLOR_BORDER,
    highlightthickness=1,
)

tracking_card.grid(
    row=2,
    column=0,
    sticky="ew",
    padx=28,
    pady=(0, 14),
)

tracking_card.columnconfigure(0, weight=1)
tracking_card.columnconfigure(1, weight=1)
tracking_card.columnconfigure(2, weight=1)

tracking_card_title = tk.Label(
    tracking_card,
    text="Automatic Tracking",
    background=COLOR_CARD,
    foreground=COLOR_TEXT,
    font=("Segoe UI", 12, "bold"),
)

tracking_card_title.grid(
    row=0,
    column=0,
    columnspan=3,
    sticky="w",
    padx=18,
    pady=(14, 12),
)

status_caption = tk.Label(
    tracking_card,
    text="STATUS",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 8, "bold"),
)

status_caption.grid(
    row=1,
    column=0,
    sticky="w",
    padx=18,
)

tracking_status_label = tk.Label(
    tracking_card,
    text="Idle",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 11, "bold"),
)

tracking_status_label.grid(
    row=2,
    column=0,
    sticky="w",
    padx=18,
    pady=(3, 12),
)

last_scan_caption = tk.Label(
    tracking_card,
    text="LAST SCAN",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 8, "bold"),
)

last_scan_caption.grid(
    row=1,
    column=1,
    sticky="w",
)

last_scan_label = tk.Label(
    tracking_card,
    text="--:--:--",
    background=COLOR_CARD,
    foreground=COLOR_TEXT,
    font=("Segoe UI", 11, "bold"),
)

last_scan_label.grid(
    row=2,
    column=1,
    sticky="w",
    pady=(3, 12),
)

next_scan_caption = tk.Label(
    tracking_card,
    text="NEXT SCAN",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 8, "bold"),
)

next_scan_caption.grid(
    row=1,
    column=2,
    sticky="w",
)

next_scan_label = tk.Label(
    tracking_card,
    text="--:--:--",
    background=COLOR_CARD,
    foreground=COLOR_TEXT,
    font=("Segoe UI", 11, "bold"),
)

next_scan_label.grid(
    row=2,
    column=2,
    sticky="w",
    padx=(0, 18),
    pady=(3, 12),
)

countdown_label = tk.Label(
    tracking_card,
    text="Ready",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 9, "bold"),
)

countdown_label.grid(
    row=3,
    column=0,
    columnspan=3,
    sticky="e",
    padx=18,
    pady=(0, 5),
)

tracking_progress = ttk.Progressbar(
    tracking_card,
    orient="horizontal",
    mode="determinate",
    maximum=100,
    value=0,
    style="Dashboard.Horizontal.TProgressbar",
)

tracking_progress.grid(
    row=4,
    column=0,
    columnspan=3,
    sticky="ew",
    padx=18,
    pady=(0, 16),
)


# --------------------------------------------------
# Snapshot table card
# --------------------------------------------------

snapshot_card = tk.Frame(
    main_frame,
    background=COLOR_CARD,
    highlightbackground=COLOR_BORDER,
    highlightthickness=1,
)

snapshot_card.grid(
    row=3,
    column=0,
    sticky="nsew",
    padx=28,
    pady=(0, 24),
)

snapshot_card.columnconfigure(0, weight=1)
snapshot_card.rowconfigure(1, weight=1)

snapshot_header = tk.Frame(
    snapshot_card,
    background=COLOR_CARD,
)

snapshot_header.grid(
    row=0,
    column=0,
    columnspan=2,
    sticky="ew",
    padx=18,
    pady=(14, 12),
)

snapshot_header.columnconfigure(0, weight=1)

snapshots_label = tk.Label(
    snapshot_header,
    text="Latest Market Snapshots",
    background=COLOR_CARD,
    foreground=COLOR_TEXT,
    font=("Segoe UI", 12, "bold"),
)

snapshots_label.grid(
    row=0,
    column=0,
    sticky="w",
)

data_update_indicator = tk.Label(
    snapshot_header,
    text="Waiting for next data refresh",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 9, "bold"),
)

data_update_indicator.grid(
    row=0,
    column=1,
    sticky="e",
    padx=(15, 20),
)

snapshot_count_label = tk.Label(
    snapshot_header,
    text="0 latest records",
    background=COLOR_CARD,
    foreground=COLOR_MUTED,
    font=("Segoe UI", 9),
)

snapshot_count_label.grid(
    row=0,
    column=2,
    sticky="e",
)

columns = (
    "ID",
    "Symbol",
    "Price",
    "24h Change",
    "Rank",
    "Market Cap",
    "24h Volume",
    "Collected",
)

snapshot_table = ttk.Treeview(
    snapshot_card,
    columns=columns,
    show="headings",
    style="Dashboard.Treeview",
)

snapshot_scrollbar = ttk.Scrollbar(
    snapshot_card,
    orient="vertical",
    command=snapshot_table.yview,
)

snapshot_table.configure(
    yscrollcommand=snapshot_scrollbar.set
)

snapshot_table.heading("ID", text="ID")
snapshot_table.heading("Symbol", text="Symbol")
snapshot_table.heading("Price", text="Price")
snapshot_table.heading("24h Change", text="24h Change")
snapshot_table.heading("Rank", text="Rank")
snapshot_table.heading("Market Cap", text="Market Cap")
snapshot_table.heading("24h Volume", text="24h Volume")
snapshot_table.heading("Collected", text="Collected")

snapshot_table.column(
    "ID",
    width=55,
    minwidth=45,
    anchor="center",
    stretch=False,
)

snapshot_table.column(
    "Symbol",
    width=75,
    minwidth=65,
    anchor="center",
)

snapshot_table.column(
    "Price",
    width=115,
    minwidth=100,
    anchor="e",
)

snapshot_table.column(
    "24h Change",
    width=95,
    minwidth=85,
    anchor="e",
)

snapshot_table.column(
    "Rank",
    width=60,
    minwidth=55,
    anchor="center",
)

snapshot_table.column(
    "Market Cap",
    width=115,
    minwidth=100,
    anchor="e",
)

snapshot_table.column(
    "24h Volume",
    width=115,
    minwidth=100,
    anchor="e",
)

snapshot_table.column(
    "Collected",
    width=190,
    minwidth=175,
    anchor="center",
)

snapshot_table.tag_configure(
    "positive",
    foreground=COLOR_SUCCESS,
)

snapshot_table.tag_configure(
    "negative",
    foreground=COLOR_DANGER,
)

snapshot_table.tag_configure(
    "neutral",
    foreground=COLOR_TEXT,
)

snapshot_table.tag_configure(
    "new",
    background="#DFF3E8",
)

snapshot_table.grid(
    row=1,
    column=0,
    sticky="nsew",
    padx=(18, 0),
    pady=(0, 18),
)

snapshot_scrollbar.grid(
    row=1,
    column=1,
    sticky="ns",
    padx=(0, 18),
    pady=(0, 18),
)


# --------------------------------------------------
# Start application
# --------------------------------------------------

load_snapshots()

root.mainloop()