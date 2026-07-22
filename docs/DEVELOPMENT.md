# Development

Developer notes for working on termcore. For a usage overview see [`README.md`](../README.md); the coding conventions, the toolchain gate and the defects this repository keeps producing are in [`CLAUDE.md`](../CLAUDE.md); deferred work is in [`TODO.md`](../TODO.md); [`CLEAN-UP.md`](CLEAN-UP.md) is the checklist for a structured review pass.

termcore is a reusable toolkit for terminal applications. It depends on `rich`, `textual` and `pyyaml` and never on application types, so any program can build on it. There is exactly one consumer today, the `termplate` template, and it is also the only place where most of this code runs in anger.

## Project layout

Four sub-packages, each a coherent purpose rather than a layer. Every module declares an `__all__`; a name that is not in one is not public.

```text
termcore/
  py.typed          the marker that makes the annotations visible to consumers

  cli/
    output.py       styled console output through Rich: print_error, print_warning,
                    print_success, print_info, print_panel, print_custom_panel,
                    clear_lines, get_console

  io/
    database.py     SQLite wrapper: Database plus Condition, ColumnOrder and the
                    three operator enums. Values are bound as parameters,
                    identifiers checked against the schema and quoted
    app_state_storage.py  AppStateStorage, a JSON-backed key/value store for
                    persisted application state; a Singleton
    file.py         File and FolderItem: reading, writing and walking folders
    textfile.py     Textfile: read a text file whole or line by line, write it back
    errors.py       the domain exceptions of this package: DatabaseError,
                    UnknownIdentifierError, EmptyConditionsError, AppStateError,
                    StateFileError

  tui/
    theme_loader.py     ThemeLoader: discovers theme directories, registers their
                        themes under a prefix and swaps their stylesheets
    custom_bindings.py  CustomBindings: key bindings declared in YAML, composed
                        per tab and per screen
    question_screen.py  QuestionScreen, a modal yes/no dialog, and ButtonColor
    themes/             the sixteen bundled themes, one directory each
    custom_widgets/
      footer_rows.py       Row layout for the footer: columns, wrapping
      multiline_footer.py  MultiLineFooter: a Footer that spans several rows
      custom_data_table.py CustomDataTable: a DataTable with stretching columns
      custom_checkbox.py   CustomCheckbox: a check mark instead of an X
      custom_selection.py  CustomSelectionList: the same for a selection list

  util/
    string.py       cell_width, str_with_fixed_width, linewrap, charpos and the
                    alignment constants. Widths are terminal cells, not code points
    datetime.py     timestamp and date-string conversions plus the DateFormat enum
    index.py        next_index (wrapping) and clamped_index (stopping)
    logger.py       setup_logging, for an application to install
    debug.py        print_arguments, timing and timing_ns decorators
    singleton.py    the Singleton metaclass
    validation.py   is_number
    version.py      get_version, from the installed metadata or pyproject.toml

tests/              mirrors the package tree; every directory has an __init__.py
```

## Reusing what is already here

Section 1.2.7 of the style guide asks that an existing solution be found before a new one is written, and a toolkit without a map makes that hard. Before writing a helper, check this list:

- **Fixed-width output.** `str_with_fixed_width` truncates or pads to an exact number of terminal cells, and `cell_width` measures. Never use `len()` for a column: a CJK glyph is two cells wide and a combining mark is none, so counting characters is what pushes a column out of alignment.
- **List navigation.** `next_index` wraps at both ends, `clamped_index` stops at them. Section 1.6 requires wrapping selection lists, and both return 0 for an empty list rather than raising.
- **Themes.** `ThemeLoader` finds, registers and switches them. A theme is identified by the `name` in its `theme.py`, never by its directory.
- **Key bindings.** `CustomBindings` reads them from YAML. `get_bindings` is for the App, `get_screen_bindings` for a Screen, and `get_groups` feeds both `MultiLineFooter` and `HelpScreen`. Match bindings by action through `dispatch_name`, never by raw string: a Screen renames a global action to `app.<action>`, and comparing the two forms directly silently drops every global binding.
- **Storage.** `Database` for SQLite, `AppStateStorage` for a small JSON state file. Neither wants a wrapper around it.
- **New exceptions** go into `termcore/io/errors.py` or a sibling `errors` module, deriving from `Exception`, never a bare `raise Exception(...)`.
- **Writing a file that must not be lost.** `Textfile.write_atomic` writes to a sibling temporary file, syncs it and renames it over the target, so a crash leaves either the old content or the new one. Plain `write` truncates first: for anything rewritten whole - a store, a state file - that turns an interrupted write into total loss, not a lost last change.
- **Text wrapping** is `linewrap`; **version lookup** is `get_version`; **logging setup** is `setup_logging`, which an application calls once and which takes a `log_dir` so an app that resolves its own paths keeps that in one place.

## Textual behaviour worth knowing

### A RuntimeWarning about an un-awaited coroutine on exit

Quitting an application sometimes prints:

```text
textual/drivers/linux_driver.py:397: RuntimeWarning: coroutine
'MessagePump._post_message' was never awaited
  self._app.call_later(
```

The line it names is not where the coroutine was created. `linux_driver.py:397` is `self._app.call_later(...)` in the input thread's `except BaseException:` branch, and that path calls the synchronous `post_message`, which creates no coroutine at all. The hint in the message - "Enable tracemalloc to get the object allocation traceback" - says as much: what is shown is the frame that happened to be running when the garbage collector finalised an orphan.

The orphan comes from one of three places in the driver, all of the same shape:

```python
asyncio.run_coroutine_threadsafe(
    self._app._post_message(event),   # the coroutine is created here...
    loop=loop,                        # ...and handed to a loop that may be closed
)
```

They are `linux_driver.py:232` inside `send_size_event`, which is registered as the SIGWINCH handler, `linux_driver.py:295` for `SignalResume` after a SIGTSTP, and `driver.py:74` in `Driver.send_message`. Python evaluates the argument first, so the coroutine object exists before `run_coroutine_threadsafe` gets the chance to refuse it. Once the loop is closed that call raises and the coroutine is dropped un-awaited.

Hence "sometimes": it needs a terminal event in the sliver between the loop closing and the process ending. Leaving the alternate screen restores the terminal's previous size, which frequently raises SIGWINCH by itself, so whether it happens depends on the terminal, on timing, and on whether the window was resized.

A second failure hides in the same message. That line 397 runs at all means the input thread died with an exception during teardown; its attempt to report that through `call_later` returns `False` because the message pump is already closing, so the panic is swallowed.

None of it is ours. Neither termcore nor termplate has a thread, a worker or a signal handler, and this driver only runs in a real terminal - tests use `HeadlessDriver`, which is why neither suite ever sees it although both set `filterwarnings = ["error"]`. There is no relevant entry in Textual's changelog between 8.1.1 and 8.2.8, so upgrading does not help. It is printed after the application has exited and is left alone deliberately: a warnings filter in the entry point would swallow the same message when it one day comes from our own code.

## Common commands

```zsh
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

The gate that has to be clean before a change is finished is in [`CLAUDE.md`](../CLAUDE.md): `ruff check .`, `basedpyright`, `pytest`. Coverage runs inside `pytest` and fails below the threshold in `pyproject.toml`.

## Exercising the library

termcore has no entry point. There is nothing to run, which is why the checks below matter more than they would in an application.

- **Through the consumer.** termplate is the only one. Point it at the working copy and run its suite, then start the app:

  ```zsh
  cd ../../templates/termplate
  source .venv/bin/activate
  uv pip install -e ../../libs/termcore
  pytest
  tp tui
  ```

  Without that editable install it resolves the published release and none of your changes are exercised.

- **Through a Textual harness.** Anything under `tui/` can be driven headlessly:

  ```python
  app: App[None] = App()
  async with app.run_test() as pilot:
      await pilot.pause()
      await pilot.press("s")
  ```

- **Through an in-memory database.** `Database(":memory:")` needs no file and no cleanup.

## Testing

Four tiers, all of them already in use:

- **Pure functions** are called directly. Everything in `util/` is testable this way, and `tests/util/test_datetime.py` pins the process time zone with `monkeypatch.setenv("TZ", ...)` plus `time.tzset()`, because those conversions read the local zone by design.
- **Storage** runs against `Database(":memory:")`. `tests/io/conftest.py` provides `db`, an empty database holding one table, and `filled_db`, the same with three rows.
- **The TUI** runs through `App.run_test()`. `tests/tui/conftest.py` provides `theme_root` and `make_theme` for building theme directories under `tmp_path`, and `write_bindings` for a YAML binding file. Use them rather than writing files by hand.
- **The consumer's suite** covers what only appears in an assembled application. A binding that no longer resolves and a theme that never activates both fail silently here and visibly there.

`tests/test_public_api.py` guards the shape of the package itself: every module has an `__all__`, no borrowed import reaches the package namespace, and `termcore.util.datetime` stays the module rather than the class.

`tests/test_docs.py` guards this file and its neighbour: every path named in backticks exists and every relative link resolves.

## Adding a theme

1. Create `termcore/tui/themes/<name>/theme.py` with a module-level `TEXTUAL_THEME = Theme(...)`. The directory name is free; the `name` inside is the identity.
2. Add `style.css` or `style.tcss` beside it if the theme needs more than colours. Ten of the bundled themes have none, which is fine.
3. Use theme variables in the stylesheet, never hex values; those belong in `theme.py` alone.
4. Update the theme list in [`README.md`](../README.md), which names all sixteen.

## Adding a widget

1. Put it in `termcore/tui/custom_widgets/<name>.py`, one widget per file, and give the module an `__all__`.
2. Take what you need through the constructor. No global state and no singletons in the UI.
3. Reuse `cell_width` and `str_with_fixed_width` for anything column-shaped, and `next_index` or `clamped_index` for anything navigable.
4. Re-export it from `termcore/tui/__init__.py`.
5. Add tests through `App.run_test()`, and raise the coverage gate if the total moved.
6. Document it in [`README.md`](../README.md) and add its module line to the tree above.

## Releasing

The 0.1.1 that went out under the old name `termz` does not contain `util/version.py`, which makes termplate's dependency on it untrue for anyone but this machine. That happened because the artefact was never opened. Section 1.2.9 of the style guide asks for the built package to be checked rather than the source tree, so:

1. Raise `version` in `pyproject.toml`.
2. Close the `[Unreleased]` section in [`CHANGELOG.md`](../CHANGELOG.md) under the new version and date. Breaking changes belong at the top of it.
3. Run the full gate: `ruff check .`, `basedpyright`, `pytest`.
4. Build: `python -m build`.
5. Look inside: `unzip -l dist/*.whl`. Every sub-package, `py.typed`, and the theme `.py` and `.css` files have to be there.
6. Install the wheel into a throwaway environment and import it:

   ```zsh
   uv venv "$(mktemp -d)/termcore-check" && source "$_/bin/activate"
   uv pip install dist/*.whl
   python -c "import termcore; print(termcore.get_version('termcore'))"
   ```

7. Run termplate's suite against the built wheel rather than the editable checkout, so the dependency is exercised as a consumer sees it.
8. Publish, then tag the commit.
