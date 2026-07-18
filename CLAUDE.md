# CLAUDE.md

Project-specific instructions for termz. The global style guide referenced in `~/.claude/CLAUDE.md` remains authoritative; this file only records what is specific to this repository.

## What this project is

termz is a library, not an application. It is the foundation under termplate, which section 3.2.9 of the style guide names as the template every Textual-based TUI is checked against.

That ordering has a consequence worth stating plainly: a defect here reaches every application built on the toolkit, and it reaches them silently, because applications trust a library rather than testing it. Four of the theme bugs that held up termplate lived in this repository and none of them failed loudly – they just rendered the wrong colours. Prefer failing loudly over carrying on, and prefer a test over a comment.

## Toolchain

All of these must be clean before a change is finished:

```zsh
ruff check .
basedpyright
pytest
```

`ruff format` is deliberately absent. The formatter is not configured, line breaking is hand-made, and `E501` enforces the column limit; the reasoning sits in a comment in `pyproject.toml`. Do not add `[tool.ruff.format]` without deciding that question again.

The binary is `basedpyright`, never `pyright`, even though the configuration section is called `[tool.pyright]`. Its default mode is stricter than the `strict` the configuration asks for, which is why the four remaining suppressions read as inert – they describe real properties of this code and keep a switch to `recommended` a one-line change.

Coverage runs through `--cov` in `addopts`. The gate in `[tool.coverage.report]` holds the level currently reached: raise `fail_under` when a module gains tests, never lower it to make a run pass.

## Architecture

Four sub-packages, each a coherent purpose rather than a layer:

- `cli` – styled console output through Rich.
- `io` – SQLite, JSON application state, files and text files.
- `tui` – Textual helpers: theme loading, key bindings, custom widgets.
- `util` – dates, strings, index arithmetic, logging, debugging decorators.

The public API of each package is re-exported through `from .module import *` in its `__init__.py`, as section 3.2.2 requires. That has a consequence which has already caused a defect: a module without `__all__` re-exports its own imports too. `termz/util/datetime.py` re-exported the `datetime` class over the submodule of the same name, so `import termz.util.datetime` handed back the class. Every module declares `__all__`, and a new one has to as well – `tests/test_public_api.py` fails otherwise, and also checks that no borrowed name such as `json` or `Path` reaches the package namespace.

## The defect this repository keeps producing

Mutable class attributes shared by every instance. It has been found and fixed four times: `ThemeLoader._theme_names` and `_theme_data`, the four registries in `CustomBindings`, `CustomDataTable.flexible_columns` and `AppStateStorage._json_dict`. Each time the symptom was different and none of them raised.

Declare instance attributes annotated at class level and assign them in `__init__`, as section 3.2.5 says. `RUF012` catches the annotated-with-a-value form; it does not catch every shape, so this stays worth looking for by hand.

## Conventions particular to this repo

- No boolean parameter selects behaviour anywhere in the public API. Section 1.1.2 is enforced by `FBT`, and the established answers are two named functions (`next_index` and `clamped_index`, `timing` and `timing_ns`), a classmethod factory (`ThemeLoader.custom_only`, `CustomBindings.sorted_by_key`) or an enum (`DateFormat`). Pick whichever fits the parameter; a format selector is an enum, a behaviour switch is two functions.
- Domain exceptions live in `termz/io/errors.py`. A library that calls `sys.exit()` or prints an error leaves its caller no way to react – `AppStateStorage` did both until recently.
- Diagnostics go to a module logger with lazy `%`-formatting, never to `print`. `termz/cli/output.py` is the one module where printing is the product, and it carries a per-file ignore saying so.
- Every SQL statement binds its values as parameters, and every identifier passes `_quoted_table` or `_quoted_column`, which check it against the schema of the open database before quoting it. The `# noqa: S608` markers state exactly what the rule cannot see. There is no other way to build a statement here.
- A theme is identified by the `name` in its `theme.py` plus its registration prefix; the directory it lives in carries no meaning. Theme modules are imported by file path, never as a package – importing them by folder name made the first folder loaded in a process shadow every later one of the same name.
- Textual reads annotations at runtime, so type-only imports stay at module level under `termz/tui/`. The per-file ignore for `TC002` and `TC003` in `pyproject.toml` is that rule, not an oversight.
- hatchling ships everything inside the package directory, so runtime data (`py.typed`, the theme `.css` and `theme.py` files) needs no `package-data` entry. Every package directory does need an `__init__.py`, or it becomes an implicit namespace package that a stricter packaging tool would drop.
- termplate is the only consumer. A breaking change is pulled through it in the same pass, and its suite has to be green before the change is finished.
- `TODO.md` tracks deferred work, including findings that were deliberately left alone and why. Read it before starting, so the same gap is not filled twice in different ways.
