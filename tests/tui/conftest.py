from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest

# A theme.py is a module holding a TEXTUAL_THEME constant - that is the whole
# contract, so the fixture writes the smallest module that satisfies it.
_THEME_MODULE = dedent(
    """
    from textual.theme import Theme

    TEXTUAL_THEME = Theme(name="{name}", primary="#7ca6c2")
    """
).lstrip()

MakeTheme = Callable[..., Path]
WriteBindings = Callable[[str], str]
WriteScopes = Callable[[str], str]


@pytest.fixture
def write_bindings(tmp_path: Path) -> WriteBindings:
    """
    Returns a factory that writes a bindings YAML file and returns its path.

    The factory takes the YAML as text rather than as a dict, because how the
    file is written is exactly what several of these tests are about.
    """
    def _write_bindings(yaml_text: str) -> str:
        path = tmp_path / "bindings.yaml"
        path.write_text(dedent(yaml_text).lstrip(), encoding="utf-8")
        return str(path)

    return _write_bindings


@pytest.fixture
def write_scopes(tmp_path: Path) -> WriteScopes:
    """
    Returns a factory that writes a scope-titles file and returns its path.

    Separate from `write_bindings` because the two are separate files, and
    several tests are about what happens when they disagree.
    """
    def _write_scopes(yaml_text: str) -> str:
        path = tmp_path / "scopes.yaml"
        path.write_text(dedent(yaml_text).lstrip(), encoding="utf-8")
        return str(path)

    return _write_scopes


@pytest.fixture
def theme_root(tmp_path: Path) -> Path:
    """An empty custom theme folder, to be filled by `make_theme`."""
    root = tmp_path / "themes"
    root.mkdir()
    return root


@pytest.fixture
def make_theme() -> MakeTheme:
    """
    Returns a factory that writes a single theme folder.

    Folder name and declared theme name are separate arguments on purpose:
    telling the two apart is what several of these tests are about.
    """
    def _make_theme(
        root: Path, folder_name: str,
        theme_name: str | None = None, css: str | None = None
    ) -> Path:
        theme_folder = root / folder_name
        theme_folder.mkdir(parents=True)
        (theme_folder / "theme.py").write_text(
            _THEME_MODULE.format(name=theme_name or folder_name),
            encoding="utf-8"
        )
        if css is not None:
            (theme_folder / "style.css").write_text(css, encoding="utf-8")
        return theme_folder

    return _make_theme
