import csv
import os
import subprocess
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk


PROJECT_PREFIX = "MT"
PROJECT_NAME = "MarketTracker"

BASE_DIR = Path(__file__).resolve().parent
LOG_DIRECTORY = BASE_DIR / "project_logs"
CSV_FILE = LOG_DIRECTORY / "markettracker_project_log.csv"

CSV_HEADERS = [
    "change_id",
    "date",
    "project",
    "version",
    "sprint",
    "change_type",
    "files_changed",
    "changes_made",
    "project_intent",
    "bugs_fixed",
    "features_added",
    "testing_performed",
    "git_commit_hash",
    "screenshot_reference",
    "video_diary_reference",
    "follow_up_items",
    "notes",
]

EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    ".idea",
    ".vscode",
    "project_logs",
}

EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db-journal",
}

GIT_STATUS_LABELS = {
    "M": "Modified",
    "A": "Added",
    "D": "Deleted",
    "R": "Renamed",
    "C": "Copied",
    "U": "Unmerged",
    "?": "Untracked",
    "!": "Ignored",
}


def ensure_log_file():
    """
    Create the project_logs directory and CSV file if they do not exist.
    """
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not CSV_FILE.exists():
        with CSV_FILE.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()


def get_next_change_id():
    """
    Read existing change IDs and return the next available ID.
    Example: MT-0001, MT-0002, MT-0003
    """
    ensure_log_file()

    highest_number = 0

    with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            change_id = row.get("change_id", "").strip()

            if not change_id.startswith(f"{PROJECT_PREFIX}-"):
                continue

            try:
                number = int(change_id.split("-")[1])
                highest_number = max(highest_number, number)
            except (IndexError, ValueError):
                continue

    return f"{PROJECT_PREFIX}-{highest_number + 1:04d}"


def get_text_value(text_widget):
    """
    Return cleaned text from a multiline Text widget.
    """
    return text_widget.get("1.0", tk.END).strip()


def set_text_value(text_widget, value=""):
    """
    Replace the contents of a multiline Text widget.
    """
    text_widget.delete("1.0", tk.END)

    if value:
        text_widget.insert("1.0", value)


def collect_form_data():
    """
    Collect all information currently entered in the form.
    """
    return {
        "change_id": change_id_var.get().strip(),
        "date": date_var.get().strip(),
        "project": PROJECT_NAME,
        "version": version_var.get().strip(),
        "sprint": sprint_var.get().strip(),
        "change_type": change_type_var.get().strip(),
        "files_changed": get_text_value(files_changed_text),
        "changes_made": get_text_value(changes_made_text),
        "project_intent": get_text_value(project_intent_text),
        "bugs_fixed": get_text_value(bugs_fixed_text),
        "features_added": get_text_value(features_added_text),
        "testing_performed": get_text_value(testing_performed_text),
        "git_commit_hash": commit_hash_var.get().strip(),
        "screenshot_reference": screenshot_var.get().strip(),
        "video_diary_reference": video_reference_var.get().strip(),
        "follow_up_items": get_text_value(follow_up_text),
        "notes": get_text_value(notes_text),
    }


def validate_form(entry):
    """
    Check that the required fields contain information.
    """
    missing_fields = []

    if not entry["date"]:
        missing_fields.append("Date")

    if not entry["files_changed"]:
        missing_fields.append("Files Changed")

    if not entry["changes_made"]:
        missing_fields.append("Changes Made")

    if not entry["project_intent"]:
        missing_fields.append("Project Intent")

    if missing_fields:
        formatted_fields = "\n".join(f"• {field}" for field in missing_fields)

        messagebox.showwarning(
            "Missing Required Information",
            "Please complete these required fields:\n\n"
            f"{formatted_fields}",
        )
        return False

    return True


def save_entry():
    """
    Validate the form and append the entry to the CSV file.
    """
    ensure_log_file()
    entry = collect_form_data()

    if not validate_form(entry):
        return

    try:
        with CSV_FILE.open("a", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writerow(entry)

    except OSError as error:
        messagebox.showerror(
            "Save Error",
            "The project log entry could not be saved.\n\n"
            "Make sure the CSV file is not currently locked by another program.\n\n"
            f"Technical details:\n{error}",
        )
        return

    saved_change_id = entry["change_id"]

    messagebox.showinfo(
        "Entry Saved",
        f"{saved_change_id} was added to the project log.",
    )

    clear_form()
    load_recent_entries()
    detect_git_changes(show_messages=False)


def clear_form():
    """
    Clear the form and prepare the next project log ID.
    """
    change_id_var.set(get_next_change_id())
    date_var.set(date.today().isoformat())
    version_var.set("")
    sprint_var.set("")
    change_type_var.set("Feature")

    commit_hash_var.set("")
    screenshot_var.set("")
    video_reference_var.set("")

    set_text_value(files_changed_text)
    set_text_value(changes_made_text)
    set_text_value(project_intent_text)
    set_text_value(bugs_fixed_text)
    set_text_value(features_added_text)
    set_text_value(testing_performed_text)
    set_text_value(follow_up_text)
    set_text_value(notes_text)

    clear_detected_files()
    git_status_var.set("Git status has not been checked.")

    files_changed_text.focus_set()


def load_recent_entries():
    """
    Display the most recent CSV entries in the table.
    """
    for item in recent_entries_table.get_children():
        recent_entries_table.delete(item)

    ensure_log_file()

    entries = []

    try:
        with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            entries = list(reader)

    except OSError as error:
        messagebox.showerror(
            "Read Error",
            f"The project log could not be opened.\n\n{error}",
        )
        return

    for entry in reversed(entries[-25:]):
        recent_entries_table.insert(
            "",
            tk.END,
            values=(
                entry.get("change_id", ""),
                entry.get("date", ""),
                entry.get("change_type", ""),
                entry.get("files_changed", ""),
                entry.get("changes_made", ""),
                entry.get("git_commit_hash", ""),
            ),
        )

    status_var.set(
        f"{len(entries)} total entries | CSV: {CSV_FILE.name}"
    )


def open_csv_file():
    """
    Open the project log CSV using the default Windows application.
    """
    ensure_log_file()

    try:
        os.startfile(CSV_FILE)
    except AttributeError:
        messagebox.showinfo(
            "CSV Location",
            str(CSV_FILE),
        )
    except OSError as error:
        messagebox.showerror(
            "Open Error",
            f"The CSV file could not be opened.\n\n{error}",
        )


def open_log_folder():
    """
    Open the project_logs folder in Windows File Explorer.
    """
    ensure_log_file()

    try:
        os.startfile(LOG_DIRECTORY)
    except AttributeError:
        messagebox.showinfo(
            "Project Log Folder",
            str(LOG_DIRECTORY),
        )
    except OSError as error:
        messagebox.showerror(
            "Open Error",
            f"The project log folder could not be opened.\n\n{error}",
        )


def run_git_command(arguments):
    """
    Run a Git command inside the MarketTracker project folder.

    Returns:
        tuple:
            success: True or False
            output: Standard output
            error: Standard error or exception message
    """
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        success = result.returncode == 0

        return (
            success,
            result.stdout.strip(),
            result.stderr.strip(),
        )

    except FileNotFoundError:
        return (
            False,
            "",
            "Git was not found. Make sure Git is installed and available in PowerShell.",
        )

    except OSError as error:
        return (
            False,
            "",
            str(error),
        )


def is_git_repository():
    """
    Determine whether the project folder is inside a Git repository.
    """
    success, output, _ = run_git_command(
        ["rev-parse", "--is-inside-work-tree"]
    )

    return success and output.lower() == "true"


def get_git_branch():
    """
    Return the current Git branch name.
    """
    success, output, _ = run_git_command(
        ["branch", "--show-current"]
    )

    if success and output:
        return output

    return "Unknown"


def get_git_status_entries():
    """
    Read Git porcelain status and return structured change information.

    Each returned dictionary contains:
        file
        status_code
        status_label
        selected
    """
    success, output, error = run_git_command(
        ["status", "--short", "--untracked-files=all"]
    )

    if not success:
        raise RuntimeError(error or "Git status could not be read.")

    entries = []

    if not output:
        return entries

    for line in output.splitlines():
        if len(line) < 3:
            continue

        index_status = line[0]
        working_status = line[1]
        file_text = line[3:].strip()

        status_code = determine_primary_status(
            index_status,
            working_status,
        )

        if " -> " in file_text:
            old_name, new_name = file_text.split(" -> ", 1)
            display_file = f"{old_name} → {new_name}"
        else:
            display_file = file_text

        entries.append(
            {
                "file": display_file,
                "status_code": status_code,
                "status_label": GIT_STATUS_LABELS.get(
                    status_code,
                    "Changed",
                ),
                "selected": True,
            }
        )

    return entries


def determine_primary_status(index_status, working_status):
    """
    Convert Git's two-character status into one main status code.
    """
    combined_statuses = [index_status, working_status]

    priority = [
        "?",
        "U",
        "R",
        "D",
        "A",
        "M",
        "C",
        "!",
    ]

    for status_code in priority:
        if status_code in combined_statuses:
            return status_code

    return "M"


def clear_detected_files():
    """
    Clear all rows from the detected-files table.
    """
    for item in detected_files_table.get_children():
        detected_files_table.delete(item)


def populate_detected_files(entries):
    """
    Load Git or scanned project files into the detected-files table.
    """
    clear_detected_files()

    for entry in entries:
        selection_symbol = "✓" if entry.get("selected", True) else ""

        detected_files_table.insert(
            "",
            tk.END,
            values=(
                selection_symbol,
                entry.get("status_label", "Project File"),
                entry.get("file", ""),
            ),
        )

    update_files_changed_from_selection()


def detect_git_changes(show_messages=True):
    """
    Detect files changed according to Git and load them into the table.
    """
    if not is_git_repository():
        git_status_var.set("This folder is not recognized as a Git repository.")

        if show_messages:
            messagebox.showwarning(
                "Git Repository Not Found",
                "The Project Log Manager could not find a Git repository "
                "in this folder.\n\n"
                f"Folder checked:\n{BASE_DIR}\n\n"
                "You can still use Scan Project Files.",
            )

        return

    try:
        entries = get_git_status_entries()

    except RuntimeError as error:
        git_status_var.set("Git status could not be read.")

        if show_messages:
            messagebox.showerror(
                "Git Status Error",
                str(error),
            )

        return

    branch_name = get_git_branch()

    if not entries:
        clear_detected_files()
        set_text_value(files_changed_text)

        git_status_var.set(
            f"Branch: {branch_name} | Working tree is clean."
        )

        if show_messages:
            messagebox.showinfo(
                "No Git Changes",
                "Git reports that the working tree is clean.\n\n"
                "There are no modified, added, deleted, or untracked files.",
            )

        return

    populate_detected_files(entries)

    git_status_var.set(
        f"Branch: {branch_name} | "
        f"{len(entries)} changed file(s) detected."
    )


def should_include_project_file(file_path):
    """
    Return True when a project file should appear in the scanned file list.
    """
    relative_path = file_path.relative_to(BASE_DIR)

    if any(
        directory_name in EXCLUDED_DIRECTORIES
        for directory_name in relative_path.parts[:-1]
    ):
        return False

    if file_path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return False

    return file_path.is_file()


def scan_project_files():
    """
    Scan the project folder and show selectable files.

    This does not determine whether files changed. It simply lists project
    files that may be selected manually.
    """
    entries = []

    try:
        project_files = sorted(
            file_path
            for file_path in BASE_DIR.rglob("*")
            if should_include_project_file(file_path)
        )

    except OSError as error:
        messagebox.showerror(
            "Project Scan Error",
            f"The project folder could not be scanned.\n\n{error}",
        )
        return

    for file_path in project_files:
        relative_path = file_path.relative_to(BASE_DIR)

        entries.append(
            {
                "file": str(relative_path),
                "status_label": "Project File",
                "selected": False,
            }
        )

    populate_detected_files(entries)

    git_status_var.set(
        f"{len(entries)} project file(s) found. "
        "Double-click files to select them."
    )


def toggle_detected_file_selection(event=None):
    """
    Toggle the selected state of the highlighted detected-file row.
    """
    selected_items = detected_files_table.selection()

    if not selected_items:
        return

    for item_id in selected_items:
        current_values = detected_files_table.item(
            item_id,
            "values",
        )

        if len(current_values) < 3:
            continue

        selection_symbol = current_values[0]
        new_symbol = "" if selection_symbol == "✓" else "✓"

        detected_files_table.item(
            item_id,
            values=(
                new_symbol,
                current_values[1],
                current_values[2],
            ),
        )

    update_files_changed_from_selection()


def select_all_detected_files():
    """
    Mark all detected files as selected.
    """
    for item_id in detected_files_table.get_children():
        current_values = detected_files_table.item(
            item_id,
            "values",
        )

        if len(current_values) < 3:
            continue

        detected_files_table.item(
            item_id,
            values=(
                "✓",
                current_values[1],
                current_values[2],
            ),
        )

    update_files_changed_from_selection()


def clear_all_detected_file_selections():
    """
    Unselect every detected project file.
    """
    for item_id in detected_files_table.get_children():
        current_values = detected_files_table.item(
            item_id,
            "values",
        )

        if len(current_values) < 3:
            continue

        detected_files_table.item(
            item_id,
            values=(
                "",
                current_values[1],
                current_values[2],
            ),
        )

    update_files_changed_from_selection()


def update_files_changed_from_selection():
    """
    Copy selected filenames from the detected-files table into Files Changed.
    """
    selected_files = []

    for item_id in detected_files_table.get_children():
        values = detected_files_table.item(
            item_id,
            "values",
        )

        if len(values) < 3:
            continue

        selection_symbol = values[0]
        status_label = values[1]
        file_name = values[2]

        if selection_symbol == "✓":
            selected_files.append(
                f"{file_name} [{status_label}]"
            )

    set_text_value(
        files_changed_text,
        "\n".join(selected_files),
    )


def create_labeled_entry(parent, label_text, variable, row, width=28):
    """
    Create a standard label and single-line entry field.
    """
    label = ttk.Label(parent, text=label_text)
    label.grid(
        row=row,
        column=0,
        sticky="w",
        padx=(0, 8),
        pady=4,
    )

    entry = ttk.Entry(
        parent,
        textvariable=variable,
        width=width,
    )
    entry.grid(
        row=row,
        column=1,
        sticky="ew",
        pady=4,
    )

    return entry


def create_labeled_text(parent, label_text, row, height=3):
    """
    Create a label and multiline Text field.
    """
    label = ttk.Label(parent, text=label_text)
    label.grid(
        row=row,
        column=0,
        sticky="nw",
        padx=(0, 8),
        pady=4,
    )

    text_widget = tk.Text(
        parent,
        height=height,
        width=60,
        wrap="word",
        undo=True,
    )
    text_widget.grid(
        row=row,
        column=1,
        sticky="ew",
        pady=4,
    )

    return text_widget


ensure_log_file()

root = tk.Tk()
root.title("MarketTracker Project Log Manager - Version 2A")
root.geometry("1350x900")
root.minsize(1050, 750)

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

main_frame = ttk.Frame(root, padding=12)
main_frame.grid(
    row=0,
    column=0,
    sticky="nsew",
)

main_frame.columnconfigure(0, weight=1)
main_frame.rowconfigure(1, weight=3)
main_frame.rowconfigure(2, weight=2)

title_label = ttk.Label(
    main_frame,
    text="MarketTracker Project Log Manager",
    font=("Segoe UI", 18, "bold"),
)
title_label.grid(
    row=0,
    column=0,
    sticky="w",
    pady=(0, 10),
)

content_pane = ttk.Panedwindow(
    main_frame,
    orient=tk.HORIZONTAL,
)
content_pane.grid(
    row=1,
    column=0,
    sticky="nsew",
)

form_container = ttk.Frame(
    content_pane,
    padding=(0, 0, 10, 0),
)
form_container.columnconfigure(0, weight=1)
form_container.rowconfigure(0, weight=1)

canvas = tk.Canvas(
    form_container,
    highlightthickness=0,
)
canvas.grid(
    row=0,
    column=0,
    sticky="nsew",
)

form_scrollbar = ttk.Scrollbar(
    form_container,
    orient=tk.VERTICAL,
    command=canvas.yview,
)
form_scrollbar.grid(
    row=0,
    column=1,
    sticky="ns",
)

canvas.configure(
    yscrollcommand=form_scrollbar.set
)

form_frame = ttk.LabelFrame(
    canvas,
    text="New Project Log Entry",
    padding=12,
)
form_frame.columnconfigure(1, weight=1)

form_window = canvas.create_window(
    (0, 0),
    window=form_frame,
    anchor="nw",
)


def update_scroll_region(event=None):
    canvas.configure(
        scrollregion=canvas.bbox("all")
    )


def resize_form_width(event):
    canvas.itemconfigure(
        form_window,
        width=event.width,
    )


form_frame.bind(
    "<Configure>",
    update_scroll_region,
)
canvas.bind(
    "<Configure>",
    resize_form_width,
)

content_pane.add(
    form_container,
    weight=3,
)

tools_frame = ttk.Frame(
    content_pane,
    padding=(10, 0, 0, 0),
)
tools_frame.columnconfigure(0, weight=1)
tools_frame.rowconfigure(1, weight=1)

content_pane.add(
    tools_frame,
    weight=2,
)

change_id_var = tk.StringVar(
    value=get_next_change_id()
)
date_var = tk.StringVar(
    value=date.today().isoformat()
)
version_var = tk.StringVar()
sprint_var = tk.StringVar()
change_type_var = tk.StringVar(
    value="Feature"
)
commit_hash_var = tk.StringVar()
screenshot_var = tk.StringVar()
video_reference_var = tk.StringVar()
status_var = tk.StringVar(
    value="Ready"
)
git_status_var = tk.StringVar(
    value="Git status has not been checked."
)

change_id_entry = create_labeled_entry(
    form_frame,
    "Change ID",
    change_id_var,
    row=0,
)
change_id_entry.configure(
    state="readonly"
)

create_labeled_entry(
    form_frame,
    "Date *",
    date_var,
    row=1,
)

create_labeled_entry(
    form_frame,
    "Version",
    version_var,
    row=2,
)

create_labeled_entry(
    form_frame,
    "Sprint",
    sprint_var,
    row=3,
)

change_type_label = ttk.Label(
    form_frame,
    text="Change Type",
)
change_type_label.grid(
    row=4,
    column=0,
    sticky="w",
    padx=(0, 8),
    pady=4,
)

change_type_combo = ttk.Combobox(
    form_frame,
    textvariable=change_type_var,
    state="readonly",
    values=[
        "Feature",
        "Bug Fix",
        "Refactor",
        "UI Change",
        "Database Change",
        "Documentation",
        "Testing",
        "Configuration",
        "Maintenance",
        "Planning",
        "Other",
    ],
)
change_type_combo.grid(
    row=4,
    column=1,
    sticky="ew",
    pady=4,
)

files_changed_text = create_labeled_text(
    form_frame,
    "Files Changed *",
    row=5,
    height=4,
)

changes_made_text = create_labeled_text(
    form_frame,
    "Changes Made *",
    row=6,
    height=5,
)

project_intent_text = create_labeled_text(
    form_frame,
    "Project Intent *",
    row=7,
    height=4,
)

bugs_fixed_text = create_labeled_text(
    form_frame,
    "Bugs Fixed",
    row=8,
    height=3,
)

features_added_text = create_labeled_text(
    form_frame,
    "Features Added",
    row=9,
    height=3,
)

testing_performed_text = create_labeled_text(
    form_frame,
    "Testing Performed",
    row=10,
    height=3,
)

create_labeled_entry(
    form_frame,
    "Git Commit Hash",
    commit_hash_var,
    row=11,
)

create_labeled_entry(
    form_frame,
    "Screenshot Reference",
    screenshot_var,
    row=12,
)

create_labeled_entry(
    form_frame,
    "Video Diary Reference",
    video_reference_var,
    row=13,
)

follow_up_text = create_labeled_text(
    form_frame,
    "Follow-Up Items",
    row=14,
    height=3,
)

notes_text = create_labeled_text(
    form_frame,
    "Notes",
    row=15,
    height=4,
)

required_label = ttk.Label(
    form_frame,
    text="* Required field",
)
required_label.grid(
    row=16,
    column=1,
    sticky="w",
    pady=(8, 0),
)

git_tools_frame = ttk.LabelFrame(
    tools_frame,
    text="Project Change Detection",
    padding=10,
)
git_tools_frame.grid(
    row=0,
    column=0,
    sticky="ew",
    pady=(0, 10),
)
git_tools_frame.columnconfigure(0, weight=1)
git_tools_frame.columnconfigure(1, weight=1)

detect_changes_button = ttk.Button(
    git_tools_frame,
    text="Detect Git Changes",
    command=detect_git_changes,
)
detect_changes_button.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=(0, 4),
    pady=4,
)

scan_files_button = ttk.Button(
    git_tools_frame,
    text="Scan Project Files",
    command=scan_project_files,
)
scan_files_button.grid(
    row=0,
    column=1,
    sticky="ew",
    padx=(4, 0),
    pady=4,
)

select_all_button = ttk.Button(
    git_tools_frame,
    text="Select All",
    command=select_all_detected_files,
)
select_all_button.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=(0, 4),
    pady=4,
)

clear_selection_button = ttk.Button(
    git_tools_frame,
    text="Clear Selection",
    command=clear_all_detected_file_selections,
)
clear_selection_button.grid(
    row=1,
    column=1,
    sticky="ew",
    padx=(4, 0),
    pady=4,
)

git_status_label = ttk.Label(
    git_tools_frame,
    textvariable=git_status_var,
    wraplength=420,
    justify="left",
)
git_status_label.grid(
    row=2,
    column=0,
    columnspan=2,
    sticky="w",
    pady=(8, 2),
)

instruction_label = ttk.Label(
    git_tools_frame,
    text=(
        "Double-click a row to select or deselect it. "
        "Selected files are copied into Files Changed."
    ),
    wraplength=420,
    justify="left",
)
instruction_label.grid(
    row=3,
    column=0,
    columnspan=2,
    sticky="w",
    pady=(2, 0),
)

detected_files_frame = ttk.LabelFrame(
    tools_frame,
    text="Detected or Scanned Files",
    padding=8,
)
detected_files_frame.grid(
    row=1,
    column=0,
    sticky="nsew",
)
detected_files_frame.columnconfigure(0, weight=1)
detected_files_frame.rowconfigure(0, weight=1)

detected_file_columns = (
    "selected",
    "status",
    "file",
)

detected_files_table = ttk.Treeview(
    detected_files_frame,
    columns=detected_file_columns,
    show="headings",
    selectmode="extended",
)

detected_files_table.heading(
    "selected",
    text="Use",
)
detected_files_table.heading(
    "status",
    text="Status",
)
detected_files_table.heading(
    "file",
    text="File",
)

detected_files_table.column(
    "selected",
    width=50,
    anchor="center",
    stretch=False,
)
detected_files_table.column(
    "status",
    width=100,
    anchor="w",
    stretch=False,
)
detected_files_table.column(
    "file",
    width=320,
    anchor="w",
)

detected_files_table.grid(
    row=0,
    column=0,
    sticky="nsew",
)

detected_files_scrollbar = ttk.Scrollbar(
    detected_files_frame,
    orient=tk.VERTICAL,
    command=detected_files_table.yview,
)
detected_files_scrollbar.grid(
    row=0,
    column=1,
    sticky="ns",
)

detected_files_table.configure(
    yscrollcommand=detected_files_scrollbar.set
)

detected_files_table.bind(
    "<Double-1>",
    toggle_detected_file_selection,
)

action_buttons_frame = ttk.Frame(
    tools_frame,
)
action_buttons_frame.grid(
    row=2,
    column=0,
    sticky="ew",
    pady=(10, 0),
)
action_buttons_frame.columnconfigure(0, weight=1)
action_buttons_frame.columnconfigure(1, weight=1)

save_button = ttk.Button(
    action_buttons_frame,
    text="Save Log Entry",
    command=save_entry,
)
save_button.grid(
    row=0,
    column=0,
    columnspan=2,
    sticky="ew",
    pady=(0, 6),
    ipady=6,
)

clear_button = ttk.Button(
    action_buttons_frame,
    text="Clear Form",
    command=clear_form,
)
clear_button.grid(
    row=1,
    column=0,
    columnspan=2,
    sticky="ew",
    pady=6,
)

open_csv_button = ttk.Button(
    action_buttons_frame,
    text="Open CSV File",
    command=open_csv_file,
)
open_csv_button.grid(
    row=2,
    column=0,
    sticky="ew",
    padx=(0, 4),
    pady=6,
)

open_folder_button = ttk.Button(
    action_buttons_frame,
    text="Open Log Folder",
    command=open_log_folder,
)
open_folder_button.grid(
    row=2,
    column=1,
    sticky="ew",
    padx=(4, 0),
    pady=6,
)

refresh_button = ttk.Button(
    action_buttons_frame,
    text="Refresh Recent Entries",
    command=load_recent_entries,
)
refresh_button.grid(
    row=3,
    column=0,
    columnspan=2,
    sticky="ew",
    pady=6,
)

recent_frame = ttk.LabelFrame(
    main_frame,
    text="Recent Project Log Entries",
    padding=8,
)
recent_frame.grid(
    row=2,
    column=0,
    sticky="nsew",
    pady=(12, 0),
)

recent_frame.columnconfigure(0, weight=1)
recent_frame.rowconfigure(0, weight=1)

table_columns = (
    "change_id",
    "date",
    "change_type",
    "files_changed",
    "changes_made",
    "commit",
)

recent_entries_table = ttk.Treeview(
    recent_frame,
    columns=table_columns,
    show="headings",
    height=8,
)

recent_entries_table.heading(
    "change_id",
    text="Change ID",
)
recent_entries_table.heading(
    "date",
    text="Date",
)
recent_entries_table.heading(
    "change_type",
    text="Type",
)
recent_entries_table.heading(
    "files_changed",
    text="Files Changed",
)
recent_entries_table.heading(
    "changes_made",
    text="Changes Made",
)
recent_entries_table.heading(
    "commit",
    text="Commit",
)

recent_entries_table.column(
    "change_id",
    width=85,
    anchor="center",
)
recent_entries_table.column(
    "date",
    width=100,
    anchor="center",
)
recent_entries_table.column(
    "change_type",
    width=110,
)
recent_entries_table.column(
    "files_changed",
    width=250,
)
recent_entries_table.column(
    "changes_made",
    width=450,
)
recent_entries_table.column(
    "commit",
    width=100,
)

recent_entries_table.grid(
    row=0,
    column=0,
    sticky="nsew",
)

table_scrollbar = ttk.Scrollbar(
    recent_frame,
    orient=tk.VERTICAL,
    command=recent_entries_table.yview,
)
table_scrollbar.grid(
    row=0,
    column=1,
    sticky="ns",
)

recent_entries_table.configure(
    yscrollcommand=table_scrollbar.set
)

status_label = ttk.Label(
    main_frame,
    textvariable=status_var,
    anchor="w",
)
status_label.grid(
    row=3,
    column=0,
    sticky="ew",
    pady=(8, 0),
)

load_recent_entries()
detect_git_changes(show_messages=False)
files_changed_text.focus_set()

root.mainloop()