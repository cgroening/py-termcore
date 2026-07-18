# termz

Terminal utilities for CLI, TUI, IO and general use.

## Overview

**termz** is a Python library that bundles reusable building blocks for terminal applications. It is organized into four sub-packages:

| Package | Contents |
|---------|----------|
| `termz.cli` | Styled console output via [Rich](https://github.com/Textualize/rich) |
| `termz.tui` | [Textual](https://github.com/Textualize/textual) TUI helpers – theme loading, custom widgets, modal screens |
| `termz.io` | SQLite database abstraction, JSON app-state storage, file utilities |
| `termz.util` | Datetime helpers, string utilities, singleton metaclass, debug decorators, logging setup |

## Requirements

- Python >= 3.12
- [`rich`](https://pypi.org/project/rich/)
- [`textual`](https://pypi.org/project/textual/) (required for `termz.tui`)

## Installation

```bash
pip install termz
```

---

## termz.cli – Styled CLI Output

Provides helpers for printing color-coded panels using Rich and for clearing terminal output.

```python
from termz import print_error, print_warning, print_success, print_info, clear_lines

print_success("File saved.")
print_warning("Disk space is low.")
print_error("Connection refused.")
print_info("Starting process...")

# Remove the last 4 rendered lines from the terminal
clear_lines(4)
```

### Functions

| Function | Description |
|----------|-------------|
| `print_error(message)` | Red panel with ✗ prefix |
| `print_warning(message)` | Yellow panel with ⚠ prefix |
| `print_success(message)` | Green panel with ✓ prefix |
| `print_info(message)` | Cyan panel with ℹ prefix |
| `print_panel(message, color)` | Panel with bold colored text |
| `print_custom_panel(formatted_message, panel_color)` | Panel with pre-formatted Rich markup |
| `clear_lines(count)` | Move cursor up `count` lines and clear everything below |
| `get_console()` | Returns the shared Rich `Console` instance |

---

## termz.tui – Textual TUI Helpers

### ThemeLoader

Dynamically loads and registers [Textual](https://github.com/Textualize/textual) themes from a folder. Each theme lives in its own sub-directory and must expose a `TEXTUAL_THEME` variable of type `textual.theme.Theme`. Optional `.css` / `.tcss` files in the same folder are loaded automatically when the theme is activated.

A theme is identified by the `name` of its `TEXTUAL_THEME` plus the prefix it is registered under – the name of its directory carries no meaning and is free to differ. A theme without a stylesheet is equally valid; ten of the built-in themes below ship none. Each theme folder is read on its own, so an app can register several loaders and its own themes never collide with the ones the toolkit brings.

termz ships 16 built-in themes:

`classic-black-saturated`, `classic-black-v1`, `classic-black-v2`, `classic-blue`, `compact-gray`, `mnml-black`, `mnml-deepblack`, `pure-amber`, `pure-black`, `pure-blue`, `pure-green`, `pure-sweet16`, `xplore-black`, `xplore-blue`, `xplore-blue-muted`, `xplore-teal`

```python
from pathlib import Path
from termz import ThemeLoader

loader = ThemeLoader(
    theme_folder="themes",           # optional: path to custom themes
    include_standard_themes=True,    # include built-in termz themes
)

# In your Textual App.on_mount():
loader.register_themes_in_textual_app(app)
loader.set_previous_theme_in_textual_app(
    app,
    default_theme_name="TERMZ_xplore-blue",
    theme_config_file=Path("~/.config/myapp/theme.json").expanduser(),
)

# When the user changes theme:
loader.save_theme_to_config(app.theme, Path("~/.config/myapp/theme.json").expanduser())
loader.load_theme_css(app.theme, app)

# Cycle through themes with arrow keys:
loader.change_to_next_or_previous_theme(direction=1, app=app)
```

Theme name prefixes:

- Built-in termz themes: `TERMZ_` (e.g. `TERMZ_xplore-blue`)
- Custom themes: `CUSTOM_` (e.g. `CUSTOM_mytheme`)

Both prefixes can be customized via the `ThemeLoader` constructor.

### QuestionScreen

A Textual `ModalScreen` that presents a yes/no dialog and returns a `bool`.

```python
from termz import QuestionScreen, ButtonColor

async def confirm_delete(self):
    answer = await self.app.push_screen_wait(
        QuestionScreen(
            question="Delete this entry?",
            yes_button_color=ButtonColor.ERROR,
            no_button_color=ButtonColor.PRIMARY,
        )
    )
    if answer:
        self.do_delete()
```

`ButtonColor` values: `DEFAULT`, `PRIMARY`, `ERROR`, `SUCCESS`, `WARNING`.

### CustomDataTable

A subclass of Textual's `DataTable` that supports *flexible columns* – columns that automatically fill the remaining width when the terminal is resized.

```python
from termz.tui.custom_widgets.custom_data_table import CustomDataTable

table = CustomDataTable()
col_name = table.add_column("Name", width=20)
col_desc = table.add_column("Description")
table.flexible_columns = [col_desc]  # This column will stretch to fill space
```

### CustomCheckbox

A subclass of Textual's `Checkbox` that shows a `✔` when checked and an empty box when unchecked, instead of the default `X`.

```python
from termz.tui.custom_widgets.custom_checkbox import CustomCheckbox

yield CustomCheckbox("Enable feature", value=True)
```

### CustomSelectionList

A subclass of Textual's `SelectionList` whose items show a `✔` when selected and an empty box when unselected, instead of the default `X`.

```python
from termz.tui.custom_widgets.custom_selection import CustomSelectionList

yield CustomSelectionList(
    ("Option A", "a"),
    ("Option B", "b"),
)
```

### MultiLineFooter

A drop-in replacement for Textual's built-in `Footer` that supports multiple rows of key bindings. Two modes are available:

- **`auto_wrap=True`** (default) – bindings wrap automatically when the row is full.
- **`auto_wrap=False`** – bindings are assigned to rows explicitly via `row_map`.

```python
from termz.tui.custom_widgets.multiline_footer import MultiLineFooter

# Auto-wrap (default)
yield MultiLineFooter()

# Manual row assignment
yield MultiLineFooter(
    auto_wrap=False,
    row_map={
        'quit': 0,
        'save': 0,
        'toggle_dark': 1,
        'help': 1,
    },
)
```

### CustomBindings

Loads keyboard bindings from a YAML file and exposes them as Textual `Binding` objects. Supports global bindings, tab-specific bindings, and screen-specific bindings.

**Group naming conventions:**

| Group name | Scope | Action prefix |
|------------|-------|---------------|
| `_global` | Always visible | none (used as-is) |
| `<name>_tab` | Shown when that tab is active | `<name>_tab_` |
| `<name>_screen` | Shown on that screen | none (used as-is) |

**YAML example (`bindings.yaml`):**

```yaml
_global:
  - key: q
    action: quit
    description: Quit
    priority: true
    row: 1

tasks_tab:
  - key: a
    action: add_task
    description: Add
    row: 0

add_screen:
  - key: escape
    action: cancel
    description: Cancel
    row: 0
```

**Usage:**

```python
from termz.tui.custom_bindings import CustomBindings

bindings = CustomBindings('bindings.yaml', sort_alphabetically=False)

# In your App or Screen:
BINDINGS = bindings.get_bindings()                        # all bindings
BINDINGS = bindings.get_bindings(tab_name='tasks_tab')    # tab-specific + global
BINDINGS = bindings.get_bindings(screen_name='add')       # screen-specific + global

# Row map for MultiLineFooter(auto_wrap=False):
row_map = bindings.get_row_map()

# In check_action to hide tab bindings that don't belong to the active tab:
def check_action(self, action, parameters):
    return bindings.handle_check_action(action, parameters, active_group=self.active_tab)
```

---

## termz.io – IO Utilities

### AppStateStorage

A JSON-backed singleton for persisting small application states (scroll position, last selection, command history, etc.).

```python
from termz import AppStateStorage

# Initialize once (e.g. at startup)
storage = AppStateStorage(package_name="myapp")
# State file is created at ~/.local/state/myapp/state.json

# Read / write simple values
storage.set("last_tab", "settings")
tab = storage.get("last_tab", default_value="home")

# List operations
storage.list_insert("history", 0, "command_1")
storage.edit_list_item("history", 0, "label", "renamed")
storage.move_list_item("history", 0, 2)
storage.delete_list_item("history", 0)
```

Because `AppStateStorage` is a singleton, subsequent calls to `AppStateStorage()` anywhere in the application return the same instance. Supply an explicit `state_file_path` instead of `package_name` for a custom path.

### Database

A lightweight SQLite abstraction.

```python
from termz import Database, Condition, SQLComparisonOperator, SQLOrderByDirection, ColumnOrder

with Database("data.db") as db:
    # Fetch with conditions and ordering
    rows = db.fetch(
        table="tasks",
        columns=["id", "title", "due_date"],
        conditions=[
            Condition("done", SQLComparisonOperator.EQ, 0),
        ],
        orderby=[ColumnOrder("due_date", SQLOrderByDirection.ASC)],
        limit=50,
    )

    # Insert
    inserted = db.insert("tasks", [{"title": "Buy milk", "done": 0}])

    # Update
    db.update("tasks", [{
        "done": 1,
        "@conds": [Condition("id", SQLComparisonOperator.EQ, inserted[0]["id"])],
    }])

    # Delete
    db.remove("tasks", [Condition("id", SQLComparisonOperator.EQ, 42)])

    # Raw SQL
    db.query("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)")
    db.save()
```

### File

Static helpers for file and folder operations.

```python
from termz import File

# List folder contents (optionally filtered by extension and recursive)
items = File.folder_content("./data", extfilter="csv", withsubfolders=True)

# Copy a folder
File.copy_folder("./src_folder", "./dst_folder")

# File extension helpers
ext = File.extension("report.csv")          # "csv"
new_name = File.change_extension("report.csv", "txt")  # "report.txt"
folder = File.path("/home/user/docs/file.txt")          # "/home/user/docs"
```

### Textfile

Simple UTF-8 text file read/write.

```python
from termz import Textfile   # or: from termz.io.textfile import Textfile

content = Textfile.read("notes.txt")
lines   = Textfile.readlines("notes.txt")
Textfile.write("notes.txt", "New content")
```

---

## termz.util – General Utilities

### Logging

```python
from termz import setup_logging
import logging

setup_logging("myapp", level=logging.INFO)
# Writes to ~/.local/state/myapp/app.log
```

### Singleton

A metaclass that enforces the singleton pattern.

```python
from termz import Singleton

class Config(metaclass=Singleton):
    def __init__(self):
        self.debug = False

a = Config()
b = Config()
assert a is b  # True
```

### Datetime

```python
from termz import timestamp_to_date, date_to_timestamp, date_diff, today_timestamp, today_date

ts = date_to_timestamp("01.04.2025")           # German format (default)
ts = date_to_timestamp("2025-04-01", english_format=True)

s  = timestamp_to_date(ts)                     # "01.04.2025"
s  = timestamp_to_date(ts, english_format=True) # "2025-04-01"

days = date_diff(ts1, ts2)                     # difference in days

ts_today = today_timestamp()                   # midnight UNIX timestamp
s_today  = today_date()                        # "02.04.2026"
```

### String

```python
from termz import linewrap, charpos

wrapped = linewrap("A long piece of text that should be wrapped.", linewidth=20)
positions = charpos("hello world", "l")  # [2, 3, 9]
```

### Index Navigation

```python
from termz import next_index

# Navigate a list of 5 items, wrapping around at edges
idx = next_index(current_index=4, max_index=5, direction=1)  # 0  (wraps)
idx = next_index(current_index=0, max_index=5, direction=-1) # 4  (wraps)

# Clamp at boundaries instead of wrapping
idx = next_index(current_index=4, max_index=5, direction=1, loop_behavior=False)  # 4
```

### Validation

```python
from termz import is_number

is_number("3.14")  # True
is_number("abc")   # False
is_number(None)    # False
```

### Debug Decorators

```python
from termz import print_arguments, timing

@print_arguments
def add(a: int, b: int) -> int:
    return a + b

add(3, 5)
# Function add called
# Args: (3, 5)
# Kwargs: {}
# Function add returns: 8


@timing()                  # seconds
@timing(use_ns_timer=True) # nanoseconds
def heavy_computation():
    ...
```

---

## License

MIT
