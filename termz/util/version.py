"""Reads the installed package version, falling back to pyproject.toml."""

import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import cast


def get_version(
    package_name: str, pyproject_toml_parent_path: Path | None = None
) -> str:
    """
    Returns the version string for the given package.

    Tries `importlib.metadata` first (installed packages), then falls back
    to reading `pyproject.toml` - useful during development when the package
    is not installed.

    Parameters
    ----------
    package_name : str
        The distribution name of the package (as in pyproject.toml).
    pyproject_toml_parent_path : Path, optional
        Path of the folder that contains project's `pyproject.toml`.
        Required when the package is not installed and the fallback is needed.

    Returns
    -------
    str
        The version string (e.g. `0.1.0`).

    Raises
    ------
    FileNotFoundError
        If the metadata is unavailable and no `pyproject.toml` was provided
        or found at the given path.
    KeyError
        If `pyproject.toml` exists but contains no `[project] version`.
    """
    if pyproject_toml_parent_path:
        pyproject_toml = pyproject_toml_parent_path / "pyproject.toml"
    else:
        pyproject_toml = None

    try:
        return pkg_version(package_name)
    except PackageNotFoundError:
        toml_path = pyproject_toml or Path("pyproject.toml")
        with Path(toml_path).open("rb") as f:
            data = tomllib.load(f)
        return cast("str", data["project"]["version"])
