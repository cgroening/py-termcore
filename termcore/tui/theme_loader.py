"""Discovery, registration and stylesheet handling of Textual themes."""

import importlib.util
import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from types import ModuleType
from typing import cast

from textual.app import App
from textual.theme import Theme

__all__ = [
    "DEFAULT_CUSTOM_THEME_PREFIX",
    "DEFAULT_TERMCORE_THEME_PREFIX",
    "SCRIPT_DIR",
    "STANDARD_THEMES_DIR",
    "ThemeData",
    "ThemeLoader",
]

DEFAULT_TERMCORE_THEME_PREFIX = "TERMCORE_"
DEFAULT_CUSTOM_THEME_PREFIX = "CUSTOM_"
SCRIPT_DIR = Path(__file__).parent.parent
STANDARD_THEMES_DIR = SCRIPT_DIR / "tui/themes"

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ThemeData:
    """Data class to hold information of a single theme."""

    prefix: str
    textual_theme: Theme
    css_files: list[str] | None = None


class ThemeLoader:
    """
    Loads and manages themes for Textual applications.

    The themes are expected to be in subfolders of the theme folder, each
    containing a `theme.py` file defining a `TEXTUAL_THEME` variable.
    Additionally, any number of `.css` or `.tcss` files can be included in the
    theme folder.

    A theme is identified by the `name` of its `TEXTUAL_THEME` plus the prefix
    it is registered under; the name of its folder carries no meaning and is
    free to differ.

    This class dynamically imports the theme modules, registers them and makes
    them available for use in the application.
    """

    _theme_folder: str | None
    _termcore_theme_prefix: str
    _custom_theme_prefix: str
    _theme_names: list[str]
    _theme_data: dict[str, ThemeData]


    def __init__(
        self, theme_folder: str | None = None,
        termcore_theme_prefix: str = DEFAULT_TERMCORE_THEME_PREFIX,
        custom_theme_prefix: str = DEFAULT_CUSTOM_THEME_PREFIX
    ) -> None:
        """
        Loads the themes that ship with termcore, plus the given folder.

        Use `ThemeLoader.custom_only` for a loader that leaves the bundled
        themes out.
        """
        self._configure(
            theme_folder, termcore_theme_prefix, custom_theme_prefix
        )
        self._load_standard_themes()
        self._load_custom_themes()
        self._theme_names.sort()

    @classmethod
    def custom_only(
        cls, theme_folder: str,
        termcore_theme_prefix: str = DEFAULT_TERMCORE_THEME_PREFIX,
        custom_theme_prefix: str = DEFAULT_CUSTOM_THEME_PREFIX
    ) -> "ThemeLoader":
        """
        Returns a loader for the given folder alone, without termcore's themes.

        Parameters
        ----------
        theme_folder : str
            Path to the folder holding the theme directories.
        termcore_theme_prefix : str, optional
            Kept so that a later comparison against a bundled theme name
            still resolves, even though none are loaded.
        custom_theme_prefix : str, optional
            Prefix the themes of this folder are registered under.

        Returns
        -------
        ThemeLoader
            A loader holding only the themes of `theme_folder`.
        """
        # A factory of this very class, which is what SLF001 cannot tell
        # apart from reaching into a foreign object.
        loader = cls.__new__(cls)
        loader._configure(  # noqa: SLF001
            theme_folder, termcore_theme_prefix, custom_theme_prefix
        )
        loader._load_custom_themes()  # noqa: SLF001
        loader._theme_names.sort()  # noqa: SLF001

        return loader

    def _configure(
        self, theme_folder: str | None,
        termcore_theme_prefix: str,
        custom_theme_prefix: str
    ) -> None:
        """Stores the settings and starts from an empty registry."""
        self._theme_folder = theme_folder
        self._termcore_theme_prefix = termcore_theme_prefix
        self._custom_theme_prefix = custom_theme_prefix
        self._theme_names = []
        self._theme_data = {}

    def _load_standard_themes(self) -> None:
        """Loads and registers the themes that ship with termcore."""
        self._load_folder(
            self._termcore_theme_prefix, STANDARD_THEMES_DIR.resolve()
        )

    def _load_custom_themes(self) -> None:
        """Loads and registers the themes of the configured folder, if any."""
        if not self._theme_folder:
            return

        self._load_folder(
            self._custom_theme_prefix, Path(self._theme_folder).resolve()
        )

    def _load_folder(self, prefix: str, theme_folder_path: Path) -> None:
        """Loads every theme directory below the given folder."""
        if not theme_folder_path.is_dir():
            _logger.warning(
                "Theme folder %r not found. Skipping.", str(theme_folder_path)
            )
            return

        count_before = len(self._theme_names)
        self._process_themes(prefix, theme_folder_path)
        _logger.info(
            "Found %d themes in %r",
            len(self._theme_names) - count_before, str(theme_folder_path)
        )

    def _process_themes(self, prefix: str, theme_folder_path: Path) -> None:
        """Imports and registers themes from the given folder path."""
        # Sorted, so that a refused duplicate is always the same one
        for full_path in sorted(theme_folder_path.iterdir()):
            if full_path.name.startswith((".", "_")) \
            or not full_path.is_dir():
                continue

            self._import_and_register_theme(prefix, full_path)

    def _import_and_register_theme(
        self, prefix: str, theme_folder_path: Path
    ) -> None:
        """
        Imports a theme module and registers its theme.

        Raises
        ------
        Exception
            If any error occurs while executing the theme module.
        """
        folder_name = theme_folder_path.name
        theme_file = theme_folder_path / "theme.py"
        if not theme_file.is_file():
            _logger.warning(
                "Skipping theme folder %r (no theme.py)", folder_name
            )
            return

        try:
            theme_module = self._import_theme_module(theme_file)
            textual_theme = getattr(theme_module, "TEXTUAL_THEME", None)

            # Abort if no TEXTUAL_THEME variable is defined
            if not isinstance(textual_theme, Theme):
                _logger.warning(
                    "Skipping theme folder %r (no TEXTUAL_THEME defined)",
                    folder_name
                )
                return

            # Register the theme
            css_files = self._get_css_files_for_theme(theme_folder_path)
            self._save_theme_data(prefix, textual_theme, css_files)
        except Exception:
            _logger.exception("Error loading theme folder %r", folder_name)

    def _import_theme_module(self, theme_file: Path) -> ModuleType:
        """
        Imports a theme.py by path, leaving sys.path and sys.modules alone.

        Loading by path is what keeps theme folders independent of each
        other. Importing them as a package named after the folder made the
        first folder loaded in a process shadow every later one of the same
        name, so a second application lost the themes of the toolkit.
        """
        spec = importlib.util.spec_from_file_location(
            f"_termcore_theme_{theme_file.parent.name}", theme_file
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load a theme module from {theme_file}")

        theme_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme_module)
        return theme_module

    def _get_css_files_for_theme(self, theme_folder_path: Path) -> list[str]:
        """Generates a list of CSS files in the given folder."""
        return [
            str(path) for path in sorted(theme_folder_path.iterdir())
            if path.suffix in (".css", ".tcss")
        ]

    def _save_theme_data(
        self, prefix: str,
        theme_instance: Theme,
        css_files: list[str] | None = None
    ) -> None:
        """
        Stores the theme data and records its registered name.

        The prefix is applied to a copy of the theme, so that the
        `TEXTUAL_THEME` constant of the imported module keeps the name it was
        written with and repeated registration cannot stack prefixes.
        """
        registered_name = f"{prefix}{theme_instance.name}"
        if registered_name in self._theme_data:
            _logger.error(
                "Duplicate theme %r, keeping the one that was loaded first",
                registered_name
            )
            return

        self._theme_names.append(registered_name)
        self._theme_data[registered_name] = ThemeData(
            prefix=prefix,
            textual_theme=replace(
                theme_instance,
                name=registered_name,
                variables=dict(theme_instance.variables)
            ),
            css_files=css_files
        )
        _logger.info("Registered theme: %r", registered_name)

    def get_previously_used_theme(
        self, theme_config_file: Path, default_theme_name: str
    ) -> str:
        """
        Returns the name of the previously used theme from the config file.

        Parameters
        ----------
        theme_config_file : Path
            Path to the config file which contains the name of the theme.
        default_theme_name : str
            The default theme name to return if no previous theme is found.

        Returns
        -------
        str
            The name of the last used theme or the default name.

        Raises
        ------
        json.JSONDecodeError
            If the config file contains invalid JSON.
        IOError
            If there's an error reading the config file.
        """
        if theme_config_file.exists():
            try:
                with theme_config_file.open() as f:
                    config = cast("dict[str, str]", json.load(f))
                    if "theme" not in config:
                        _logger.warning(
                            "Invalid theme config format in %r",
                            str(theme_config_file)
                        )
                        return default_theme_name
                    return config["theme"]
            except (OSError, json.JSONDecodeError):
                return default_theme_name
        return default_theme_name

    def register_themes_in_textual_app(self, app: App[None]) -> None:
        """
        Registers all loaded themes in the given Textual application.

        Registration reads the stored themes without modifying them, so the
        same loader can be registered in more than one application.

        Parameters
        ----------
        app : App
            The instance of the Textual application.
        """
        # Sort themes, first TERMCORE_THEME_PREFIX, then CUSTOM_THEME_PREFIX
        self._theme_names.sort(key=self._registration_order)

        # Loop through name list instead of dict to keep alphabetic order
        for theme_name in self._theme_names:
            app.register_theme(self._theme_data[theme_name].textual_theme)

    def _registration_order(self, theme_name: str) -> tuple[int, str]:
        """Sorts termcore themes before custom ones, then alphabetically."""
        is_custom = \
            self._theme_data[theme_name].prefix != self._termcore_theme_prefix
        return int(is_custom), theme_name

    def set_previous_theme_in_textual_app(
        self, app: App[None], default_theme_name: str, theme_config_file: Path
    ) -> None:
        """
        Set the previously used theme in the given Textual application.

        Parameters
        ----------
        app : App
            The instance of the Textual application.
        default_theme_name : str
            The default theme name to use if no previous theme is found.
        theme_config_file : Path
            Path to the config file containing the previous theme.
        """
        theme_name = self.get_previously_used_theme(
            theme_config_file, default_theme_name
        )

        # A theme removed between two runs is the ordinary case, and a caller
        # that passes a default expects it to be used rather than ignored
        if theme_name not in app.available_themes:
            _logger.warning(
                "Stored theme %r is not registered, falling back to %r",
                theme_name, default_theme_name
            )
            theme_name = default_theme_name

        if theme_name not in app.available_themes:
            _logger.error(
                "Default theme %r is not registered either, leaving the "
                "theme as it is", theme_name
            )
            return

        app.theme = theme_name
        _logger.info("Set previous theme: %r", theme_name)

    def save_theme_to_config(
        self, theme_name: str, theme_config_file: Path
    ) -> None:
        """
        Saves the name of the active theme in the config file.

        Raises
        ------
        IOError
            If there's an error writing to the config file.
        """
        try:
            with theme_config_file.open("w") as f:
                json.dump({"theme": theme_name}, f)
        except OSError:
            _logger.exception("Could not save theme config")

    def load_theme_css(self, theme_name: str, app: App[None]) -> None:
        """
        Loads the CSS files for the current theme.

        A theme without a stylesheet and a theme this loader never registered
        (one of Textual's built-ins, for instance) are both normal: the CSS of
        the previous theme is removed and nothing is loaded in its place.

        Parameters
        ----------
        theme_name : str
            The registered name of the theme, including its prefix.
        app : App
            The instance of the Textual application.
        """
        # Remove CSS from previous theme
        self._remove_all_theme_css(app)

        theme_data = self._theme_data.get(theme_name)
        css_files = theme_data.css_files if theme_data else None
        if css_files:
            self._read_css_files(css_files, app)
        else:
            _logger.debug("Theme %r has no stylesheet", theme_name)

        self._apply_stylesheet(app)

    def _read_css_files(self, css_files: list[str], app: App[None]) -> None:
        """Reads the given CSS files into the app's stylesheet."""
        for css_file in css_files:
            try:
                app.stylesheet.read(css_file)
                _logger.debug("Loaded CSS file: %r", css_file)
            except Exception:
                _logger.exception("Error loading CSS file %r", css_file)

    def _apply_stylesheet(self, app: App[None]) -> None:
        """
        Re-parses the stylesheet so that changes take effect.

        A theme shipping invalid TCSS would otherwise take the whole
        application down from inside this library. Keeping the previous
        stylesheet is a defined state; the failure goes to the log.
        """
        try:
            app.stylesheet.reparse()
        except Exception:
            _logger.exception(
                "Theme stylesheet could not be parsed, keeping the previous "
                "one"
            )
            return

        try:
            app.stylesheet.update(app.screen)
        except Exception:
            _logger.exception("Error updating stylesheet")

    def _remove_all_theme_css(self, app: App[None]) -> None:
        """
        Remove all CSS files that were loaded from a theme folder.

        This is necessary when switching themes to avoid conflicts
        between styles from different themes.

        The files this loader actually loaded are the yardstick, not a fixed
        directory - otherwise the stylesheet of a consumer's own theme folder
        would never be removed.

        Parameters
        ----------
        app : App
            The instance of the Textual application.
        """
        theme_css_paths = {
            Path(css_file).resolve()
            for theme_data in self._theme_data.values()
            for css_file in (theme_data.css_files or [])
        }

        for key in list(app.stylesheet.source.keys()):
            path_str, _ = key
            try:
                css_path = Path(path_str).resolve()
            except (OSError, ValueError):
                # An unresolvable path is simply not one of ours
                continue

            if css_path in theme_css_paths:
                _logger.debug("Removing CSS file: %r", path_str)
                del app.stylesheet.source[key]

    def change_to_next_or_previous_theme(
        self, direction: int, app: App[None]
    ) -> None:
        """
        Change to the next or previous theme in the list.

        Cycling deliberately walks every theme the app knows, including
        Textual's built-ins, which simply carry no termcore stylesheet.

        Parameters
        ----------
        direction : int
            1 for next theme, -1 for previous theme.
        app : App
            The instance of the Textual application.
        """
        themes = list(app.available_themes)
        current_index = themes.index(app.theme)
        next_index = (current_index + direction) % len(themes)
        app.theme = themes[next_index]
