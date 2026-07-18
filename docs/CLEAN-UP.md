# Code Walkthrough and Cleanup (checklist to tick off)

## Context

A structured pass through the whole library: read every module once against the style guide, and fix what the reading turns up. Not a rewrite and not a feature pass.

The rules themselves live in the style guide; this is the reminder list, not a copy of it. Deferred work is tracked in [`TODO.md`](../TODO.md) and is not duplicated here – a finding that is real but out of scope for the pass goes there instead of being fixed in passing.

Nothing below is ticked. It is the scaffold for the next walkthrough, not a record of previous ones.

How to run it:

- One phase at a time, each ending green on `ruff check .`, `basedpyright` and `pytest`.
- Read the module before changing it. Half the defects found in this repository so far were invisible in a diff and obvious in a full read.
- A finding that needs a decision rather than a fix goes to [`TODO.md`](../TODO.md) with the decision spelled out, not a `# TODO` in the code.

## Generic checkpoints (apply to every module)

- [ ] Module docstring present, one-line summary first, and an `__all__` naming the real public surface.
- [ ] Every public function and class documented NumPy-style; private ones get a line.
- [ ] Class attributes: annotated at class level, assigned in `__init__`. A mutable default on the class is shared by every instance – the single most frequent defect in this repository.
- [ ] Diagnostics through `logging.getLogger(__name__)` with lazy `%`-formatting. No `print` outside `cli/output.py`.
- [ ] No boolean parameter selects behaviour. Two named functions, a factory or an enum.
- [ ] Errors are raised, not printed and not swallowed. Domain exceptions, never a bare `Exception`.
- [ ] Paths go through `pathlib`, timestamps carry a time zone, widths count terminal cells.
- [ ] No dead code, no commented-out code, no stale comment naming a renamed thing.
- [ ] Tests exist for the behaviour, not for the source text. Coverage rose, and `fail_under` rose with it.

## Phase 0, baseline and scope

- [ ] Record the starting point: `pytest` line count and coverage, `ruff check .` and `basedpyright` both clean.
- [ ] Read [`CLAUDE.md`](../CLAUDE.md) and the module tree in [`DEVELOPMENT.md`](DEVELOPMENT.md), so the pass knows what is already decided.
- [ ] Skim [`TODO.md`](../TODO.md) so a known finding is not rediscovered as a surprise.

## Phase 1, the console output module

`cli/output.py`, the module that owns every visible byte termz produces, and it has no tests at all.

- [ ] Read it. Nine public functions, all of them wrappers around Rich.
- [ ] `console` is a module-level public name; decide whether it belongs in `__all__` or whether `get_console` is the whole contract.
- [ ] Tests through Rich's own capture, asserting on what is printed rather than that it did not raise.
- [ ] Check the glyph set against section 1.6: no coloured emoji, and an ASCII fallback where a symbol carries meaning.

## Phase 2, the file modules

`io/file.py` and `io/textfile.py`, never read in any previous pass; both were only touched at lint level.

- [ ] `File.folder_content` and `folder_content_recursive`: paths are still assembled by string concatenation (`path + "/" + item`) although `pathlib` is imported. Decide whether these take and return `Path`.
- [ ] `FolderItem` carries `level` for recursion; check that the non-recursive entry point cannot produce a confusing value.
- [ ] `File.copy_folder` still carries a `TODO` about sub-folders. Either implement it or move the note to `TODO.md`.
- [ ] `Textfile` takes `path` per call while `File` is all static methods. Decide whether both shapes should exist.
- [ ] Tests for both, against `tmp_path`.

## Phase 3, the application state store

- [ ] Read `io/app_state_storage.py` whole. It was changed under the tooling pass without being read.
- [ ] The list helpers (`list_insert`, `edit_list_item`, `delete_list_item`, `move_list_item`) cast their way into nested structures; check what each does with a wrong type or an index out of range.
- [ ] It is a `Singleton`, so a second construction with different arguments returns the first instance and silently ignores them. Decide whether that should be reported.
- [ ] Tests, including the failure paths that now raise `StateFileError`.

## Phase 4, the modal screen and the widgets

`tui/question_screen.py` plus the four under `tui/custom_widgets/`: five modules, no tests, and the widgets are what a consumer sees first.

- [ ] `question_screen.py`: `ButtonColor` and the dismissal contract.
- [ ] `multiline_footer.py`: the largest of the four. Check `row_map` handling against a key that no binding declares, and the wrapping behaviour at a narrow width.
- [ ] `custom_data_table.py`: `flexible_columns` is now per instance; check the resize arithmetic against a table narrower than its fixed columns.
- [ ] `custom_checkbox.py` and `custom_selection.py`: both override rendering only; confirm nothing else is needed.
- [ ] Tests for all five through `App.run_test()`.

## Phase 5, the remaining util modules

- [ ] `debug.py`: the decorators log every call at debug level. Check the overhead when the logger is disabled, and that they preserve signatures.
- [ ] `logger.py`: `setup_logging` writes below the user's local state directory. Section 1.2.7 requires the XDG variables to be honoured rather than the default hard-coded.
- [ ] `singleton.py`: the instance registry is module-level. Check what happens on a subclass.
- [ ] `validation.py`: one function; decide whether the module earns its place or belongs with `string.py`.
- [ ] `version.py`: the `pyproject.toml` fallback only works from the source tree. Check what it does when neither source is available.
- [ ] Tests for each.

## Phase 6, the covered modules

Lighter, because these were read and tested recently. Look for what the tests do not cover rather than for the obvious.

- [ ] `tui/theme_loader.py`, `tui/custom_bindings.py`, `io/database.py`.
- [ ] `util/string.py`, `util/datetime.py`, `util/index.py`.
- [ ] For each: read the uncovered lines the coverage report names and decide whether they are unreachable, untested or dead.

## Phase 7, configuration and packaging

- [ ] `pyproject.toml`: the four remaining pyright suppressions still describe something real.
- [ ] The dependency floors in `[project]` and `[project.optional-dependencies]` match what the code actually needs.
- [ ] Build the wheel and read its file list. A sub-package without an `__init__.py` disappears without a word.
- [ ] `pip-audit` inside the project venv.

## Phase 8, cross-cutting and wrap-up

- [ ] Read [`README.md`](../README.md) end to end against the code. Every signature it shows is one a reader will copy.
- [ ] [`CLAUDE.md`](../CLAUDE.md) and [`DEVELOPMENT.md`](DEVELOPMENT.md) still describe the tree that exists.
- [ ] `CHANGELOG.md` has an entry for everything the pass changed in the published package.
- [ ] Raise `fail_under` to the level the pass reached.
- [ ] Move every finding that was not fixed into [`TODO.md`](../TODO.md), with the reason it was left.

## Verification

```zsh
ruff check .
basedpyright
pytest
python -m build && unzip -l dist/*.whl
```

Then the consumer, because a toolkit is only exercised by something that uses it: termplate's suite green against this working copy, and its TUI started once by hand.

## Notes and non-goals

- Not a rewrite. A module that is correct, tested and readable is finished, however much it differs from how it would be written today.
- Not a feature pass. The gaps in [`TODO.md`](../TODO.md) under "Missing widgets" stay there.
- Not a formatting pass. `ruff format` is deliberately unconfigured in this repository; see the comment in `pyproject.toml`.
