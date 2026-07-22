import tkinter as tk
from datetime import datetime
from tkinter import ttk

from database import get_connection, save_portfolio_position

DEFAULT_COLORS = {
    "window": "#f4f7fb",
    "card": "#ffffff",
    "border": "#dfe5ec",
    "text": "#172033",
    "muted": "#667085",
    "primary": "#2563eb",
    "success": "#16845b",
    "danger": "#c63f4a",
    "table_header": "#edf2f7",
}


def _format_large_currency(value):
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


def _format_snapshot_time(timestamp):
    if not timestamp:
        return "--"

    normalized_timestamp = timestamp.replace("Z", "+00:00")
    parsed_timestamp = datetime.fromisoformat(normalized_timestamp)
    local_timestamp = parsed_timestamp.astimezone()
    return local_timestamp.strftime("%m/%d/%Y %I:%M:%S %p")


def get_portfolio_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM assets")
    asset_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM market_snapshots")
    snapshot_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM portfolio_positions WHERE quantity > 0"
    )
    position_count = cursor.fetchone()[0]

    conn.close()
    return asset_count, snapshot_count, position_count


def get_portfolio_asset_options():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, symbol, COALESCE(name, symbol)
        FROM assets
        ORDER BY symbol ASC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_portfolio_rows(search_text="", change_filter="All", sort_mode="Symbol A-Z"):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            assets.symbol,
            COALESCE(assets.name, assets.symbol),
            COALESCE(pp.quantity, 0) AS quantity,
            COALESCE(pp.average_cost, 0) AS average_cost,
            latest.price,
            latest.price_change_percentage_24h,
            latest.market_cap,
            latest.collected_at_utc
        FROM assets
        LEFT JOIN portfolio_positions pp
            ON pp.asset_id = assets.id
        LEFT JOIN (
            SELECT
                ms.asset_id,
                ms.price,
                ms.price_change_percentage_24h,
                ms.market_cap,
                ms.collected_at_utc
            FROM market_snapshots ms
            INNER JOIN (
                SELECT asset_id, MAX(id) AS latest_id
                FROM market_snapshots
                GROUP BY asset_id
            ) latest_ids
                ON latest_ids.asset_id = ms.asset_id
               AND latest_ids.latest_id = ms.id
        ) latest
            ON latest.asset_id = assets.id
        WHERE 1 = 1
    """

    parameters = []

    if search_text:
        query += " AND (LOWER(assets.symbol) LIKE ? OR LOWER(COALESCE(assets.name, assets.symbol)) LIKE ?)"
        search_pattern = f"%{search_text.lower()}%"
        parameters.extend([search_pattern, search_pattern])

    if change_filter == "Positive":
        query += " AND latest.price_change_percentage_24h > 0"
    elif change_filter == "Negative":
        query += " AND latest.price_change_percentage_24h < 0"
    elif change_filter == "Neutral":
        query += " AND (latest.price_change_percentage_24h IS NULL OR latest.price_change_percentage_24h = 0)"

    if sort_mode == "Symbol Z-A":
        query += " ORDER BY assets.symbol DESC"
    elif sort_mode == "Highest Price":
        query += " ORDER BY latest.price DESC"
    elif sort_mode == "Lowest Price":
        query += " ORDER BY latest.price ASC"
    elif sort_mode == "Biggest 24h Change":
        query += " ORDER BY latest.price_change_percentage_24h DESC"
    elif sort_mode == "Largest Market Cap":
        query += " ORDER BY latest.market_cap DESC"
    elif sort_mode == "Held Assets":
        query += " ORDER BY COALESCE(pp.quantity, 0) DESC"
    else:
        query += " ORDER BY assets.symbol ASC"

    cursor.execute(query, parameters)
    rows = cursor.fetchall()
    conn.close()

    portfolio_rows = []

    for symbol, name, quantity, average_cost, price, change_percentage, market_cap, collected_at_utc in rows:
        formatted_change = "--"
        change_tag = "neutral"

        if change_percentage is not None:
            formatted_change = f"{change_percentage:+.2f}%"
            if change_percentage > 0:
                change_tag = "positive"
            elif change_percentage < 0:
                change_tag = "negative"

        portfolio_rows.append(
            {
                "symbol": symbol,
                "name": name,
                "quantity": quantity,
                "average_cost": average_cost,
                "price": price,
                "price_text": f"${price:,.4f}" if price is not None else "--",
                "change_percentage": change_percentage,
                "change_text": formatted_change,
                "market_cap": market_cap,
                "market_cap_text": _format_large_currency(market_cap),
                "collected_at_utc": collected_at_utc,
                "collected_text": _format_snapshot_time(collected_at_utc),
                "change_tag": change_tag,
                "position_text": f"{quantity:,.4f}" if quantity else "--",
                "cost_basis_text": _format_large_currency(average_cost) if average_cost else "--",
            }
        )

    return portfolio_rows


class PortfolioPage(tk.Frame):
    def __init__(self, parent, colors=None):
        self.colors = DEFAULT_COLORS.copy()
        if colors:
            self.colors.update(colors)

        super().__init__(parent, background=self.colors["window"])

        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        self.asset_lookup = {}
        self._configure_styles()
        self._build_header()
        self._build_summary_cards()
        self._build_filters()
        self._build_table()
        self._build_position_editor()
        self.load_position_options()
        self.load_summary()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.configure(
            "Portfolio.Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
            foreground="#ffffff",
            background=self.colors["primary"],
        )
        style.map(
            "Portfolio.Primary.TButton",
            background=[("active", "#1d4ed8")],
        )
        style.configure(
            "Portfolio.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
        )
        style.configure(
            "Portfolio.TCombobox",
            padding=6,
        )
        style.configure(
            "Portfolio.Treeview",
            background=self.colors["card"],
            fieldbackground=self.colors["card"],
            foreground=self.colors["text"],
            rowheight=27,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Portfolio.Treeview.Heading",
            background=self.colors["table_header"],
            foreground=self.colors["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(8, 8),
        )
        style.map(
            "Portfolio.Treeview.Heading",
            background=[("active", "#DCE5ED")],
        )

    def _build_header(self):
        header = tk.Frame(self, background=self.colors["window"])
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=28,
            pady=(24, 16),
        )
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="Portfolio",
            background=self.colors["window"],
            foreground=self.colors["text"],
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            header,
            text="Review tracked asset exposure using the latest snapshot data",
            background=self.colors["window"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.summary_label = tk.Label(
            header,
            text="0 assets • 0 snapshots",
            background=self.colors["window"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        )
        self.summary_label.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
        )

    def _build_summary_cards(self):
        cards_frame = tk.Frame(
            self,
            background=self.colors["window"],
        )
        cards_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 14),
        )
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)
        cards_frame.columnconfigure(2, weight=1)

        self.asset_count_card = tk.Frame(
            cards_frame,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        self.asset_count_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.asset_count_value = tk.Label(
            self.asset_count_card,
            text="0",
            background=self.colors["card"],
            foreground=self.colors["primary"],
            font=("Segoe UI", 18, "bold"),
        )
        self.asset_count_value.pack(anchor="w", padx=16, pady=(16, 4))

        tk.Label(
            self.asset_count_card,
            text="Tracked Assets",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 16))

        self.snapshot_count_card = tk.Frame(
            cards_frame,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        self.snapshot_count_card.grid(row=0, column=1, sticky="nsew", padx=10)

        self.snapshot_count_value = tk.Label(
            self.snapshot_count_card,
            text="0",
            background=self.colors["card"],
            foreground=self.colors["success"],
            font=("Segoe UI", 18, "bold"),
        )
        self.snapshot_count_value.pack(anchor="w", padx=16, pady=(16, 4))

        tk.Label(
            self.snapshot_count_card,
            text="Latest Snapshots",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 16))

        self.position_count_card = tk.Frame(
            cards_frame,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        self.position_count_card.grid(row=0, column=2, sticky="nsew", padx=(10, 0))

        self.position_count_value = tk.Label(
            self.position_count_card,
            text="0",
            background=self.colors["card"],
            foreground=self.colors["danger"],
            font=("Segoe UI", 18, "bold"),
        )
        self.position_count_value.pack(anchor="w", padx=16, pady=(16, 4))

        tk.Label(
            self.position_count_card,
            text="Held Positions",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 16))

    def _build_filters(self):
        filters_card = tk.Frame(
            self,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        filters_card.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 14),
        )
        filters_card.columnconfigure(1, weight=1)
        filters_card.columnconfigure(3, weight=1)

        tk.Label(
            filters_card,
            text="Search",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky="w", padx=(18, 8), pady=(16, 8))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            filters_card,
            textvariable=self.search_var,
            width=24,
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
            text="Change",
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
            style="Portfolio.TCombobox",
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

        self.sort_var = tk.StringVar(value="Symbol A-Z")
        self.sort_dropdown = ttk.Combobox(
            filters_card,
            textvariable=self.sort_var,
            values=[
                "Symbol A-Z",
                "Symbol Z-A",
                "Highest Price",
                "Lowest Price",
                "Biggest 24h Change",
                "Largest Market Cap",
                "Held Assets",
            ],
            state="readonly",
            width=20,
            style="Portfolio.TCombobox",
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
            text="Apply",
            command=self.load_summary,
            style="Portfolio.Primary.TButton",
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
            style="Portfolio.TButton",
        )
        self.reset_filters_button.grid(
            row=1,
            column=3,
            padx=(4, 18),
            pady=(8, 16),
        )

    def _build_position_editor(self):
        editor_frame = tk.Frame(
            self,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        editor_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 14),
        )
        editor_frame.columnconfigure(1, weight=1)
        editor_frame.columnconfigure(3, weight=1)
        editor_frame.columnconfigure(5, weight=1)

        tk.Label(
            editor_frame,
            text="Position Editor",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=(18, 8), pady=(16, 12))

        tk.Label(
            editor_frame,
            text="Asset",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", padx=(18, 8), pady=(0, 8))

        self.position_asset_var = tk.StringVar()
        self.position_asset_dropdown = ttk.Combobox(
            editor_frame,
            textvariable=self.position_asset_var,
            state="readonly",
            width=22,
            style="Portfolio.TCombobox",
        )
        self.position_asset_dropdown.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 18),
            pady=(0, 8),
        )

        tk.Label(
            editor_frame,
            text="Qty",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=2, sticky="w", padx=(0, 8), pady=(0, 8))

        self.position_quantity_var = tk.StringVar(value="0")
        self.position_quantity_entry = ttk.Entry(
            editor_frame,
            textvariable=self.position_quantity_var,
            width=14,
        )
        self.position_quantity_entry.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=(0, 18),
            pady=(0, 8),
        )

        tk.Label(
            editor_frame,
            text="Avg Cost",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=4, sticky="w", padx=(0, 8), pady=(0, 8))

        self.position_cost_var = tk.StringVar(value="0")
        self.position_cost_entry = ttk.Entry(
            editor_frame,
            textvariable=self.position_cost_var,
            width=14,
        )
        self.position_cost_entry.grid(
            row=1,
            column=5,
            sticky="ew",
            padx=(0, 18),
            pady=(0, 8),
        )

        tk.Label(
            editor_frame,
            text="Notes",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=2, column=0, sticky="w", padx=(18, 8), pady=(0, 16))

        self.position_notes_var = tk.StringVar()
        self.position_notes_entry = ttk.Entry(
            editor_frame,
            textvariable=self.position_notes_var,
            width=40,
        )
        self.position_notes_entry.grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(0, 18),
            pady=(0, 16),
        )

        self.save_position_button = ttk.Button(
            editor_frame,
            text="Save Position",
            command=self.save_position,
            style="Portfolio.Primary.TButton",
        )
        self.save_position_button.grid(
            row=2,
            column=4,
            padx=(0, 8),
            pady=(0, 16),
        )

        self.clear_position_button = ttk.Button(
            editor_frame,
            text="Clear",
            command=self.clear_position_form,
            style="Portfolio.TButton",
        )
        self.clear_position_button.grid(
            row=2,
            column=5,
            padx=(0, 18),
            pady=(0, 16),
        )

        self.position_status_label = tk.Label(
            editor_frame,
            text="Use the editor to save a quantity and average cost for an asset.",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        )
        self.position_status_label.grid(
            row=3,
            column=0,
            columnspan=6,
            sticky="w",
            padx=(18, 18),
            pady=(0, 16),
        )

    def _build_table(self):
        table_frame = tk.Frame(
            self,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        table_frame.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(0, 24),
        )
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)

        columns = (
            "Symbol",
            "Name",
            "Qty",
            "Avg Cost",
            "Latest Price",
            "24h Change",
            "Market Cap",
            "Last Updated",
        )

        self.portfolio_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Portfolio.Treeview",
        )

        self.portfolio_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.portfolio_table.yview,
        )
        self.portfolio_table.configure(
            yscrollcommand=self.portfolio_scrollbar.set,
        )

        self.portfolio_table.column("Symbol", width=100, anchor="center")
        self.portfolio_table.column("Name", width=180, anchor="w")
        self.portfolio_table.column("Qty", width=90, anchor="center")
        self.portfolio_table.column("Avg Cost", width=110, anchor="e")
        self.portfolio_table.column("Latest Price", width=130, anchor="e")
        self.portfolio_table.column("24h Change", width=120, anchor="e")
        self.portfolio_table.column("Market Cap", width=150, anchor="e")
        self.portfolio_table.column("Last Updated", width=200, anchor="center")

        for column_name in columns:
            self.portfolio_table.heading(column_name, text=column_name)

        self.portfolio_table.tag_configure(
            "positive",
            foreground=self.colors["success"],
        )
        self.portfolio_table.tag_configure(
            "negative",
            foreground=self.colors["danger"],
        )
        self.portfolio_table.tag_configure(
            "neutral",
            foreground=self.colors["text"],
        )

        self.empty_state_label = tk.Label(
            table_frame,
            text="No portfolio data available for the current filter",
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

        self.portfolio_table.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(18, 0),
            pady=(0, 18),
        )
        self.portfolio_scrollbar.grid(
            row=1,
            column=1,
            sticky="ns",
            padx=(0, 18),
            pady=(0, 18),
        )

    def reset_filters(self):
        self.search_var.set("")
        self.change_filter_var.set("All")
        self.sort_var.set("Symbol A-Z")
        self.load_summary()

    def load_position_options(self):
        rows = get_portfolio_asset_options()
        self.asset_lookup = {
            f"{symbol} - {name}": asset_id
            for asset_id, symbol, name in rows
        }

        asset_labels = list(self.asset_lookup.keys())
        self.position_asset_dropdown.configure(values=asset_labels)

        if asset_labels:
            if self.position_asset_var.get() not in self.asset_lookup:
                self.position_asset_var.set(asset_labels[0])
        else:
            self.position_asset_var.set("")

    def clear_position_form(self):
        self.position_quantity_var.set("0")
        self.position_cost_var.set("0")
        self.position_notes_var.set("")
        self.position_status_label.config(
            text="Position form cleared.",
            foreground=self.colors["muted"],
        )

    def save_position(self):
        selected_asset = self.position_asset_var.get()
        if not selected_asset or selected_asset not in self.asset_lookup:
            self.position_status_label.config(
                text="Choose an asset before saving a position.",
                foreground=self.colors["danger"],
            )
            return

        try:
            quantity = float(self.position_quantity_var.get())
            average_cost = float(self.position_cost_var.get())
        except ValueError:
            self.position_status_label.config(
                text="Quantity and average cost must be numeric values.",
                foreground=self.colors["danger"],
            )
            return

        asset_id = self.asset_lookup[selected_asset]
        save_portfolio_position(
            asset_id=asset_id,
            quantity=quantity,
            average_cost=average_cost,
            notes=self.position_notes_var.get().strip() or None,
        )

        self.position_status_label.config(
            text=f"Saved position for {selected_asset}.",
            foreground=self.colors["success"],
        )
        self.load_summary()

    def load_summary(self):
        self.load_position_options()

        asset_count, snapshot_count, position_count = get_portfolio_summary()
        self.asset_count_value.config(text=str(asset_count))
        self.snapshot_count_value.config(text=str(snapshot_count))
        self.position_count_value.config(text=str(position_count))
        self.summary_label.config(
            text=f"{asset_count} assets • {snapshot_count} snapshots • {position_count} positions"
        )

        rows = get_portfolio_rows(
            search_text=self.search_var.get(),
            change_filter=self.change_filter_var.get(),
            sort_mode=self.sort_var.get(),
        )

        for item in self.portfolio_table.get_children():
            self.portfolio_table.delete(item)

        if not rows:
            self.portfolio_table.grid_remove()
            self.portfolio_scrollbar.grid_remove()
            self.empty_state_label.grid()
            self.position_count_value.config(text=str(position_count))
            return

        self.empty_state_label.grid_remove()
        self.portfolio_table.grid()
        self.portfolio_scrollbar.grid()

        top_row = max(rows, key=lambda row: row["market_cap"] or 0)
        self.position_count_value.config(text=str(position_count))

        for row in rows:
            self.portfolio_table.insert(
                "",
                "end",
                values=(
                    row["symbol"],
                    row["name"],
                    row["position_text"],
                    row["cost_basis_text"],
                    row["price_text"],
                    row["change_text"],
                    row["market_cap_text"],
                    row["collected_text"],
                ),
                tags=(row["change_tag"],),
            )
