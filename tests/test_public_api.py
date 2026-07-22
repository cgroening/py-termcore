"""Guards the size and shape of what `from termcore import *` hands out.

Every module re-exports through `import *`, so a module without an `__all__`
re-exports its own imports too. That is not theoretical: `util/datetime.py`
once re-exported the `datetime` class over the submodule of the same name,
and `import termcore.util.datetime` handed back the class.
"""

import importlib
import pkgutil

import termcore
import termcore.util.datetime

# Names a module imported for its own use and must not pass on.
BORROWED = {
    "Any", "Enum", "Iterable", "Mapping", "Path", "Sequence", "TracebackType",
    "cast", "dataclass", "importlib", "json", "logging", "os", "re", "shutil",
    "sqlite3", "sys", "time", "tomllib", "unicodedata", "yaml",
}


def public_names(module: object) -> set[str]:
    """Returns the names `import *` would take from the given module."""
    return {name for name in dir(module) if not name.startswith("_")}


class TestTheStarExportCarriesOnlyTheApi:
    def test_no_borrowed_name_is_re_exported(self) -> None:
        assert not public_names(termcore) & BORROWED

    def test_the_surface_stays_small(self) -> None:
        # Not a magic number to keep in step: a sharp rise means a module
        # gained an import and lost its `__all__`, which is the defect this
        # file exists for. Raised from 100 when the header and status bar
        # were added deliberately - at 99 of 100 the next widget would have
        # tripped this for the wrong reason.
        assert len(public_names(termcore)) < 120

    def test_the_documented_entry_points_are_reachable(self) -> None:
        for name in (
            "Database", "Condition", "SQLComparisonOperator",
            "ThemeLoader", "CustomBindings", "QuestionScreen",
            "AppStateStorage", "MultiLineFooter",
            "BindingGroup", "HelpScreen", "active_actions",
            "AppHeader", "StatusBar", "HeaderTab",
            "next_index", "clamped_index", "cell_width",
            "str_with_fixed_width", "DateFormat", "print_error",
        ):
            assert hasattr(termcore, name), name

    def test_the_layout_helpers_stay_out_of_the_namespace(self) -> None:
        # They are the arithmetic behind two widgets, not an API an
        # application consumes; exporting them would widen the surface for
        # nobody's benefit.
        for name in ("FooterLayout", "build_rows", "hint_width", "pack"):
            assert not hasattr(termcore, name), name


class TestEveryModuleDeclaresItsApi:
    def test_no_module_is_missing_an_all(self) -> None:
        # A module without one silently widens the package's public surface.
        missing: list[str] = []
        for info in pkgutil.walk_packages(
            termcore.__path__, prefix="termcore."
        ):
            if ".themes." in info.name:
                continue
            module = importlib.import_module(info.name)
            if not info.ispkg and not hasattr(module, "__all__"):
                missing.append(info.name)

        assert missing == []

    def test_the_datetime_submodule_is_not_shadowed(self) -> None:
        # The regression this file was written for.
        assert termcore.util.datetime.__name__ == "termcore.util.datetime"
