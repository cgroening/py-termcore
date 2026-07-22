"""Tests for the header as it actually renders.

The packing is pinned in test_tab_rows; what is left for here is what only a
running app shows: that the widget grows with its rows instead of clipping
them, that a resize re-wraps, and that the active tab is told apart.
"""

from textual.app import App, ComposeResult
from textual.content import Content
from textual.widgets import Static

from termcore.tui.custom_widgets.app_header import AppHeader
from termcore.tui.custom_widgets.tab_rows import HeaderTab

TABS = [
    HeaderTab("tasks_tab", "1", "Tasks"),
    HeaderTab("done_tab", "2", "Done"),
    HeaderTab("notes_tab", "3", "Notes"),
]


class HeaderApp(App[None]):
    """An app whose only chrome is the header under test."""

    def __init__(self, active: str = "tasks_tab") -> None:
        super().__init__()
        self.active = active

    def compose(self) -> ComposeResult:
        yield AppHeader("Termplate", TABS, active=self.active)
        yield Static("body")


def lines(app: HeaderApp) -> list[str]:
    """Returns the header's rendered text, row by row."""
    return str(content(app)).split("\n")


def content(app: HeaderApp) -> Content:
    """Returns the header's rendered content, styles included."""
    visual = app.query_one(AppHeader).visual
    assert isinstance(visual, Content)

    return visual


def styles_at(app: HeaderApp, token: str) -> set[str]:
    """Returns the styles covering the first character of the token."""
    rendered = content(app)
    start = str(rendered).index(token)

    return {
        str(span.style)
        for span in rendered.spans
        if span.start <= start < span.end
    }


class TestRendering:
    async def test_the_brand_opens_the_first_row(self) -> None:
        app = HeaderApp()

        async with app.run_test(size=(90, 10)) as pilot:
            await pilot.pause()

            assert lines(app)[0].startswith(" Termplate   ")

    async def test_every_tab_is_rendered_with_its_key(self) -> None:
        app = HeaderApp()

        async with app.run_test(size=(90, 10)) as pilot:
            await pilot.pause()
            text = "\n".join(lines(app))

            for tab in TABS:
                assert f"[{tab.key}] {tab.label}" in text

    async def test_a_wide_terminal_needs_one_row(self) -> None:
        app = HeaderApp()

        async with app.run_test(size=(90, 10)) as pilot:
            await pilot.pause()

            assert len(lines(app)) == 1

    async def test_the_separator_sits_only_between_tabs(self) -> None:
        # Never at the end of a row, never at the start of the next.
        app = HeaderApp()

        async with app.run_test(size=(90, 10)) as pilot:
            await pilot.pause()

            for line in lines(app):
                assert not line.rstrip().endswith("│")
                assert not line.strip().startswith("│")


class TestWrapping:
    async def test_a_narrow_terminal_wraps(self) -> None:
        app = HeaderApp()

        async with app.run_test(size=(32, 10)) as pilot:
            await pilot.pause()

            assert len(lines(app)) > 1

    async def test_a_continuation_row_is_blank_under_the_brand(self) -> None:
        app = HeaderApp()

        async with app.run_test(size=(32, 10)) as pilot:
            await pilot.pause()
            rendered = lines(app)
            column = len(rendered[0]) - len(rendered[0].lstrip())

            assert "Termplate" not in rendered[1]
            assert rendered[1].startswith(" " * column)

    async def test_the_widget_grows_with_its_rows(self) -> None:
        # height: auto - a fixed height would clip the wrapped rows, which is
        # exactly what Textual's own Header does at its fixed 1 or 3.
        app = HeaderApp()

        async with app.run_test(size=(32, 10)) as pilot:
            await pilot.pause()
            header = app.query_one(AppHeader)

            assert len(lines(app)) > 1
            assert header.size.height == len(lines(app))
            assert header.outer_size.height == header.size.height + 2

    async def test_widening_the_terminal_collapses_the_rows(self) -> None:
        app = HeaderApp()

        async with app.run_test(size=(32, 10)) as pilot:
            await pilot.pause()
            narrow = len(lines(app))

            await pilot.resize_terminal(90, 10)
            await pilot.pause()
            await pilot.pause()

            assert narrow > 1
            assert len(lines(app)) == 1


class TestActiveTab:
    async def test_the_active_tab_is_styled_apart(self) -> None:
        app = HeaderApp(active="done_tab")

        async with app.run_test(size=(90, 10)) as pilot:
            await pilot.pause()
            assert "bold" in styles_at(app, "[2] Done")

    async def test_changing_the_active_tab_redraws(self) -> None:
        app = HeaderApp(active="tasks_tab")

        async with app.run_test(size=(90, 10)) as pilot:
            await pilot.pause()
            app.query_one(AppHeader).active = "notes_tab"
            await pilot.pause()

            assert "bold" in styles_at(app, "[3] Notes")


class TestTabsCanChange:
    async def test_set_tabs_replaces_the_bar(self) -> None:
        app = HeaderApp()

        async with app.run_test(size=(90, 10)) as pilot:
            await pilot.pause()
            header = app.query_one(AppHeader)
            header.set_tabs([HeaderTab("only_tab", "9", "Only")])
            await pilot.pause()

            assert "[9] Only" in "\n".join(lines(app))
            assert "[1] Tasks" not in "\n".join(lines(app))
