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
