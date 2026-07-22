import csv
from datetime import datetime, timedelta, timezone
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from database import get_connection


REPORT_RANGE_OPTIONS = {
    "Last 24 Hours": timedelta(hours=24),
    "Last 7 Days": timedelta(days=7),
    "Last 30 Days": timedelta(days=30),
    "Last 90 Days": timedelta(days=90),
    "All Data": None,
}

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


def _format_price(value):
    if value is None:
        return "--"
    if abs(value) >= 1:
        return f"${value:,.4f}"
    return f"${value:,.8f}"


def _format_local_time(timestamp):
    if not timestamp:
        return "--"

    parsed_timestamp = datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)

    return parsed_timestamp.astimezone().strftime(
        "%m/%d/%Y %I:%M:%S %p"
    )


def get_report_assets():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT
            assets.id,
            assets.symbol,
            COALESCE(assets.name, assets.symbol)
        FROM assets
        JOIN market_snapshots
            ON market_snapshots.asset_id = assets.id
        ORDER BY assets.symbol
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_price_history(asset_id, selected_range):
    range_delta = REPORT_RANGE_OPTIONS[selected_range]
    parameters = [asset_id]
    date_filter = ""

    if range_delta is not None:
        cutoff = datetime.now(timezone.utc) - range_delta
        date_filter = "AND collected_at_utc >= ?"
        parameters.append(cutoff.isoformat(timespec="seconds"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT
            collected_at_utc,
            price,
            market_cap,
            total_volume_24h
        FROM market_snapshots
        WHERE asset_id = ?
            {date_filter}
        ORDER BY collected_at_utc ASC, id ASC
        """,
        parameters,
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


class ReportsPage(tk.Frame):
    def __init__(self, parent, colors=None):
        self.colors = DEFAULT_COLORS.copy()
        if colors:
            self.colors.update(colors)

        super().__init__(parent, background=self.colors["window"])

        self.asset_lookup = {}
        self.current_rows = []
        self.current_symbol = ""

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._configure_styles()
        self._build_header()
        self._build_filters()
        self._build_summary_cards()
        self._build_chart_and_table()
        self.load_assets()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.configure(
            "Reports.Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
            foreground="#ffffff",
            background=self.colors["primary"],
        )
        style.map(
            "Reports.Primary.TButton",
            background=[("active", "#1d4ed8")],
        )
        style.configure(
            "Reports.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
        )
        style.configure("Reports.TCombobox", padding=6)
        style.configure(
            "Reports.Treeview",
            background=self.colors["card"],
            fieldbackground=self.colors["card"],
            foreground=self.colors["text"],
            rowheight=27,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Reports.Treeview.Heading",
            background=self.colors["table_header"],
            foreground=self.colors["text"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(8, 8),
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
            text="Reports",
            background=self.colors["window"],
            foreground=self.colors["text"],
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            header,
            text="Review historical prices and export collected market data",
            background=self.colors["window"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.record_count_label = tk.Label(
            header,
            text="0 records",
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
        filters_card.columnconfigure(3, weight=1)

        tk.Label(
            filters_card,
            text="Asset",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky="w", padx=(18, 8), pady=(16, 8))

        self.asset_choice = tk.StringVar()
        self.asset_dropdown = ttk.Combobox(
            filters_card,
            textvariable=self.asset_choice,
            state="readonly",
            width=22,
            style="Reports.TCombobox",
        )
        self.asset_dropdown.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 18),
            pady=(16, 8),
        )

        tk.Label(
            filters_card,
            text="Time Range",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 9),
        ).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=(16, 8))

        self.range_choice = tk.StringVar(value="Last 7 Days")
        self.range_dropdown = ttk.Combobox(
            filters_card,
            textvariable=self.range_choice,
            values=list(REPORT_RANGE_OPTIONS.keys()),
            state="readonly",
            width=16,
            style="Reports.TCombobox",
        )
        self.range_dropdown.grid(
            row=0,
            column=3,
            sticky="ew",
            padx=(0, 18),
            pady=(16, 8),
        )

        ttk.Button(
            filters_card,
            text="Update Report",
            command=self.refresh_report,
            style="Reports.Primary.TButton",
        ).grid(row=1, column=0, padx=(18, 5), pady=(8, 16), sticky="w")

        self.export_button = ttk.Button(
            filters_card,
            text="Export CSV",
            command=self.export_csv,
            state="disabled",
            style="Reports.TButton",
        )
        self.export_button.grid(
            row=1,
            column=1,
            padx=(5, 18),
            pady=(8, 16),
            sticky="w",
        )

    def _build_summary_cards(self):
        summary_frame = tk.Frame(
            self,
            background=self.colors["window"],
        )
        summary_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 14),
        )

        for column in range(4):
            summary_frame.columnconfigure(column, weight=1)

        self.latest_value = self._create_summary_card(
            summary_frame,
            0,
            "LATEST PRICE",
        )
        self.high_value = self._create_summary_card(
            summary_frame,
            1,
            "PERIOD HIGH",
        )
        self.low_value = self._create_summary_card(
            summary_frame,
            2,
            "PERIOD LOW",
        )
        self.change_value = self._create_summary_card(
            summary_frame,
            3,
            "PERIOD CHANGE",
        )

    def _create_summary_card(self, parent, column, caption):
        left_pad = 0 if column == 0 else 5
        right_pad = 0 if column == 3 else 5

        card = tk.Frame(
            parent,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        card.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=(left_pad, right_pad),
        )

        tk.Label(
            card,
            text=caption,
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 3))

        value_label = tk.Label(
            card,
            text="--",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Segoe UI", 15, "bold"),
        )
        value_label.pack(anchor="w", padx=16, pady=(0, 12))
        return value_label

    def _build_chart_and_table(self):
        content = tk.Frame(
            self,
            background=self.colors["window"],
        )
        content.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=28,
            pady=(0, 24),
        )
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        chart_card = tk.Frame(
            content,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        chart_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )
        chart_card.columnconfigure(0, weight=1)
        chart_card.rowconfigure(1, weight=1)

        self.chart_title_label = tk.Label(
            chart_card,
            text="Price History",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Segoe UI", 12, "bold"),
        )
        self.chart_title_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=18,
            pady=(14, 4),
        )

        self.figure = Figure(figsize=(6.5, 4.0), dpi=100)
        self.figure.patch.set_facecolor(self.colors["card"])
        self.axes = self.figure.add_subplot(111)
        self.figure.subplots_adjust(
            left=0.13,
            right=0.96,
            top=0.92,
            bottom=0.20,
        )

        self.chart_canvas = FigureCanvasTkAgg(
            self.figure,
            master=chart_card,
        )
        self.chart_canvas.get_tk_widget().grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=10,
            pady=(0, 10),
        )

        table_card = tk.Frame(
            content,
            background=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        table_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(1, weight=1)

        tk.Label(
            table_card,
            text="Recent Report Records",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Segoe UI", 12, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=18,
            pady=(14, 10),
        )

        columns = ("Collected", "Price")
        self.history_table = ttk.Treeview(
            table_card,
            columns=columns,
            show="headings",
            style="Reports.Treeview",
        )
        self.history_table.heading("Collected", text="Collected")
        self.history_table.heading("Price", text="Price")
        self.history_table.column(
            "Collected",
            width=165,
            minwidth=145,
            anchor="center",
        )
        self.history_table.column(
            "Price",
            width=105,
            minwidth=90,
            anchor="e",
        )

        scrollbar = ttk.Scrollbar(
            table_card,
            orient="vertical",
            command=self.history_table.yview,
        )
        self.history_table.configure(yscrollcommand=scrollbar.set)
        self.history_table.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(18, 0),
            pady=(0, 18),
        )
        scrollbar.grid(
            row=1,
            column=1,
            sticky="ns",
            padx=(0, 18),
            pady=(0, 18),
        )

        self._draw_empty_chart("Choose an asset to build a report")

    def load_assets(self):
        try:
            assets = get_report_assets()
        except Exception as error:
            messagebox.showerror(
                "Reports Error",
                f"Failed to load report assets:\n{error}",
                parent=self,
            )
            return

        self.asset_lookup = {
            f"{symbol} - {name}": asset_id
            for asset_id, symbol, name in assets
        }
        asset_labels = list(self.asset_lookup.keys())
        self.asset_dropdown.configure(values=asset_labels)

        if not asset_labels:
            self._draw_empty_chart(
                "No market snapshots are available yet"
            )
            return

        if self.asset_choice.get() not in self.asset_lookup:
            self.asset_choice.set(asset_labels[0])

        self.refresh_report()

    def refresh_report(self):
        selected_asset = self.asset_choice.get()
        selected_range = self.range_choice.get()

        if selected_asset not in self.asset_lookup:
            messagebox.showwarning(
                "Reports",
                "Choose an asset before updating the report.",
                parent=self,
            )
            return

        asset_id = self.asset_lookup[selected_asset]
        self.current_symbol = selected_asset.split(" - ", 1)[0]

        try:
            self.current_rows = get_price_history(
                asset_id,
                selected_range,
            )
        except Exception as error:
            messagebox.showerror(
                "Reports Error",
                f"Failed to build the report:\n{error}",
                parent=self,
            )
            return

        self.record_count_label.config(
            text=f"{len(self.current_rows):,} records"
        )
        self.chart_title_label.config(
            text=f"{self.current_symbol} Price History - {selected_range}"
        )

        self._update_summary()
        self._update_chart()
        self._update_table()
        self.export_button.config(
            state="normal" if self.current_rows else "disabled"
        )

    def _update_summary(self):
        if not self.current_rows:
            for label in (
                self.latest_value,
                self.high_value,
                self.low_value,
                self.change_value,
            ):
                label.config(
                    text="--",
                    foreground=self.colors["text"],
                )
            return

        prices = [row[1] for row in self.current_rows]
        first_price = prices[0]
        latest_price = prices[-1]

        self.latest_value.config(text=_format_price(latest_price))
        self.high_value.config(text=_format_price(max(prices)))
        self.low_value.config(text=_format_price(min(prices)))

        if first_price == 0:
            change_text = "--"
            change_color = self.colors["text"]
        else:
            percentage_change = (
                (latest_price - first_price) / first_price
            ) * 100
            change_text = f"{percentage_change:+.2f}%"
            if percentage_change > 0:
                change_color = self.colors["success"]
            elif percentage_change < 0:
                change_color = self.colors["danger"]
            else:
                change_color = self.colors["text"]

        self.change_value.config(
            text=change_text,
            foreground=change_color,
        )

    def _update_chart(self):
        self.axes.clear()
        self._style_axes()

        if not self.current_rows:
            self._draw_empty_chart(
                "No records were found for this time range"
            )
            return

        display_rows = self._downsample_rows(self.current_rows, 2000)
        timestamps = []
        prices = []

        for timestamp, price, _, _ in display_rows:
            parsed_timestamp = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
            if parsed_timestamp.tzinfo is None:
                parsed_timestamp = parsed_timestamp.replace(
                    tzinfo=timezone.utc
                )
            timestamps.append(parsed_timestamp.astimezone())
            prices.append(price)

        line_color = self.colors["primary"]
        if prices[-1] < prices[0]:
            line_color = self.colors["danger"]

        self.axes.plot(
            timestamps,
            prices,
            color=line_color,
            linewidth=2,
        )
        self.axes.fill_between(
            timestamps,
            prices,
            min(prices),
            color=line_color,
            alpha=0.08,
        )
        self.axes.set_ylabel(
            "Price (USD)",
            color=self.colors["muted"],
        )
        self.axes.tick_params(axis="x", rotation=25)
        self.figure.autofmt_xdate(rotation=25, ha="right")
        self.chart_canvas.draw_idle()

    def _style_axes(self):
        self.axes.set_facecolor(self.colors["card"])
        self.axes.grid(
            True,
            color=self.colors["border"],
            linewidth=0.7,
            alpha=0.8,
        )
        self.axes.set_axisbelow(True)
        self.axes.tick_params(
            colors=self.colors["muted"],
            labelsize=8,
        )
        for spine in self.axes.spines.values():
            spine.set_visible(False)

    def _draw_empty_chart(self, message):
        self.axes.clear()
        self._style_axes()
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.text(
            0.5,
            0.5,
            message,
            transform=self.axes.transAxes,
            horizontalalignment="center",
            verticalalignment="center",
            color=self.colors["muted"],
            fontsize=10,
        )
        self.chart_canvas.draw_idle()

    def _update_table(self):
        for row_id in self.history_table.get_children():
            self.history_table.delete(row_id)

        for timestamp, price, _, _ in reversed(self.current_rows[-100:]):
            self.history_table.insert(
                "",
                "end",
                values=(
                    _format_local_time(timestamp),
                    _format_price(price),
                ),
            )

    @staticmethod
    def _downsample_rows(rows, maximum_points):
        if len(rows) <= maximum_points:
            return rows

        step = len(rows) / maximum_points
        selected_rows = [
            rows[int(index * step)]
            for index in range(maximum_points)
        ]

        if selected_rows[-1] != rows[-1]:
            selected_rows[-1] = rows[-1]

        return selected_rows

    def export_csv(self):
        if not self.current_rows:
            return

        safe_range = self.range_choice.get().lower().replace(" ", "_")
        default_name = (
            f"{self.current_symbol.lower()}_{safe_range}_report.csv"
        )
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Market Report",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")],
        )

        if not file_path:
            return

        try:
            with open(
                file_path,
                "w",
                newline="",
                encoding="utf-8",
            ) as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [
                        "symbol",
                        "collected_at_utc",
                        "price_usd",
                        "market_cap_usd",
                        "total_volume_24h_usd",
                    ]
                )
                for timestamp, price, market_cap, volume in self.current_rows:
                    writer.writerow(
                        [
                            self.current_symbol,
                            timestamp,
                            price,
                            market_cap,
                            volume,
                        ]
                    )
        except OSError as error:
            messagebox.showerror(
                "Export Error",
                f"Failed to export the report:\n{error}",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Report Exported",
            f"Saved {len(self.current_rows):,} records to:\n{file_path}",
            parent=self,
        )

