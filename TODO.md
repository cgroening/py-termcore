# TODO

Deferred work for termcore, collected from two sources: the bugs that surfaced while hardening `termplate` against the style guide, and a feature comparison with `ratada`, the Rust toolkit that plays the same role for `clibase`.

termcore is the foundation under termplate. That ordering matters for how this list is sorted: a defect here reaches every application built on the toolkit, and it reaches them silently, because the applications trust the library rather than testing it.

## Tests

Every module named below is covered now, and the suite has grown from nothing to a little over 70 % of the package. What is left untested is the rest: `cli/output.py`, the custom widgets, `io/app_state_storage.py`, `io/file.py`, `io/textfile.py` and the remaining `util` modules. The coverage gate in `pyproject.toml` holds the level reached so far – raise `fail_under` with every module that gains tests.

Writing these suites produced the same result every time: each module had to be fixed before it could be meaningfully tested. That pattern is the argument for the remaining entries, not against them.

The practical consequence was already documented before the first test existed: of the four theme bugs that held up termplate, three lived in `termcore/tui/theme_loader.py`, and each of them would have been caught by one test. Writing that suite immediately surfaced a fifth and a sixth defect that nobody had noticed.

Ordered by how much a test would buy:

- [x] `termcore/tui/theme_loader.py` – the module with the most silent behaviour and all four known bugs: theme discovery, name prefixing, CSS resolution, persistence and cycling. Nothing here fails loudly when it goes wrong; it just renders the wrong colours.
- [x] `termcore/tui/custom_bindings.py` – the group and prefix contract (`_global`, `<name>_tab`, `<name>_screen`) that every derived app depends on and that no consumer can verify from the outside.
- [x] `termcore/io/database.py` – it assembles SQL strings. That is pure, side-effect-light logic and therefore the cheapest meaningful coverage in the repository.
- [x] `termcore/util/datetime.py`, `termcore/util/index.py`, `termcore/util/string.py` – pure functions with obvious edge cases (empty input, boundaries, wrapping).

## Tooling

- [x] There is no `[tool.ruff]` section in `pyproject.toml`, so ruff runs on its defaults: no line length, no rule selection. Adopt the baseline from section 3.2.1 of the style guide, the one termplate already runs green. Done: the rule set reported 531 violations on adoption and `ruff check .` is green now. The formatter is deliberately left unconfigured - it would have rewritten 41 of 55 files for no behavioural gain, and `E501` enforces the column limit.
- [x] `[tool.pyright]` sets six blanket suppressions and no `typeCheckingMode` at all, so the library is not even checked in strict mode. The guide requires strict. Set it, then review each suppression individually and leave a comment on every one that stays. Done, with a correction to the premise: basedpyright's own default is `recommended`, which is stricter than `strict`, so the library was already being checked more strictly than the guide asks. Setting `strict` states the contract and is what a consumer running plain pyright needs. Two suppressions were deleted after measuring that they report nothing in either mode; the four that stayed carry a comment each.
- [x] `py.typed` is missing. Without that marker a consumer's type checker treats the whole package as untyped and silently degrades every import to `Any` – including termplate, which otherwise runs strict basedpyright. Add the file and ship it via `package-data`. Done; no `package-data` entry was needed, since hatchling ships everything inside the package directory. Verified in the built wheel. The marker immediately earned itself: with termcore typed, termplate's checker found that `Singleton` reported `object` for every instance it built.

## Bugs found while hardening termplate

All four were diagnosed from termplate but had to be fixed here. All four are done; the two below them were found while fixing them and are done as well.

- [x] `ThemeLoader._theme_names` and `_theme_data` are class attributes with mutable defaults that `__init__` never resets, and `register_themes_in_textual_app` re-prefixes the same `Theme` objects on every call. A second app instance in one process therefore sees `CUSTOM_CUSTOM_classic-black`, a third `CUSTOM_CUSTOM_CUSTOM_...`. Production gets away with it because there is one app per process; a test suite that builds an app per test does not. termplate carries a `reset_theme_loader` fixture purely to work around this, and it can be deleted once the state is per instance. Fixed: state is per instance, and the prefix is applied once at load time to a copy of the theme, so registration mutates nothing. The fixture in termplate is gone.
- [x] The coupling "a theme directory's name must equal the `name` in its `theme.py`" is undocumented and unenforced, because themes are stored under the directory name but their CSS is resolved by the theme name. Breaking it registers the theme and silently drops its stylesheet – the failure termplate shipped with. Either key both lookups the same way or refuse a mismatch loudly. Fixed: both are keyed by the registered name, so the coupling no longer exists rather than being enforced. A duplicate name within one prefix is refused with an error.
- [x] `ThemeLoader` logs through the root logger (`logging.warning(...)`) instead of `logging.getLogger(__name__)`, so its diagnostics cannot be filtered per module and surface as `WARNING:root:` in every consumer. Fixed, and the same lines moved to lazy `%`-formatting with `%r`.
- [x] Cycling themes also walks Textual's built-in themes, which have no termcore stylesheet, so each one logs "No CSS files found for theme: textual-dark". The theme renders correctly, so this is noise rather than breakage – but a warning that fires during normal use trains people to ignore warnings. Either restrict cycling to registered themes or lower the level for the built-ins. Fixed by lowering the level: the built-ins were only half the noise, since ten of the sixteen bundled themes ship no stylesheet either and warned just as loudly. Cycling deliberately still reaches the built-ins.
- [x] From the second `ThemeLoader` in a process on, the bundled themes were not found at all. `_load_themes` only inserted a theme folder's parent into `sys.path` if it was absent, so on the second load termcore's own folder sat behind the consumer's, and the package `themes` resolved to the wrong one – every bundled folder reported "no theme.py". The shared class-level registry hid this completely, because the second loader still saw the first one's themes. Fixed by importing each `theme.py` by file path via `importlib.util`, which removes the `sys.path` and `sys.modules` handling entirely.
- [x] `_remove_all_theme_css` compared against termcore's own theme directory, so the stylesheet of a consumer's theme was never removed on a switch and stayed applied on top of every theme afterwards. Fixed by removing exactly the files the loader read. The re-parse now also runs when the new theme has no stylesheet, which previously left the removal unapplied.

## Further findings in ThemeLoader

Noticed while fixing the above, deliberately left alone to keep that change focused.

- [x] `set_previous_theme_in_textual_app` silently does nothing when the stored theme is not registered – a theme removed between two runs leaves the app on Textual's default rather than on the `default_theme_name` the caller passed, and says so in neither the log nor the return value. It should fall back to the default explicitly and report it.
- [x] `include_standard_themes: bool` and `_load_themes(standard_themes: bool)` are flag arguments, which section 1.1.2 of the style guide forbids. Changing the first is a breaking API change and belongs with a release. Done earlier than planned: the tooling round removed both while adopting the FBT rules - `ThemeLoader.custom_only` replaced the constructor flag and `_load_themes` became `_load_standard_themes` and `_load_custom_themes`.
- [x] `_apply_stylesheet` calls `app.stylesheet.reparse()` unguarded, so a theme shipping invalid TCSS takes the whole application down. Decide whether that should be reported and skipped instead – failing loudly may well be right, but it should be a decision rather than an accident.

## Further findings in CustomBindings

Noticed while writing its tests, deliberately left alone to keep that change focused.

- [x] A binding missing `key`, `action` or `description` is dropped silently. Nothing is logged, so a typo in `bindings.yaml` costs a shortcut and says nothing.
- [x] Two groups declaring the same action name both land in `action_to_groups`, but `action_row_map` keeps only the last one – the earlier binding silently moves to the other footer row.
- [x] `get_bindings` with a `tab_name` or `screen_name` that matches no group returns just the globals instead of complaining, so a typo looks like a tab with no shortcuts.
- [x] `show`, `priority` and `system` are read with `bool(...)`, so the YAML string `"false"` is `True`. Only an unquoted `false` behaves as written.
- [x] `_parse_key_display` overrides an explicitly declared `key_display` for function keys, and returns `None` rather than the key when neither applies, contrary to what its docstring said.

## Further findings in the util modules

- [x] `date_diff` divides by 86400, so a difference of one second in the wrong direction reports -1 days, and any span crossing a daylight saving switch is off by one. Deciding between "whole 24-hour periods" and "calendar days apart" is a semantic choice, not a bug fix.
- [x] `str_with_fixed_width` counts code points, not terminal cells. CJK text and emoji therefore render wider than the requested width, which defeats the purpose of the function. Fixing it properly needs an East-Asian-width table, and section 1.2.7 requires asking before adding a dependency. Corrected: Python ships that table, so no dependency was needed. `cell_width` in `util/string.py` counts cells with `unicodedata`, and `str_with_fixed_width` is built on it.
- [x] Only `util/datetime.py` declares `__all__`, and only because its star-export shadowed the submodule itself. Every other module leaks its imports into the package namespace – `termcore.io.database` exports `sqlite3`, `Enum` and `TracebackType`, for instance. Section 1.2.6 asks for a small public interface; this is the opposite.

## Release

- [ ] Publish 0.1.2, the first release under the name `termcore`. It is prepared but not uploaded. Everything termplate needs exists only in this working copy: `util/version.py`, the named replacements for the three flag arguments, and the `TERMCORE_` theme prefix. Until the upload happens, termplate's `termcore>=0.1.2` constraint resolves to nothing and the app cannot be installed by anyone else. The old `termz` releases stay on PyPI untouched – not yanked, just no longer maintained.

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

ratada implements the following because ratatui draws every cell itself. Textual provides them, so reimplementing them in termcore would be duplicated work that ages badly. This list exists to stop that happening.

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

ratada has each of these; termcore has none of them.

- [x] `CLAUDE.md` with the project-specific conventions.
- [x] `docs/` holding `DEVELOPMENT.md` and a `CLEAN-UP.md` walkthrough checklist. Done, modelled on ratada's rather than termplate's: termplate's DEVELOPMENT.md is a signpost because `_TEMPLATE_GUIDE.md` carries everything, and termcore has no such document. `tests/test_docs.py` came with them, which is what turned up the six horizontal rules in the README that section 1.5.1 forbids.
