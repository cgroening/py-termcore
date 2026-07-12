import logging
import importlib
import os
import json
import sys
from dataclasses import dataclass
from typing import cast
from pathlib import Path
from textual.app import App
from textual.theme import Theme


DEFAULT_TERMZ_THEME_PREFIX = "TERMZ_"
DEFAULT_CUSTOM_THEME_PREFIX = "CUSTOM_"
SCRIPT_DIR = Path(__file__).parent.parent
STANDARD_THEMES_DIR = SCRIPT_DIR / "tui/themes"


@dataclass(frozen=False, slots=True)
class ThemeData:
    """Data class to hold information of a single theme."""
    name: str
    prefix: str
    textual_theme: Theme
    css_files: list[str] | None = None


class ThemeLoader:
    """
    Loads and manages themes for Textual applications.

    The themes are expected to be in subfolder of `THEME_FOLDER`, each
    containing a `theme.py` file defining a `TEXTUAL_THEME` variable.
    Additionally, any number of `.css` oder `.tcc` files can be included in the
    theme folder.

    This class dynamically imports the theme modules, registers them and makes
    them available for use in the application.
    """
    _theme_folder: str | None
    _termz_theme_prefix: str
    _custom_theme_prefix: str
    _theme_names: list[str] = []
    _theme_data: dict[str, ThemeData] = {}


    def __init__(
        self, theme_folder: str | None = None,
        termz_theme_prefix: str = DEFAULT_TERMZ_THEME_PREFIX or "",
        custom_theme_prefix: str = DEFAULT_CUSTOM_THEME_PREFIX or "",
        include_standard_themes: bool = True
    ) -> None:
        """
        Initializes the ThemeLoader and loads the themes from the specified
        directory.
        """
        self._theme_folder = theme_folder
        self._termz_theme_prefix = termz_theme_prefix
        self._custom_theme_prefix = custom_theme_prefix
        if include_standard_themes:
            self._load_themes(standard_themes=include_standard_themes)
        self._load_themes()  # Custom themes
        self._theme_names.sort()

    def _load_themes(self, standard_themes: bool = False) -> None:
        """Loads themes from the specified folder and register them."""
        result = self._generate_theme_folder_path_and_prefix(standard_themes)
        if not result:
            return

        prefix, theme_folder_path = result
        parent = theme_folder_path.parent
        folder_name = theme_folder_path.name

        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))

        self._clear_package_cache(folder_name)
        self._process_themes(folder_name, prefix, theme_folder_path)
        logging.info(
            f"Found {len(self._theme_names)} themes in \"{theme_folder_path}\"."
        )

    def _generate_theme_folder_path_and_prefix(self, standard_themes: bool) \
    -> tuple[str, Path] | None:
        """
        Checks whether to load standard themes or custom themes and returns
        the corresponding folder path and prefix.
        """
        if standard_themes:
            theme_folder_path = STANDARD_THEMES_DIR.resolve()
            prefix = self._termz_theme_prefix
        else:
            if not self._theme_folder:
                return
            theme_folder_path = Path(self._theme_folder).resolve()
            prefix = self._custom_theme_prefix

        if not theme_folder_path.is_dir():
            logging.warning(
                f"Theme folder \"{theme_folder_path}\" not found. Skipping."
            )
            return

        return prefix, theme_folder_path

    def _clear_package_cache(self, folder_name: str) -> None:
        """
        Clears the entire package from the module cache, including the parent
        package itself - otherwise Python reuses a stale entry pointing to the
        previously loaded folder (critical when both folders share the
        same name, e.g. "themes") and prevents loading new themes.
        """
        for key in list(sys.modules.keys()):
            if key == folder_name or key.startswith(f"{folder_name}."):
                del sys.modules[key]

    def _process_themes(
        self, folder_name: str, prefix: str, theme_folder_path: Path
    ) -> None:
        """Imports and registers themes from the given folder path."""
        for item in os.listdir(theme_folder_path):
            full_path = theme_folder_path / item
            if item.startswith(".") or item.startswith("_") \
            or not full_path.is_dir():
                continue

            module_name = f"{folder_name}.{item}.theme"
            self._import_and_register_theme(
                item, prefix, module_name, str(full_path)
            )

    def _get_css_files_for_theme(self, theme_folder_path: str) -> list[str]:
        """ Generates a list of CSS files in the given folder."""
        css_files: list[str] = []
        for file_name in os.listdir(theme_folder_path):
            if file_name.endswith(".css") or file_name.endswith(".tcss"):
                css_files.append(os.path.join(theme_folder_path, file_name))
        return css_files

    def _import_and_register_theme(
        self, theme_name: str, prefix: str, module_name: str, full_path: str
    ) -> None:
        """
        Imports a theme module and register its theme.

        Raises
        ------
        ModuleNotFoundError
            If the theme module cannot be imported.
        Exception
            If any other error occurs during theme loading.
        """
        try:
            # Import the theme module (theme.py)
            theme_module = importlib.import_module(module_name)
            textual_theme = getattr(theme_module, "TEXTUAL_THEME", None)
            css_files = self._get_css_files_for_theme(full_path)

            # Abort if no TEXTUAL_THEME variable is defined
            if not isinstance(textual_theme, Theme):
                logging.warning(
                    f"Skipping theme \"{theme_name}\" (no TEXTUAL_THEME defined)"
                )
                return

            # Register the theme
            self._save_theme_data(theme_name, prefix, textual_theme, css_files)
            logging.info(f"Registered theme: {theme_name}")
        except ModuleNotFoundError:
            logging.warning(f"Skipping theme \"{theme_name}\" (no theme.py)")
        except Exception as e:
            logging.error(f"Error loading theme \"{theme_name}\": {e}")

    def _save_theme_data(
        self, name: str,
        prefix: str,
        theme_instance: Theme,
        css_files: list[str] | None = None
    ) -> None:
        """
        Saves the theme data into the `theme_data` dictionary and adds the theme
        name to the list of all names.
        """
        self._theme_names.append(name)
        self._theme_data[name] = ThemeData(
            name=name,
            prefix=prefix,
            textual_theme=theme_instance,
            css_files=css_files
        )

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
                with open(theme_config_file, "r") as f:
                    config = cast(dict[str, str], json.load(f))
                    if "theme" not in config:
                        logging.warning(
                            f"Invalid theme config format in {theme_config_file}."
                        )
                        return default_theme_name
                    return config.get("theme", theme_config_file.name)
            except (json.JSONDecodeError, IOError):
                return default_theme_name
        return default_theme_name

    def register_themes_in_textual_app(self, app: App[None]) -> None:
        """
        Registers all loaded themes in the given Textual application.

        Parameters
        ----------
        app : App
            The instance of the Textual application.
        """
        # Sort themes, first TERMZ_THEME_PREFIX, then CUSTOM_THEME_PREFIX
        self._theme_names.sort( key=lambda name: (
            0 if self._theme_data[name].prefix == self._termz_theme_prefix else 1,
            name
        ) )

        # Loop through name list instead of dict to keep alphabetic order
        for theme_name in self._theme_names:
            theme_data = self._theme_data[theme_name]
            theme_data.textual_theme.name = \
                f"{theme_data.prefix}{theme_data.textual_theme.name}"
            app.register_theme(theme_data.textual_theme)

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
        if theme_name in app.available_themes:
            app.theme = theme_name

        logging.info(f"Set previous theme: {theme_name}")

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
            with open(theme_config_file, "w") as f:
                json.dump({"theme": theme_name}, f)
        except IOError as e:
            logging.error(f"Could not save theme config: {e}")

    def load_theme_css(self, theme_name: str, app: App[None]) -> None:
        """
        Loads the CSS files for the current theme.

        Parameters
        ----------
        theme_name : str
            The name of the theme to load.
        app : App
            The instance of the Textual application.
        """
        # Remove CSS from previous theme
        self._remove_all_theme_css(app)

        # Remove any prefixes
        clean_name = theme_name
        for prefix in [self._termz_theme_prefix, self._custom_theme_prefix]:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):]
                break

        # Load all CSS files that are in folder themes/{theme_name}/
        theme_data = self._theme_data.get(clean_name)
        if not theme_data or not theme_data.css_files:
            logging.warning(f"No CSS files found for theme: {clean_name}")
            return

        for css_file in theme_data.css_files:
            try:
                app.stylesheet.read(str(css_file))
                logging.debug(f"Loaded CSS file: {css_file}")
            except Exception as e:
                logging.error(f"Error loading CSS file {css_file}: {e}")

        # Re-parse and apply to make sure changes take effect
        app.stylesheet.reparse()
        try:
            app.stylesheet.update(app.screen)
        except Exception as e:
            logging.error(f"Error updating stylesheet: {e}")

    def _remove_all_theme_css(self, app: App[None]) -> None:
        """
        Remove all CSS files that were loaded from the /themes/ folder.

        This is necessary when switching themes to avoid conflicts
        between styles from different themes.

        Parameters
        ----------
        app : App
            The instance of the Textual application.
        """
        themes_dir = STANDARD_THEMES_DIR.resolve()

        logging.debug(f"Removing CSS files from themes directory: {themes_dir}")

        for key in list(app.stylesheet.source.keys()):
            path_str, _ = key
            try:
                css_path = Path(path_str).resolve()
            except Exception:
                continue

            # Check if the CSS file is inside the themes directory
            if themes_dir in css_path.parents:
                del app.stylesheet.source[key]

    def change_to_next_or_previous_theme(
        self, direction: int, app: App[None]
    ) -> None:
        """
        Change to the next or previous theme in the list.

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

