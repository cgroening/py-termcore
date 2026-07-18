"""Guards the size and shape of what `from termz import *` hands out.

Every module re-exports through `import *`, so a module without an `__all__`
re-exports its own imports too. That is not theoretical: `util/datetime.py`
once re-exported the `datetime` class over the submodule of the same name,
and `import termz.util.datetime` handed back the class.
"""

import importlib
import pkgutil

import termz
import termz.util.datetime

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
        assert not public_names(termz) & BORROWED

    def test_the_surface_stays_small(self) -> None:
        # Not a magic number to keep in step: a sharp rise means a module
        # gained an import and lost its `__all__`, which is the defect this
        # file exists for.
        assert len(public_names(termz)) < 100

    def test_the_documented_entry_points_are_reachable(self) -> None:
        for name in (
            "Database", "Condition", "SQLComparisonOperator",
            "ThemeLoader", "CustomBindings", "QuestionScreen",
            "AppStateStorage", "MultiLineFooter",
            "next_index", "clamped_index", "cell_width",
            "str_with_fixed_width", "DateFormat", "print_error",
        ):
            assert hasattr(termz, name), name


class TestEveryModuleDeclaresItsApi:
    def test_no_module_is_missing_an_all(self) -> None:
        # A module without one silently widens the package's public surface.
        missing: list[str] = []
        for info in pkgutil.walk_packages(
            termz.__path__, prefix="termz."
        ):
            if ".themes." in info.name:
                continue
            module = importlib.import_module(info.name)
            if not info.ispkg and not hasattr(module, "__all__"):
                missing.append(info.name)

        assert missing == []

    def test_the_datetime_submodule_is_not_shadowed(self) -> None:
        # The regression this file was written for.
        assert termz.util.datetime.__name__ == "termz.util.datetime"
