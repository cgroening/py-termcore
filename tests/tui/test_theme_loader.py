"""Tests for theme discovery, registration, stylesheets and persistence.

The assertions run against a loader and a live Textual app rather than
against the text of the theme modules. Every bug this module ever shipped was
invisible in the source and only showed up in the object graph the loader
builds - a stacked prefix, a stylesheet that silently never loaded.
"""

import json
import logging
from pathlib import Path

import pytest
from textual.app import App
from textual.theme import BUILTIN_THEMES

from termcore.tui.theme_loader import (
    DEFAULT_CUSTOM_THEME_PREFIX,
    DEFAULT_TERMCORE_THEME_PREFIX,
    STANDARD_THEMES_DIR,
    ThemeLoader,
)
from tests.tui.conftest import MakeTheme

CSS = "Screen { background: #101010; }"
OTHER_CSS = "Screen { background: #202020; }"


def bundled_theme_folders() -> list[Path]:
    """Returns the theme folders that ship with termcore."""
    return [
        folder for folder in STANDARD_THEMES_DIR.iterdir()
        if folder.is_dir() and not folder.name.startswith(("_", "."))
    ]


def registered_names(app: App[None]) -> list[str]:
    """Returns the theme names a loader put into the app, in order."""
    return [
        name for name in app.available_themes if name not in BUILTIN_THEMES
    ]


def names_in_app(loader: ThemeLoader) -> list[str]:
    """Registers the loader in a fresh app and returns the names it added."""
    app: App[None] = App()
    loader.register_themes_in_textual_app(app)
    return registered_names(app)


def loaded_css_paths(app: App[None]) -> set[Path]:
    """Returns the resolved paths of every stylesheet the app has read."""
    return {Path(path).resolve() for path, _ in app.stylesheet.source}


def custom_loader(theme_root: Path) -> ThemeLoader:
    """Returns a loader for a custom theme folder, without termcore's own."""
    return ThemeLoader.custom_only(str(theme_root))


class TestThemeRegistryIsPerInstance:
    """The registry used to be a class attribute shared by every loader.

    A second app in the same process saw CUSTOM_CUSTOM_<name>, a third
    CUSTOM_CUSTOM_CUSTOM_<name>. One app per process hid it in production;
    a suite that builds an app per test does not.
    """

    def test_a_second_loader_sees_the_same_themes(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")

        first = custom_loader(theme_root)
        second = custom_loader(theme_root)

        assert names_in_app(first) == names_in_app(second)

    def test_a_second_loader_does_not_stack_prefixes(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        # The actual regression: CUSTOM_CUSTOM_solar on the second instance.
        make_theme(theme_root, "solar")

        custom_loader(theme_root)
        second = custom_loader(theme_root)

        assert names_in_app(second) == [f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"]

    def test_a_third_loader_does_not_accumulate_entries(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")

        custom_loader(theme_root)
        custom_loader(theme_root)
        third = custom_loader(theme_root)

        assert len(names_in_app(third)) == 1

    def test_a_second_loader_still_finds_the_bundled_themes(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        # A consumer's theme folder used to shadow termcore's own on every
        # loader after the first, because both were imported as a package
        # named after the folder. The shared registry hid it: the second
        # loader still saw the first one's themes.
        make_theme(theme_root, "solar")
        first = ThemeLoader(theme_folder=str(theme_root))
        second = ThemeLoader(theme_folder=str(theme_root))

        assert names_in_app(second) == names_in_app(first)
        assert len(names_in_app(second)) == len(bundled_theme_folders()) + 1

    def test_a_new_loader_does_not_disturb_an_existing_one(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")
        first = custom_loader(theme_root)
        before = names_in_app(first)

        custom_loader(theme_root)

        assert names_in_app(first) == before


class TestRegistrationIsRepeatable:
    """Registering reads the stored themes; it must not rewrite them."""

    def test_two_apps_receive_the_same_names(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)

        first_app: App[None] = App()
        second_app: App[None] = App()
        loader.register_themes_in_textual_app(first_app)
        loader.register_themes_in_textual_app(second_app)

        assert registered_names(first_app) == registered_names(second_app)

    def test_registering_twice_does_not_stack_prefixes(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()

        loader.register_themes_in_textual_app(app)
        loader.register_themes_in_textual_app(app)

        assert registered_names(app) == [
            f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"
        ]

    def test_a_second_prefix_does_not_inherit_the_first(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        # The prefix belongs to the registration, not to the theme itself.
        # Registering under one prefix must leave the theme untouched for a
        # loader that registers the same folder under another.
        make_theme(theme_root, "solar")
        first = ThemeLoader.custom_only(
            str(theme_root), custom_theme_prefix="ONE_"
        )
        second = ThemeLoader.custom_only(
            str(theme_root), custom_theme_prefix="TWO_"
        )
        first.register_themes_in_textual_app(App())

        assert names_in_app(second) == ["TWO_solar"]


class TestThemeIdentityIsTheDeclaredName:
    """A theme is its declared name plus a prefix, never its folder name.

    Themes used to be stored under the folder name but have their CSS looked
    up by the theme name, so a folder that disagreed with its theme.py
    registered fine and silently lost its stylesheet.
    """

    def test_a_theme_registers_under_its_declared_name(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "any-folder-name", theme_name="solar")

        loader = custom_loader(theme_root)

        assert names_in_app(loader) == [f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"]

    async def test_the_stylesheet_is_found_when_the_folder_name_differs(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        folder = make_theme(
            theme_root, "any-folder-name", theme_name="solar", css=CSS
        )
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            loader.load_theme_css(f"{DEFAULT_CUSTOM_THEME_PREFIX}solar", app)

            assert (folder / "style.css").resolve() in loaded_css_paths(app)

    def test_a_custom_theme_may_reuse_a_bundled_name(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        # Different prefixes, so both are registered and neither is lost.
        bundled = bundled_theme_folders()[0].name
        make_theme(theme_root, bundled)

        loader = ThemeLoader(theme_folder=str(theme_root))
        names = names_in_app(loader)

        assert f"{DEFAULT_TERMCORE_THEME_PREFIX}{bundled}" in names
        assert f"{DEFAULT_CUSTOM_THEME_PREFIX}{bundled}" in names

    def test_a_duplicate_declared_name_is_refused(
        self, theme_root: Path, make_theme: MakeTheme,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        make_theme(theme_root, "first-folder", theme_name="solar")
        make_theme(theme_root, "second-folder", theme_name="solar")

        with caplog.at_level(logging.ERROR):
            loader = custom_loader(theme_root)

        assert names_in_app(loader) == [f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"]
        assert "Duplicate theme" in caplog.text


class TestThemeDiscovery:
    def test_every_bundled_theme_folder_is_registered(self) -> None:
        loader = ThemeLoader()

        assert len(names_in_app(loader)) == len(bundled_theme_folders())

    def test_bundled_themes_carry_the_termcore_prefix(self) -> None:
        loader = ThemeLoader()

        assert all(
            name.startswith(DEFAULT_TERMCORE_THEME_PREFIX)
            for name in names_in_app(loader)
        )

    def test_a_folder_without_theme_py_is_skipped(
        self, theme_root: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        (theme_root / "empty").mkdir()

        with caplog.at_level(logging.WARNING):
            loader = custom_loader(theme_root)

        assert names_in_app(loader) == []
        assert "no theme.py" in caplog.text

    def test_a_module_without_textual_theme_is_skipped(
        self, theme_root: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        folder = theme_root / "broken"
        folder.mkdir()
        (folder / "theme.py").write_text("OTHER = 1\n", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            loader = custom_loader(theme_root)

        assert names_in_app(loader) == []
        assert "no TEXTUAL_THEME defined" in caplog.text

    def test_a_theme_module_that_fails_to_import_is_skipped(
        self, theme_root: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        folder = theme_root / "broken"
        folder.mkdir()
        (folder / "theme.py").write_text(
            "raise ValueError(\"boom\")\n", encoding="utf-8"
        )

        with caplog.at_level(logging.ERROR):
            loader = custom_loader(theme_root)

        assert names_in_app(loader) == []
        assert "Error loading theme folder" in caplog.text

    def test_underscore_and_dot_folders_are_ignored(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "_private")
        make_theme(theme_root, ".hidden")
        make_theme(theme_root, "solar")

        loader = custom_loader(theme_root)

        assert names_in_app(loader) == [f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"]

    def test_loose_files_are_ignored(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")
        (theme_root / "README.md").write_text("not a theme", encoding="utf-8")

        loader = custom_loader(theme_root)

        assert names_in_app(loader) == [f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"]

    def test_a_missing_custom_folder_leaves_bundled_themes_intact(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            loader = ThemeLoader(theme_folder=str(tmp_path / "gone"))

        assert len(names_in_app(loader)) == len(bundled_theme_folders())
        assert "not found" in caplog.text

    def test_bundled_themes_can_be_excluded(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")

        loader = custom_loader(theme_root)

        assert names_in_app(loader) == [f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"]


class TestRegistrationOrder:
    def test_bundled_themes_come_before_custom_ones(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        # Alphabetically first, so only the grouping can put it last.
        make_theme(theme_root, "aaa-first-alphabetically")

        loader = ThemeLoader(theme_folder=str(theme_root))
        names = names_in_app(loader)

        assert names[0].startswith(DEFAULT_TERMCORE_THEME_PREFIX)
        assert names[-1].startswith(DEFAULT_CUSTOM_THEME_PREFIX)

    def test_themes_are_alphabetical_within_their_group(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "zulu")
        make_theme(theme_root, "alpha")
        make_theme(theme_root, "mike")

        loader = custom_loader(theme_root)
        names = names_in_app(loader)

        assert names == sorted(names)


class TestStylesheetLoading:
    async def test_the_stylesheet_of_the_active_theme_is_loaded(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        folder = make_theme(theme_root, "solar", css=CSS)
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            loader.load_theme_css(f"{DEFAULT_CUSTOM_THEME_PREFIX}solar", app)

            assert (folder / "style.css").resolve() in loaded_css_paths(app)

    async def test_switching_themes_removes_the_previous_stylesheet(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        # A consumer's themes live outside termcore's own folder, which is
        # exactly the case the removal used to miss.
        solar = make_theme(theme_root, "solar", css=CSS)
        lunar = make_theme(theme_root, "lunar", css=OTHER_CSS)
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            loader.load_theme_css(f"{DEFAULT_CUSTOM_THEME_PREFIX}solar", app)
            loader.load_theme_css(f"{DEFAULT_CUSTOM_THEME_PREFIX}lunar", app)
            loaded = loaded_css_paths(app)

            assert (lunar / "style.css").resolve() in loaded
            assert (solar / "style.css").resolve() not in loaded

    async def test_a_theme_without_a_stylesheet_is_not_a_warning(
        self, theme_root: Path, make_theme: MakeTheme,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        # Ten of the sixteen bundled themes ship no stylesheet at all.
        make_theme(theme_root, "bare")
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            with caplog.at_level(logging.WARNING):
                loader.load_theme_css(
                    f"{DEFAULT_CUSTOM_THEME_PREFIX}bare", app
                )

            assert caplog.text == ""

    async def test_a_builtin_theme_is_not_a_warning(
        self, theme_root: Path, make_theme: MakeTheme,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        make_theme(theme_root, "solar", css=CSS)
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            with caplog.at_level(logging.WARNING):
                loader.load_theme_css("textual-dark", app)

            assert caplog.text == ""

    async def test_a_builtin_theme_drops_the_previous_stylesheet(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        solar = make_theme(theme_root, "solar", css=CSS)
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            loader.load_theme_css(f"{DEFAULT_CUSTOM_THEME_PREFIX}solar", app)
            loader.load_theme_css("textual-dark", app)

            assert (solar / "style.css").resolve() not in loaded_css_paths(app)


class TestThemePersistence:
    def test_a_saved_theme_is_read_back(self, tmp_path: Path) -> None:
        config = tmp_path / "theme.json"
        loader = ThemeLoader.custom_only(str(tmp_path / "none"))

        loader.save_theme_to_config("CUSTOM_solar", config)

        assert loader.get_previously_used_theme(config, "fallback") \
            == "CUSTOM_solar"

    def test_a_missing_config_file_yields_the_default(
        self, tmp_path: Path
    ) -> None:
        loader = ThemeLoader.custom_only(str(tmp_path / "none"))

        assert loader.get_previously_used_theme(
            tmp_path / "absent.json", "fallback"
        ) == "fallback"

    def test_invalid_json_yields_the_default(self, tmp_path: Path) -> None:
        config = tmp_path / "theme.json"
        config.write_text("{ not json", encoding="utf-8")
        loader = ThemeLoader.custom_only(str(tmp_path / "none"))

        assert loader.get_previously_used_theme(config, "fallback") \
            == "fallback"

    def test_a_config_without_a_theme_key_yields_the_default(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = tmp_path / "theme.json"
        config.write_text(json.dumps({"other": "value"}), encoding="utf-8")
        loader = ThemeLoader.custom_only(str(tmp_path / "none"))

        with caplog.at_level(logging.WARNING):
            result = loader.get_previously_used_theme(config, "fallback")

        assert result == "fallback"
        assert "Invalid theme config format" in caplog.text

    def test_an_unwritable_config_is_reported(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A directory where the config file belongs: open() cannot write it.
        config = tmp_path / "theme.json"
        config.mkdir()
        loader = ThemeLoader.custom_only(str(tmp_path / "none"))

        with caplog.at_level(logging.ERROR):
            loader.save_theme_to_config("CUSTOM_solar", config)

        assert "Could not save theme config" in caplog.text

    def test_a_registered_previous_theme_is_applied(
        self, theme_root: Path, make_theme: MakeTheme, tmp_path: Path
    ) -> None:
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()
        loader.register_themes_in_textual_app(app)
        config = tmp_path / "theme.json"
        name = f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"
        loader.save_theme_to_config(name, config)

        loader.set_previous_theme_in_textual_app(app, name, config)

        assert app.theme == name

    def test_an_unknown_previous_theme_falls_back_to_the_default(
        self, theme_root: Path, make_theme: MakeTheme, tmp_path: Path,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        # A theme removed between two runs used to leave the app on Textual's
        # own default, silently ignoring the default the caller passed.
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()
        loader.register_themes_in_textual_app(app)
        config = tmp_path / "theme.json"
        loader.save_theme_to_config("CUSTOM_gone", config)
        default = f"{DEFAULT_CUSTOM_THEME_PREFIX}solar"

        with caplog.at_level(logging.WARNING):
            loader.set_previous_theme_in_textual_app(app, default, config)

        assert app.theme == default
        assert "is not registered" in caplog.text

    def test_an_unknown_default_is_reported_and_nothing_changes(
        self, theme_root: Path, make_theme: MakeTheme, tmp_path: Path,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()
        loader.register_themes_in_textual_app(app)
        before = app.theme
        config = tmp_path / "theme.json"
        loader.save_theme_to_config("CUSTOM_gone", config)

        with caplog.at_level(logging.ERROR):
            loader.set_previous_theme_in_textual_app(app, "CUSTOM_also_gone",
                                                     config)

        assert app.theme == before
        assert "is not registered either" in caplog.text


class TestABrokenStylesheetDoesNotKillTheApp:
    """reparse() used to run unguarded, so invalid TCSS crashed the app.

    A library has no business taking the whole application down because a
    theme it was handed will not parse.
    """

    async def test_the_application_survives_invalid_tcss(
        self, theme_root: Path, make_theme: MakeTheme,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        make_theme(theme_root, "broken", css="this is not valid tcss {{{")
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)

            with caplog.at_level(logging.ERROR):
                loader.load_theme_css(
                    f"{DEFAULT_CUSTOM_THEME_PREFIX}broken", app
                )

            assert app.is_running
            assert "could not be parsed" in caplog.text


class TestThemeCycling:
    async def test_the_next_theme_wraps_at_the_end(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            app.theme = list(app.available_themes)[-1]

            loader.change_to_next_or_previous_theme(1, app)

            assert app.theme == next(iter(app.available_themes))

    async def test_the_previous_theme_wraps_at_the_start(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            app.theme = next(iter(app.available_themes))

            loader.change_to_next_or_previous_theme(-1, app)

            assert app.theme == list(app.available_themes)[-1]

    async def test_next_then_previous_returns_to_the_start(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            before = app.theme

            loader.change_to_next_or_previous_theme(1, app)
            loader.change_to_next_or_previous_theme(-1, app)

            assert app.theme == before

    async def test_builtin_themes_are_part_of_the_cycle(
        self, theme_root: Path, make_theme: MakeTheme
    ) -> None:
        # A deliberate decision: they render correctly, they just carry no
        # termcore stylesheet.
        make_theme(theme_root, "solar")
        loader = custom_loader(theme_root)
        app: App[None] = App()

        async with app.run_test():
            loader.register_themes_in_textual_app(app)
            app.theme = "textual-dark"

            loader.change_to_next_or_previous_theme(1, app)

            assert app.theme in BUILTIN_THEMES


class TestDiagnosticsAreFilterable:
    def test_records_carry_the_module_logger_name(
        self, theme_root: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Logging through the root logger surfaces as WARNING:root: in every
        # consumer and cannot be filtered per module.
        (theme_root / "empty").mkdir()

        with caplog.at_level(logging.WARNING):
            custom_loader(theme_root)

        assert [record.name for record in caplog.records] \
            == ["termcore.tui.theme_loader"]
