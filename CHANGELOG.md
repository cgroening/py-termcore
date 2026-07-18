# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `util/version.py`: New utility module to retrieve the package version via `importlib.metadata` with a fallback to `pyproject.toml`
- First test suite, covering `tui/theme_loader.py`, together with the pytest, coverage and dev-dependency setup the project was missing
- Test suites for `tui/custom_bindings.py`, `io/database.py`, `util/datetime.py`, `util/index.py` and `util/string.py`, which completes the list of modules named in `TODO.md`
- `io/errors.py`: `DatabaseError` and its two subclasses `UnknownIdentifierError` and `EmptyConditionsError`, the project's first domain exceptions
- `SQLComparisonOperator`: `NE`, `LIKE`, `IS_NULL` and `IS_NOT_NULL`. There was previously no way to express "not equal" at all

### Changed

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

### Fixed

- `CustomBindings`: The binding registry was held in class attributes shared by every instance, the same defect as in `ThemeLoader`. A second `CustomBindings` in one process inherited the first one's groups and appended its own on top, so every binding appeared twice
- `next_index`: An empty list raised `ZeroDivisionError` instead of yielding index 0, and the clamped branch ignored the step size while the wrapping branch honoured it
- `str_with_fixed_width`: Did not return the promised number of characters at the edges. Width 1 with `align="right"` returned the entire string, because the offset became `-0`; width 0 returned the text minus its last character
- `linewrap`: Raised `ValueError` on a word longer than the line, and looped forever for a width below 1
- `termz.util.datetime` resolved to the `datetime` class rather than the module, because the package's star-import re-exported the imported name over the submodule
- `Database.fetch`: An offset without a limit produced a syntax error, `limit=0` was silently dropped, and an empty column list produced `SELECT  FROM`
- `Database`: `ORDER BY` and `WHERE` were joined using identity checks against the first and last element, so passing the same `Condition` or `ColumnOrder` object twice produced malformed SQL
- `Database.insert`: Read the new row back through a hard-coded `id` column, which failed after the write on any table without one, and committed each row separately, so a failure half way through left the earlier rows behind
- `Database.update`: Deleted the conditions out of the caller's own dictionary while parsing them, so a second call with the same data built a statement with an empty `WHERE` clause
- `Database`: `__del__` raised `AttributeError` as an unraisable when the connection had never been assigned
- `ThemeLoader`: The theme registry was held in class attributes shared by every instance, and registration re-prefixed the same `Theme` objects each time. A second application in one process saw `CUSTOM_CUSTOM_<name>`, a third `CUSTOM_CUSTOM_CUSTOM_<name>`. State is now per instance and the prefix is applied once, to a copy
- `ThemeLoader`: A theme folder whose name differed from the `name` in its `theme.py` registered but silently lost its stylesheet
- `ThemeLoader`: From the second loader in a process on, the bundled themes were not found at all, because a consumer's theme folder shadowed them under the shared package name `themes`. The bug was masked by the shared registry described above
- `ThemeLoader`: Switching themes never removed the stylesheet of a theme outside termz's own theme folder, so a consumer's CSS stayed applied on top of every theme it switched to
- `ThemeLoader`: A theme without a stylesheet, and any theme not registered by termz such as Textual's built-ins, logged a warning during entirely normal use. This is reported at debug level now
- `ThemeLoader`: Diagnostics went to the root logger and surfaced as `WARNING:root:` in every consumer; they now use a module logger and lazy formatting
- `ThemeLoader`: Two theme folders declaring the same name silently overwrote each other; the second is now refused with an error

### Removed

- `Database.tostr`: Values are parameters now, so the method had no purpose left; leaving it would have invited hand-built statements
- `Database.update` no longer accepts the list-of-dictionaries form with an `@`-prefixed conditions key
- `CustomBindings._action_belongs_to_group`: Never called

## [0.1.1] – 2026-04-07

- Initial Release

## [0.1.0] – 2026-03-25

*PyPI name reservation – no functional code.*

[Unreleased]: https://github.com/cgroening/py-termz/compare/v0.1.1...HEAD [0.1.1]: https://github.com/cgroening/py-termz/compare/v0.1.0...v0.1.1 [0.1.0]: https://github.com/cgroening/py-termz/releases/tag/v0.1.0
