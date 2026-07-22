"""
Tests for the status bar as it actually renders.

The two halves are different things and the tests keep them apart: `info`
stands, `message` passes. What only a running app shows is the spacing
between them, which is why this goes through `run_test`.
"""

from textual.app import App, ComposeResult
from textual.widgets import Static

from termcore.tui.custom_widgets.status_bar import StatusBar
from termcore.util.string import cell_width

WIDTH = 60


class StatusApp(App[None]):
    """An app whose only chrome is the status bar under test."""

    def compose(self) -> ComposeResult:
        yield Static("body")
        yield StatusBar()

    def on_key(self) -> None:
        # The convention the widget's docstring describes: whoever owns the
        # bar clears the passing half on the next key.
        self.query_one(StatusBar).message = ""


def rendered(app: StatusApp) -> str:
    """Returns the bar's rendered text."""
    return str(app.query_one(StatusBar).visual)


class TestHalves:
    async def test_the_standing_half_opens_the_line(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            app.query_one(StatusBar).info = "3 tasks · 1 done"
            await pilot.pause()

            assert rendered(app).startswith("3 tasks · 1 done")

    async def test_the_passing_half_closes_it(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            app.query_one(StatusBar).message = "task added"
            await pilot.pause()

            assert rendered(app).endswith("task added")

    async def test_both_fit_on_one_line(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            bar = app.query_one(StatusBar)
            bar.info = "3 tasks"
            bar.message = "task added"
            await pilot.pause()
            text = rendered(app)

            assert "\n" not in text
            assert text.startswith("3 tasks")
            assert text.endswith("task added")

    async def test_an_empty_message_leaves_the_right_blank(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            app.query_one(StatusBar).info = "3 tasks"
            await pilot.pause()

            assert rendered(app) == "3 tasks"


class TestSpacing:
    async def test_the_two_halves_span_the_width(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            bar = app.query_one(StatusBar)
            bar.info = "left"
            bar.message = "right"
            await pilot.pause()

            assert cell_width(rendered(app)) == bar.size.width

    async def test_a_crowded_line_keeps_one_space_between(self) -> None:
        # Nothing is truncated; the gap closes and the line clips.
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            bar = app.query_one(StatusBar)
            bar.info = "x" * WIDTH
            bar.message = "y" * WIDTH
            await pilot.pause()

            assert " " in rendered(app)

    async def test_wide_characters_are_measured_in_cells(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            bar = app.query_one(StatusBar)
            bar.info = "日本語"
            bar.message = "右"
            await pilot.pause()

            assert cell_width(rendered(app)) == bar.size.width


class TestClearing:
    async def test_the_message_survives_until_a_key_is_pressed(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            app.query_one(StatusBar).message = "theme: classic-black"
            await pilot.pause()

            assert "theme" in rendered(app)

    async def test_a_key_press_clears_it(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            app.query_one(StatusBar).message = "theme: classic-black"
            await pilot.pause()
            await pilot.press("x")
            await pilot.pause()

            assert "theme" not in rendered(app)

    async def test_clearing_the_message_leaves_the_info(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            bar = app.query_one(StatusBar)
            bar.info = "3 tasks"
            bar.message = "task added"
            await pilot.pause()
            await pilot.press("x")
            await pilot.pause()

            assert rendered(app) == "3 tasks"


class TestTheDimmingIsReal:
    """
    Checked on the rendered colour, not on the style string.

    `info` first shipped with `$text-muted`, an `auto` colour that resolves
    to white inside a Content style string - the opposite of dimmed, and
    invisible to any test that only reads the style back.
    """

    async def test_the_standing_half_is_dimmed(self) -> None:
        app = StatusApp()

        async with app.run_test(size=(WIDTH, 8)) as pilot:
            await pilot.pause()
            bar = app.query_one(StatusBar)
            bar.info = "3 tasks"
            await pilot.pause()
            segment = next(
                seg
                for seg in bar.render_lines(bar.region.size.region)[0]
                if "3 tasks" in seg.text
            )
            colour = segment.style.color if segment.style else None
            triplet = colour.triplet if colour is not None else None

            assert triplet is not None
            assert (triplet.red, triplet.green, triplet.blue) != (255, 255, 255)
