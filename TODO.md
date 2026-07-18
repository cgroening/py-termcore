# TODO

Deferred work for termz, collected from two sources: the bugs that surfaced while hardening `termplate` against the style guide, and a feature comparison with `ratada`, the Rust toolkit that plays the same role for `clibase`.

termz is the foundation under termplate. That ordering matters for how this list is sorted: a defect here reaches every application built on the toolkit, and it reaches them silently, because the applications trust the library rather than testing it.

## Tests

termz has 3562 lines of Python and not a single test. There is no test dependency, no pytest configuration and no `tests/` directory. For comparison, ratada carries 389 test functions.

The practical consequence is already documented: of the four theme bugs that held up termplate, three live in `termz/tui/theme_loader.py`, and each of them would have been caught by one test. Today the only thing exercising termz is termplate's suite, incidentally, through the parts termplate happens to use.

Ordered by how much a test would buy:

- [ ] `termz/tui/theme_loader.py` – the module with the most silent behaviour and all four known bugs: theme discovery, name prefixing, CSS resolution, persistence and cycling. Nothing here fails loudly when it goes wrong; it just renders the wrong colours.
- [ ] `termz/tui/custom_bindings.py` – the group and prefix contract (`_global`, `<name>_tab`, `<name>_screen`) that every derived app depends on and that no consumer can verify from the outside.
- [ ] `termz/io/database.py` – it assembles SQL strings. That is pure, side-effect-light logic and therefore the cheapest meaningful coverage in the repository.
- [ ] `termz/util/datetime.py`, `termz/util/index.py`, `termz/util/string.py` – pure functions with obvious edge cases (empty input, boundaries, wrapping).

## Tooling

- [ ] There is no `[tool.ruff]` section in `pyproject.toml`, so ruff runs on its defaults: no line length, no rule selection. Adopt the baseline from section 3.2.1 of the style guide, the one termplate already runs green.
- [ ] `[tool.pyright]` sets six blanket suppressions and no `typeCheckingMode` at all, so the library is not even checked in strict mode. The guide requires strict. Set it, then review each suppression individually and leave a comment on every one that stays.
- [ ] `py.typed` is missing. Without that marker a consumer's type checker treats the whole package as untyped and silently degrades every import to `Any` – including termplate, which otherwise runs strict basedpyright. Add the file and ship it via `package-data`.

## Bugs found while hardening termplate

All four were diagnosed from termplate but have to be fixed here.

- [ ] `ThemeLoader._theme_names` and `_theme_data` are class attributes with mutable defaults that `__init__` never resets, and `register_themes_in_textual_app` re-prefixes the same `Theme` objects on every call. A second app instance in one process therefore sees `CUSTOM_CUSTOM_classic-black`, a third `CUSTOM_CUSTOM_CUSTOM_...`. Production gets away with it because there is one app per process; a test suite that builds an app per test does not. termplate carries a `reset_theme_loader` fixture purely to work around this, and it can be deleted once the state is per instance.
- [ ] The coupling "a theme directory's name must equal the `name` in its `theme.py`" is undocumented and unenforced, because themes are stored under the directory name but their CSS is resolved by the theme name. Breaking it registers the theme and silently drops its stylesheet – the failure termplate shipped with. Either key both lookups the same way or refuse a mismatch loudly.
- [ ] `ThemeLoader` logs through the root logger (`logging.warning(...)`) instead of `logging.getLogger(__name__)`, so its diagnostics cannot be filtered per module and surface as `WARNING:root:` in every consumer.
- [ ] Cycling themes also walks Textual's built-in themes, which have no termz stylesheet, so each one logs "No CSS files found for theme: textual-dark". The theme renders correctly, so this is noise rather than breakage – but a warning that fires during normal use trains people to ignore warnings. Either restrict cycling to registered themes or lower the level for the built-ins.

## Release

- [ ] Publish a version that contains `termz/util/version.py`. It is missing from the published 0.1.1 and exists only in the local development copy, which makes termplate's `termz>=0.1.1` constraint untrue: a fresh install fails at import time with `ModuleNotFoundError`. Until that release exists, termplate cannot be installed by anyone else.

## Missing widgets

Genuine gaps against ratada, ordered by usefulness. Everything here is something Textual does not provide, so it is work that belongs in the toolkit rather than in each application.

- [ ] Help overlay with fuzzy search over the bindings, grouped by section. Section 1.6 of the style guide requires one in every TUI, and termplate is waiting on it.
- [ ] The modal set beyond the existing `QuestionScreen`, which only covers confirmation: text input, single select, multi select, number input and a plain message modal. The underlying widgets exist in Textual; what is missing is the ready-made prompt that returns a value.
- [ ] Calendar date picker, plus the date-range and month variants. Also required by section 1.6.
- [ ] Fuzzy finder over arbitrary lists. Textual ships `textual.fuzzy.Matcher`, but it is wired into the command palette rather than reusable as a generic picker.
- [ ] Schema-driven form modal: several fields of mixed type in one dialog, returning a filled structure. `CustomBindings` already shows that the declarative-schema approach fits this codebase.
- [ ] Autocomplete dropdown for text fields.
- [ ] Colour picker and swatch picker, and a numeric slider or stepper.
- [ ] `$EDITOR` handoff helper. `App.suspend()` is the primitive; the temp-file, spawn and read-back dance around it is not.
- [ ] Double-press-to-confirm detector, and a quit-confirmation policy for apps with unsaved state.
- [ ] Duplicate and conflict detection in `CustomBindings`, so that two actions claiming the same key is an error rather than a silent shadow.
- [ ] Filtering and multi-select on `CustomDataTable`. Sorting is native to Textual's `DataTable`; these two are not.
- [ ] Incremental search inside a scrolled view.

## Deliberately not rebuilt

ratada implements the following because ratatui draws every cell itself. Textual provides them, so reimplementing them in termz would be duplicated work that ages badly. This list exists to stop that happening.

- Command palette: `App.COMMANDS` with a `Provider`.
- Collapsible tree: `Tree` and `Collapsible`.
- Markdown rendering and viewer: `Markdown` and `MarkdownViewer`.
- Toasts and notifications: `App.notify`.
- Multi-line editor: `TextArea`.
- Tab bar: `Tabs`, `TabbedContent`, `TabPane`.
- Spinner and progress: `LoadingIndicator` and `ProgressBar`.
- Header: `Header`.
- Filesystem browser: `DirectoryTree`. Only a modal wrapper that returns the chosen path would be new.
- Clipboard: `App.copy_to_clipboard`, plus the bindings already built into `Input` and `TextArea`.
- Scrollbars on overflow, text truncation, wrapping and layout arithmetic: all CSS.

A third group does not arise at all in a Textual application: the terminal guard, the event-loop driver and the shared text-editing core exist in ratada only because it owns the render loop. Textual's `App` owns all three.

## Repo hygiene

ratada has each of these; termz has none of them.

- [ ] `CLAUDE.md` with the project-specific conventions.
- [ ] `docs/` holding `DEVELOPMENT.md` and a `CLEAN-UP.md` walkthrough checklist.
- [ ] `CONTRIBUTING.md` naming the merge gates.
- [ ] `examples/` with a runnable demonstration per major widget. The README carries snippets, but nothing that can be executed.
