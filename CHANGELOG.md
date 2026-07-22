# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] – 2026-07-22

### Added

- `Textfile.write_atomic`, which writes through a synced temporary file and a rename. `AppStateStorage`, `ThemeLoader` and any consumer rewriting a file whole now keep their old content when a write is interrupted; a plain write truncates first, so a crash between truncating and writing loses everything rather than the last change
- `setup_logging` takes a `log_dir`, so an application that resolves its own paths does not have a second resolver behind its back. Its default now follows `XDG_STATE_HOME` instead of hard-coding `~/.local/state`
- `AppHeader` posts `TabSelected` when a tab label is clicked. The header does not switch anything itself - it does not own the content - and only inactive tabs carry the click, because Textual restyles anything clickable with its link colour and that would flatten the active tab to the same grey as the rest

- `tui/binding_groups.py`: `BindingGroup`, the labelled row of shortcuts that the footer and the help overlay both render from, plus `active_actions` to snapshot what is bound on a screen and `dispatch_name` to strip the `app.` prefix a Screen adds
- `CustomBindings.get_groups`, returning every declared group in the order the YAML file declares it. It replaces both row maps, and the defect they invited disappears with them: there is no longer a pair of calls that can be mismatched
- A `group` entry in the binding YAML. A scope may now hold groups, single bindings, or both; consecutive single bindings share one unlabelled row. Grouping is optional and adds no ceremony where it is not wanted
- `tui/help_screen.py`: `HelpScreen`, the overlay section 1.8 of the style guide asks for - every shortcut, grouped, with a fuzzy search over them and a `ctrl+t` toggle between all bindings and the ones currently active. Matching uses Textual's own `Matcher` rather than a hand-written one
- `tui/help_rows.py`: the filtering and row order behind the overlay, testable without an application
- A second file of scope display names, passed to `CustomBindings` as `scopes_file`. Scope names such as `tasks_tab` are identifiers; this maps them to the words people read. `scope_title` resolves one, `BindingGroup.scope_title` carries it, and a title naming no scope is reported - nothing else would ever notice it
- `display_scope`, which falls back to the raw scope name where no title was declared. The fallback is meant to look unfinished rather than invent a heading nobody chose
- `tui/custom_widgets/footer_rows.py`: the footer's arithmetic - label column width, key width and wrapping - split out so it can be tested without an application and so `multiline_footer.py` stays inside the file-size limit
- `tui/custom_widgets/app_header.py`: `AppHeader`, a header carrying the application name in its own column and the tabs after it, wrapping onto further rows whose brand cell is blank but as wide. Textual's `Header` is fixed at one line (three with `-tall`) with three hard-wired slots, and `Tabs` scrolls rather than wraps, so neither could serve
- `tui/custom_widgets/tab_rows.py`: the header's packing, testable without an application
- `tui/custom_widgets/status_bar.py`: `StatusBar`, one line with standing information on the left and a passing message on the right. Textual has no status widget; `App.notify` covers only the passing half, as a box that expires on a timer
- A `key` field in the scopes file, and `scope_key`, `get_tab_scopes` and `get_tab_bindings` to read it. Declaring a key is what makes a scope a tab: the key selects it, the header prints it, and the order of the file is the order of the bar
- The first tests for `MultiLineFooter`, which had none: row order, separator count, label alignment, wrapping at a narrow width, and that clicking a key still runs its action

### Changed

- **Breaking.** The `row` field is gone, and with it `CustomBindings.get_row_map`, `get_screen_row_map` and the `row_map` parameter of `MultiLineFooter`. A group is now one row, so a second way to assign rows could only contradict the first
- **Breaking.** `CustomBindings.sorted_by_key` is gone, along with the alphabetical sorting it enabled. The order of the YAML file is now the order of the footer, without exception
- **Breaking.** `MultiLineFooter` no longer takes `auto_wrap`. Passing `groups` selects the grouped layout; omitting it wraps on width, which is what the old default did
- **Breaking.** `handle_check_action`'s keyword argument `active_group` is now `active_scope`. The word "group" now means a footer row throughout, and what it used to mean - a top-level key of the YAML file - is called a scope
- The help overlay groups on two levels: the scope heads the section, the group is the level below it, and a scope holding a single group prints no group heading at all. The footer keeps its one-dimensional layout - the two surfaces answer different questions, which is why clibase gives them separate tables as well
- **Breaking.** The scopes file maps each scope to a mapping of `title` and optional `key`, where it previously mapped straight to the title. One shape covers both a plain heading and a tab
- **Breaking.** `HelpScope` is now `HelpCoverage` and `HelpRequest.scope` is `coverage`. With the overlay grouping by scope, the old name meant two things at once, which is exactly the ambiguity the group/scope split had just removed
- The footer prints group labels in a left column of shared width, keys separated by ` · `. A group too wide to fit wraps onto continuation rows whose label cell stays blank, so the keys align under the keys rather than under the label
- The command palette key's width is now reserved, so the last row can no longer wrap into the space it is docked in
- `setup_logging` installs a file handler only, and now says so. Its docstring claimed "file and console logging" while installing neither a console handler nor wanting one: a console handler writes into the terminal the application is drawing on
- The docstring layout rule of style guide 3.2.4 is enforced in the test suite as well. `tests/**` ignored the whole `D` group, so the one rule that is about layout rather than about requiring a docstring was off there too; the ignore is now `D1`
- Text fields are read strictly: a `key`, `action` or `description` that YAML resolved to a boolean is dropped with a warning naming the fix, instead of rendering `False` as a label
- Widths are measured in terminal cells rather than characters, so a CJK label no longer pushes the footer out of alignment

## [0.2.0] – 2026-07-19

### Added

- `util/version.py`: New utility module to retrieve the package version via `importlib.metadata` with a fallback to `pyproject.toml`
- First test suite, covering `tui/theme_loader.py`, together with the pytest, coverage and dev-dependency setup the project was missing
- Test suites for `tui/custom_bindings.py`, `io/database.py`, `util/datetime.py`, `util/index.py` and `util/string.py`, which completes the list of modules named in `TODO.md`
- `io/errors.py`: `DatabaseError` and its two subclasses `UnknownIdentifierError` and `EmptyConditionsError`, the project's first domain exceptions
- `SQLComparisonOperator`: `NE`, `LIKE`, `IS_NULL` and `IS_NOT_NULL`. There was previously no way to express "not equal" at all
- `py.typed`. Without the marker a consumer's type checker treated the whole package as untyped and degraded every import to `Any`
- A `[tool.ruff]` section with the rule set from section 3.2.1 of the style guide, and `typeCheckingMode = "strict"` for basedpyright. The library was previously linted on ruff's defaults, which select no rules and enforce no line length
- `io/errors.py`: `AppStateError` and `StateFileError`
- `termcore/tui/custom_widgets/__init__.py`. The directory was an implicit namespace package, which is one packaging tool away from being dropped from the wheel entirely
- `clamped_index`, `timing_ns`, `File.folder_content_recursive`, `ThemeLoader.custom_only`, `CustomBindings.sorted_by_key`, `CustomBindings.get_screen_bindings` and `CustomBindings.get_screen_row_map`, each replacing a boolean parameter (section 1.1.2)
- `DateFormat`, an enum replacing the `english_format` flag of the datetime helpers
- `cell_width`, which counts the terminal cells a string occupies rather than its code points
- An `__all__` in every module, so that `from termcore import *` carries the public API instead of every module's own imports. The star export shrank from 141 names to 85

### Changed

- The project is now called `termcore`. This is a breaking change on three levels: the distribution on PyPI (`pip install termcore`), the import path (`from termcore.tui.theme_loader import ThemeLoader`), and the registration prefix of the bundled themes, which is `TERMCORE_` instead of `TERMZ_`. A theme name stored in a consumer's config file therefore no longer resolves; `ThemeLoader.set_previous_theme` reports this and falls back to the default rather than failing. The `termz` releases on PyPI are not maintained further
- `ThemeLoader`: The keyword argument `termz_theme_prefix` is now `termcore_theme_prefix`, and the constant `DEFAULT_TERMZ_THEME_PREFIX` is `DEFAULT_TERMCORE_THEME_PREFIX`
- `CustomBindings`: Global bindings are no longer prefixed with `*`
- Updated colors of Textual themes `compact-gray` and `mnml-deepblack`
- `ThemeLoader`: A theme is now identified by the `name` in its `theme.py` plus its registration prefix. The directory name is no longer used as a key, so it may differ freely, and a standard and a custom theme may share a name
- `ThemeLoader`: Theme modules are imported by file path instead of through `sys.path`, so loading no longer alters the interpreter's import state
- `ThemeData`: Now frozen, and its redundant `name` field was removed
- `Database`: Values are bound as query parameters instead of being formatted into the statement, and identifiers are checked against the schema of the open database and quoted. Neither a value nor a name can be read as SQL any more
- `Database.update`: Takes the table, the new values and the conditions as three arguments, replacing the list of dictionaries carrying the conditions under an `@`-prefixed key. It now returns the number of changed rows
- `Database.remove`: Returns the number of deleted rows
- `Database.query`: Takes an optional `params` sequence, so callers never have to format values into the statement themselves
- `Database`: Leaving a `with` block commits, or rolls back if the block is left through an exception. It previously closed the connection without committing, so writes made through `query()` were lost
- `Database`: `debug_mode` writes to the module logger at debug level instead of printing to stdout
- `next_index`: The `max_index` parameter is now called `length`. It was a length in both the code and the docstring, and the old name invited an off-by-one
- `util/datetime`: Every conversion states the local time zone instead of leaving it implied. Results are unchanged on a given machine
- `str_with_fixed_width`: The alignment is validated before the text length is looked at, so an invalid value is rejected either way
- Every boolean parameter that selected behaviour is gone, replaced by a second named function, a factory or an enum: `next_index(loop_behavior=)`, `timing(use_ns_timer=)`, `File.folder_content(withsubfolders=)`, `ThemeLoader(include_standard_themes=)`, `CustomBindings(sort_alphabetically=)`, `get_bindings(for_screen=)`, `get_row_map(for_screen=)` and `english_format=` on the five datetime helpers. All of these are breaking
- `AppStateStorage`: A failure to read, create or write the state file raises `StateFileError` instead of printing a message and calling `sys.exit()`. A library taking the whole process down left the caller no way to react
- `termcore.util.debug`: The decorators log at debug level through a module logger instead of printing to stdout
- File and directory handling moved from `os.path` to `pathlib` throughout
- `str_with_fixed_width` counts terminal cells instead of code points, so a column holding CJK text or emoji stays aligned. A double-width glyph cannot be split, so where one would straddle the boundary the result is padded to reach the width exactly. Breaking for anyone who relied on the returned string having exactly `width` characters
- `date_diff` compares local calendar dates instead of dividing by 86400. Two moments on the same day are 0 days apart whatever the clock says, and a span crossing a daylight saving switch is no longer off by one
- `CustomBindings` reads `show`, `priority` and `system` as genuine YAML booleans. The quoted string `"false"` used to be read as `True`, so a quoted boolean silently meant its opposite; it now falls back to the documented default and says so
- `CustomBindings`: an explicitly declared `key_display` is no longer overridden for function keys. The field exists to override how a key is rendered

### Fixed

- `CustomBindings`: The binding registry was held in class attributes shared by every instance, the same defect as in `ThemeLoader`. A second `CustomBindings` in one process inherited the first one's groups and appended its own on top, so every binding appeared twice
- `next_index`: An empty list raised `ZeroDivisionError` instead of yielding index 0, and the clamped branch ignored the step size while the wrapping branch honoured it
- `str_with_fixed_width`: Did not return the promised number of characters at the edges. Width 1 with `align="right"` returned the entire string, because the offset became `-0`; width 0 returned the text minus its last character
- `linewrap`: Raised `ValueError` on a word longer than the line, and looped forever for a width below 1
- `termcore.util.datetime` resolved to the `datetime` class rather than the module, because the package's star-import re-exported the imported name over the submodule
- `Database.fetch`: An offset without a limit produced a syntax error, `limit=0` was silently dropped, and an empty column list produced `SELECT  FROM`
- `Database`: `ORDER BY` and `WHERE` were joined using identity checks against the first and last element, so passing the same `Condition` or `ColumnOrder` object twice produced malformed SQL
- `Database.insert`: Read the new row back through a hard-coded `id` column, which failed after the write on any table without one, and committed each row separately, so a failure half way through left the earlier rows behind
- `Database.update`: Deleted the conditions out of the caller's own dictionary while parsing them, so a second call with the same data built a statement with an empty `WHERE` clause
- `Database`: `__del__` raised `AttributeError` as an unraisable when the connection had never been assigned
- `ThemeLoader`: The theme registry was held in class attributes shared by every instance, and registration re-prefixed the same `Theme` objects each time. A second application in one process saw `CUSTOM_CUSTOM_<name>`, a third `CUSTOM_CUSTOM_CUSTOM_<name>`. State is now per instance and the prefix is applied once, to a copy
- `ThemeLoader`: A theme folder whose name differed from the `name` in its `theme.py` registered but silently lost its stylesheet
- `ThemeLoader`: From the second loader in a process on, the bundled themes were not found at all, because a consumer's theme folder shadowed them under the shared package name `themes`. The bug was masked by the shared registry described above
- `ThemeLoader`: Switching themes never removed the stylesheet of a theme outside termcore's own theme folder, so a consumer's CSS stayed applied on top of every theme it switched to
- `ThemeLoader`: A theme without a stylesheet, and any theme not registered by termcore such as Textual's built-ins, logged a warning during entirely normal use. This is reported at debug level now
- `ThemeLoader`: Diagnostics went to the root logger and surfaced as `WARNING:root:` in every consumer; they now use a module logger and lazy formatting
- `ThemeLoader`: Two theme folders declaring the same name silently overwrote each other; the second is now refused with an error
- `Singleton`: The metaclass reported `object` as the type of every instance it built, so a consumer type-checking against a singleton got no type at all. It now reports the class it constructed
- `CustomDataTable.flexible_columns` and `AppStateStorage._json_dict` were class attributes with mutable defaults, so every instance in a process shared one object. Same defect as in `ThemeLoader` and `CustomBindings`
- `File.change_extension` printed the split file name to stdout, a debug statement left in a pure function
- A message in `AppStateStorage` was in German, against the rule that all visible text is English
- `ThemeLoader.set_previous_theme_in_textual_app` did nothing at all when the stored theme was no longer registered, so a theme removed between two runs left the application on Textual's default rather than on the `default_theme_name` the caller passed. It now falls back explicitly and reports both that and the case where the default is unknown too
- `ThemeLoader` called `Stylesheet.reparse()` unguarded, so a theme shipping invalid TCSS took the whole application down from inside the library. The failure is logged and the previous stylesheet is kept
- `CustomBindings` was silent in three places that now warn: a binding dropped for a missing `key`, `action` or `description`, a second group claiming an action name and overwriting the first one's footer row, and a tab or screen name matching no group at all

### Removed

- `Database.tostr`: Values are parameters now, so the method had no purpose left; leaving it would have invited hand-built statements
- `Database.update` no longer accepts the list-of-dictionaries form with an `@`-prefixed conditions key
- `CustomBindings._action_belongs_to_group`: Never called
- Commented-out code in `CustomBindings` and `CustomDataTable`
- Two of the six blanket pyright suppressions, after measuring that they report nothing in either checking mode

## [0.1.1] – 2026-04-07

- Initial Release

## [0.1.0] – 2026-03-25

*PyPI name reservation – no functional code.*

[0.2.0]: https://github.com/cgroening/py-termcore/compare/v0.1.1...v0.2.0 [0.1.1]: https://github.com/cgroening/py-termcore/compare/v0.1.0...v0.1.1 [0.1.0]: https://github.com/cgroening/py-termcore/releases/tag/v0.1.0
