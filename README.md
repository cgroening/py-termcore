# termcore

Terminal utilities for CLI, TUI, IO and general use.

## Overview

**termcore** is a Python library that bundles reusable building blocks for terminal applications. It is organized into four sub-packages:

| Package | Contents |
|---------|----------|
| `termcore.cli` | Styled console output via [Rich](https://github.com/Textualize/rich) |
| `termcore.tui` | [Textual](https://github.com/Textualize/textual) TUI helpers – theme loading, custom widgets, modal screens |
| `termcore.io` | SQLite database abstraction, JSON app-state storage, file utilities |
| `termcore.util` | Datetime helpers, string utilities, singleton metaclass, debug decorators, logging setup |

## Requirements

- Python >= 3.12
- [`rich`](https://pypi.org/project/rich/)
- [`textual`](https://pypi.org/project/textual/) (required for `termcore.tui`)

## Installation

```bash
pip install termcore
```

## termcore.cli – Styled CLI Output

Provides helpers for printing color-coded panels using Rich and for clearing terminal output.

```python
from termcore import print_error, print_warning, print_success, print_info, clear_lines

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

## termcore.tui – Textual TUI Helpers

### ThemeLoader

Dynamically loads and registers [Textual](https://github.com/Textualize/textual) themes from a folder. Each theme lives in its own sub-directory and must expose a `TEXTUAL_THEME` variable of type `textual.theme.Theme`. Optional `.css` / `.tcss` files in the same folder are loaded automatically when the theme is activated.

A theme is identified by the `name` of its `TEXTUAL_THEME` plus the prefix it is registered under – the name of its directory carries no meaning and is free to differ. A theme without a stylesheet is equally valid; ten of the built-in themes below ship none. Each theme folder is read on its own, so an app can register several loaders and its own themes never collide with the ones the toolkit brings.

termcore ships 16 built-in themes:

`classic-black-saturated`, `classic-black-v1`, `classic-black-v2`, `classic-blue`, `compact-gray`, `mnml-black`, `mnml-deepblack`, `pure-amber`, `pure-black`, `pure-blue`, `pure-green`, `pure-sweet16`, `xplore-black`, `xplore-blue`, `xplore-blue-muted`, `xplore-teal`

```python
from pathlib import Path
from termcore import ThemeLoader

loader = ThemeLoader("themes")              # bundled themes plus that folder
loader = ThemeLoader.custom_only("themes")  # only that folder

# In your Textual App.on_mount():
loader.register_themes_in_textual_app(app)
loader.set_previous_theme_in_textual_app(
    app,
    default_theme_name="TERMCORE_xplore-blue",
    theme_config_file=Path("~/.config/myapp/theme.json").expanduser(),
)

# When the user changes theme:
loader.save_theme_to_config(app.theme, Path("~/.config/myapp/theme.json").expanduser())
loader.load_theme_css(app.theme, app)

# Cycle through themes with arrow keys:
loader.change_to_next_or_previous_theme(direction=1, app=app)
```

Theme name prefixes:

- Built-in termcore themes: `TERMCORE_` (e.g. `TERMCORE_xplore-blue`)
- Custom themes: `CUSTOM_` (e.g. `CUSTOM_mytheme`)

Both prefixes can be customized via the `ThemeLoader` constructor.

### QuestionScreen

A Textual `ModalScreen` that presents a yes/no dialog and returns a `bool`.

```python
from termcore import QuestionScreen, ButtonColor

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
from termcore.tui.custom_widgets.custom_data_table import CustomDataTable

table = CustomDataTable()
col_name = table.add_column("Name", width=20)
col_desc = table.add_column("Description")
table.flexible_columns = [col_desc]  # This column will stretch to fill space
```

### CustomCheckbox

A subclass of Textual's `Checkbox` that shows a `✔` when checked and an empty box when unchecked, instead of the default `X`.

```python
from termcore.tui.custom_widgets.custom_checkbox import CustomCheckbox

yield CustomCheckbox("Enable feature", value=True)
```

### CustomSelectionList

A subclass of Textual's `SelectionList` whose items show a `✔` when selected and an empty box when unselected, instead of the default `X`.

```python
from termcore.tui.custom_widgets.custom_selection import CustomSelectionList

yield CustomSelectionList(
    ("Option A", "a"),
    ("Option B", "b"),
)
```

### MultiLineFooter

A drop-in replacement for Textual's built-in `Footer` that supports multiple rows of key bindings. Which of its two modes applies follows from whether groups are passed:

- **without `groups`** – the keys wrap onto a new row whenever the current one is full.
- **with `groups`** – each declared group becomes one row, its label printed in a column on the left and its keys separated by ` · `. A group too wide for the terminal wraps onto continuation rows whose label cell stays blank, so the keys line up under the keys rather than under the label.

```python
from termcore.tui.custom_bindings import CustomBindings
from termcore.tui.custom_widgets.multiline_footer import MultiLineFooter

bindings = CustomBindings("bindings.yaml")

# Wrap on width
yield MultiLineFooter()

# One row per group, in the order the YAML file declares them
yield MultiLineFooter(groups=bindings.get_groups())
```

```text
Tasks:       a Add · d Done
Appearance:  w Previous Theme · s Next Theme
App:         ? Help · q Quit
```

`get_groups()` returns every declared group, not only the ones belonging to the current screen. A group whose bindings are not active right now renders no row at all, so the same call serves every screen.

### HelpScreen

The overlay style guide section 1.8 asks every terminal interface for: every shortcut, grouped, with a fuzzy search over them. It reads the same groups the footer does, so a binding cannot appear in one and be missing from the other.

```python
from termcore.tui.binding_groups import active_actions
from termcore.tui.help_screen import HelpScreen

def action_help(self) -> None:
    # Snapshot before the push: afterwards `self.screen` is the modal.
    active = active_actions(self.screen)
    self.push_screen(HelpScreen(bindings.get_groups(), active))
```

It opens listing every declared shortcut. `ctrl+t` narrows the list to the bindings that would actually fire where the overlay was opened, which is what the snapshot above feeds; `escape` and `?` close it. Matching is Textual's own `Matcher`, the fuzzy search behind its command palette, so `ntm` finds "next theme".

### CustomBindings

Loads keyboard bindings from a YAML file and exposes them as Textual `Binding` objects. Supports global bindings, tab-specific bindings, and screen-specific bindings.

Two words are kept apart and are not interchangeable. A **scope** is a top-level key of the file: it decides when a binding is visible and how its action is named. A **group** is one labelled footer row inside a scope: it decides only how the footer and the help overlay lay the bindings out. Grouping is optional.

**Scope naming conventions:**

| Scope name | Visibility | Action prefix |
|------------|------------|---------------|
| `_global` | Always visible | none (used as-is) |
| `<name>_tab` | Shown when that tab is active | `<name>_tab_` |
| `<name>_screen` | Shown on that screen | none (used as-is) |

The order of the file is the order of the footer, without exception. Nothing is re-sorted on the way out, so a scope moved in the file moves its rows - which is why `_global` usually belongs at the bottom.

**YAML example (`bindings.yaml`):**

```yaml
tasks_tab:
  - group: Tasks
    bindings:
      - key: a
        action: add_task
        description: Add
      - key: d
        action: mark_done
        description: Done
  - key: z            # no group: its own row, no label
    action: zoom
    description: Zoom

_global:
  - group: App
    bindings:
      - key: q
        action: quit
        description: Quit
        priority: true
```

An entry carrying `bindings` is a group; an entry carrying `key` is a single binding. Both may be mixed inside one scope, and consecutive single bindings share one unlabelled row.

**Usage:**

```python
from termcore.tui.custom_bindings import CustomBindings

bindings = CustomBindings("bindings.yaml")   # file order, always

# In your App or Screen:
# On the App: globals dispatch as declared
BINDINGS = bindings.get_bindings()                      # every tab + global
BINDINGS = bindings.get_bindings(tab_name="tasks_tab")  # one tab + global

# On a Screen: globals are prefixed with `app.` so they dispatch on the App
BINDINGS = bindings.get_screen_bindings()               # every tab + global
BINDINGS = bindings.get_screen_bindings("add")          # that screen + global

# Footer rows and help overlay, both from the same call:
groups = bindings.get_groups()

# In check_action to hide tab bindings that don't belong to the active tab:
def check_action(self, action, parameters):
    return bindings.handle_check_action(
        dispatch_name(action), parameters, active_scope=self.active_tab
    )
```

## termcore.io – IO Utilities

### AppStateStorage

A JSON-backed singleton for persisting small application states (scroll position, last selection, command history, etc.).

```python
from termcore import AppStateStorage

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

Values are always bound as query parameters, never formatted into the statement, so a value can never be read as SQL. Identifiers cannot be parameters, so a table or column name is checked against the schema of the open database and quoted before it is used; a name that is not part of the schema raises `UnknownIdentifierError` instead of reaching the database. `update` and `remove` refuse an empty condition list with `EmptyConditionsError` rather than rewriting or emptying the whole table.

```python
from termcore import Database, Condition, SQLComparisonOperator, SQLOrderByDirection, ColumnOrder

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

    # Update - returns the number of changed rows
    changed = db.update(
        "tasks",
        {"done": 1},
        [Condition("id", SQLComparisonOperator.EQ, inserted[0]["id"])],
    )

    # Delete
    db.remove("tasks", [Condition("id", SQLComparisonOperator.EQ, 42)])

    # Raw SQL - pass values through params, never format them into the string
    db.query("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER)")
    db.query("INSERT INTO tasks (title) VALUES (?)", ["Buy bread"])
    db.save()
```

Leaving the `with` block commits, unless it is left through an exception, in which case the transaction is rolled back. Available comparison operators are `LT`, `LE`, `EQ`, `NE`, `GE`, `GT`, `LIKE`, `IS_NULL` and `IS_NOT_NULL`; the last two take no value.

### File

Static helpers for file and folder operations.

```python
from termcore import File

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
from termcore import Textfile   # or: from termcore.io.textfile import Textfile

content = Textfile.read("notes.txt")
lines   = Textfile.readlines("notes.txt")
Textfile.write("notes.txt", "New content")
```

## termcore.util – General Utilities

### Logging

```python
from termcore import setup_logging
import logging

setup_logging("myapp", level=logging.INFO)
# Writes to ~/.local/state/myapp/app.log
```

### Singleton

A metaclass that enforces the singleton pattern.

```python
from termcore import Singleton

class Config(metaclass=Singleton):
    def __init__(self):
        self.debug = False

a = Config()
b = Config()
assert a is b  # True
```

### Datetime

```python
from termcore import DateFormat, timestamp_to_date, date_to_timestamp, date_diff, today_timestamp, today_date

ts = date_to_timestamp("01.04.2025")           # German format (default)
ts = date_to_timestamp("2025-04-01", DateFormat.ISO)

s  = timestamp_to_date(ts)                     # "01.04.2025"
s  = timestamp_to_date(ts, DateFormat.ISO)     # "2025-04-01"

days = date_diff(ts1, ts2)                     # difference in days

ts_today = today_timestamp()                   # midnight UNIX timestamp
s_today  = today_date()                        # "02.04.2026"
```

### String

```python
from termcore import linewrap, charpos, cell_width, str_with_fixed_width

wrapped = linewrap("A long piece of text that should be wrapped.", linewidth=20)
positions = charpos("hello world", "l")  # [2, 3, 9]

cell_width("abc")     # 3
cell_width("日本語")  # 6 - one CJK glyph occupies two terminal cells

# Exactly `width` terminal cells, truncated with an ellipsis or padded
str_with_fixed_width("a long value", 8)             # "a long …"
str_with_fixed_width("a long value", 8, "right")    # "…g value"
str_with_fixed_width("ok", 8, "center")             # "   ok   "
str_with_fixed_width("日本語テキスト", 8)           # "日本語… "
```

Widths are counted in terminal cells rather than in code points, so a column stays aligned whatever the data contains. A double-width glyph cannot be split, so where one would straddle the boundary the result is padded with a space to reach the requested width exactly.

### Index Navigation

```python
from termcore import next_index, clamped_index

# Navigate a list of 5 items, wrapping around at edges
idx = next_index(current_index=4, length=5, direction=1)  # 0  (wraps)
idx = next_index(current_index=0, length=5, direction=-1) # 4  (wraps)

# Clamp at the boundaries instead of wrapping
idx = clamped_index(current_index=4, length=5, direction=1)  # 4

# An empty list has no valid index
idx = next_index(current_index=0, length=0)  # 0
```

### Validation

```python
from termcore import is_number

is_number("3.14")  # True
is_number("abc")   # False
is_number(None)    # False
```

### Debug Decorators

```python
from termcore import print_arguments, timing, timing_ns

@print_arguments
def add(a: int, b: int) -> int:
    return a + b

add(3, 5)
# Logged at debug level on the `termcore.util.debug` logger:
#   Function add called
#   Args: (3, 5)
#   Kwargs: {}
#   Function add returns: 8


@timing()     # seconds
@timing_ns()  # nanoseconds
def heavy_computation():
    ...
```

The decorators log at debug level rather than printing, so enable that logger to see them.

## Development

```zsh
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

ruff check .     # linting; the rule set is the style guide's baseline
basedpyright     # strict type checking
pytest           # tests, with coverage
```

The ruff formatter is deliberately not configured: line breaking is hand-made and the 80-column limit is enforced by `E501`.

## License

MIT
