"""Tests for the multi-line footer as it actually renders.

The widget had no tests at all before grouping arrived, so the rules it has
always followed are pinned here alongside the new ones. Everything runs
through `run_test`, because a footer that composes the right widget tree can
still lay it out wrongly, and only a running app shows the difference.
"""

from collections.abc import Sequence

import pytest
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets._footer import FooterKey

from termcore.tui.binding_groups import BindingGroup
from termcore.tui.custom_widgets.footer_rows import hint_width
from termcore.tui.custom_widgets.multiline_footer import (
    FooterGroupLabel,
    FooterRow,
    FooterSeparator,
    MultiLineFooter,
)
from termcore.util.string import cell_width

TASKS = BindingGroup(
    name="Tasks",
    scope="tasks_tab",
    bindings=(
        Binding("a", "add", "Add"),
        Binding("d", "done", "Done"),
    ),
)
APPEARANCE = BindingGroup(
    name="Appearance",
    scope="_global",
    bindings=(Binding("w", "theme", "Theme"),),
)
INACTIVE = BindingGroup(
    name="Hidden",
    scope="done_tab",
    bindings=(Binding("r", "reopen", "Reopen"),),
)


class FooterApp(App[None]):
    """An app whose only content is the footer under test."""

    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [  # noqa: RUF012 - Textual reads this as a class attribute
        Binding("a", "add", "Add"),
        Binding("d", "done", "Done"),
        Binding("w", "theme", "Theme"),
    ]

    def __init__(self, groups: Sequence[BindingGroup] | None = None) -> None:
        super().__init__()
        self.groups = groups
        self.pressed: list[str] = []

    def compose(self) -> ComposeResult:
        yield MultiLineFooter(groups=self.groups)

    def action_add(self) -> None:
        self.pressed.append("add")

    def action_done(self) -> None:
        self.pressed.append("done")

    def action_theme(self) -> None:
        self.pressed.append("theme")


def row_keys(app: FooterApp) -> list[list[str]]:
    """Returns the key of every FooterKey, row by row."""
    return [
        [key.key for key in row.query(FooterKey).results()]
        for row in app.query(FooterRow).results()
    ]


def row_labels(app: FooterApp) -> list[str]:
    """Returns the text of every group label, row by row."""
    return [
        str(label.visual)
        for label in app.query(FooterGroupLabel).results()
    ]


class TestGroupedRows:
    async def test_each_group_gets_its_own_row(self) -> None:
        app = FooterApp([TASKS, APPEARANCE])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()

            assert row_keys(app) == [["a", "d"], ["w"]]

    async def test_rows_follow_the_declared_order(self) -> None:
        app = FooterApp([APPEARANCE, TASKS])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()

            assert row_keys(app) == [["w"], ["a", "d"]]

    async def test_a_group_with_no_active_binding_renders_no_row(self) -> None:
        app = FooterApp([TASKS, INACTIVE])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()

            assert row_keys(app) == [["a", "d"]]

    async def test_every_label_renders_at_the_same_width(self) -> None:
        # This is the alignment the whole design rests on.
        app = FooterApp([TASKS, APPEARANCE])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()
            widths = {
                label.size.width
                for label in app.query(FooterGroupLabel).results()
            }

            assert len(widths) == 1

    async def test_a_label_is_as_wide_as_its_padded_text(self) -> None:
        app = FooterApp([TASKS, APPEARANCE])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()

            for label in app.query(FooterGroupLabel).results():
                assert label.size.width == cell_width(str(label.visual))

    async def test_the_labels_carry_the_group_names(self) -> None:
        app = FooterApp([TASKS, APPEARANCE])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()

            assert [text.strip() for text in row_labels(app)] == [
                "Tasks:", "Appearance:"
            ]


class TestSeparators:
    async def test_a_row_has_one_separator_between_its_keys(self) -> None:
        app = FooterApp([TASKS, APPEARANCE])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()
            counts = [
                len(list(row.query(FooterSeparator).results()))
                for row in app.query(FooterRow).results()
            ]

            assert counts == [1, 0]

    async def test_a_separator_is_one_cell_wide(self) -> None:
        # The surrounding spaces come from FooterKey's padding, so a wider
        # separator would double them.
        app = FooterApp([TASKS])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()

            for mark in app.query(FooterSeparator).results():
                assert mark.size.width == 1


class TestUngrouped:
    async def test_without_groups_there_is_one_row_and_no_labels(
        self,
    ) -> None:
        app = FooterApp()

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()

            assert row_keys(app) == [["a", "d", "w"]]
            assert row_labels(app) == []

    async def test_a_narrow_terminal_wraps_the_keys(self) -> None:
        app = FooterApp()

        async with app.run_test(size=(16, 8)) as pilot:
            await pilot.pause()

            assert len(row_keys(app)) > 1


class TestResize:
    async def test_widening_the_terminal_collapses_the_rows(self) -> None:
        app = FooterApp([TASKS])

        async with app.run_test(size=(14, 8)) as pilot:
            await pilot.pause()
            narrow = len(row_keys(app))

            await pilot.resize_terminal(80, 8)
            await pilot.pause()
            await pilot.pause()

            assert narrow > 1
            assert len(row_keys(app)) == 1


class TestMouse:
    async def test_clicking_a_key_runs_its_action(self) -> None:
        # Rendering each row as one piece of text would be simpler and would
        # silently cost exactly this.
        app = FooterApp([TASKS])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()
            key = next(iter(app.query(FooterKey).results()))

            await pilot.click(key)
            await pilot.pause()

            assert app.pressed == ["add"]


class TestCommandPalette:
    async def test_the_palette_key_sits_in_the_last_row(self) -> None:
        class PaletteApp(FooterApp):
            ENABLE_COMMAND_PALETTE = True

        app = PaletteApp([TASKS, APPEARANCE])

        async with app.run_test(size=(80, 6)) as pilot:
            await pilot.pause()
            rows = list(app.query(FooterRow).results())
            palette = list(app.query(FooterKey)
                .filter(".-command-palette").results())

            assert len(palette) == 1
            assert palette[0] in list(rows[-1].query(FooterKey).results())

    async def test_the_last_row_leaves_room_for_the_palette_key(self) -> None:
        # The palette key is docked right. Without reserving its width, the
        # last row wraps into that space and the two overlap.
        class PaletteApp(FooterApp):
            ENABLE_COMMAND_PALETTE = True

        app = PaletteApp([TASKS])
        width = 80

        async with app.run_test(size=(width, 6)) as pilot:
            await pilot.pause()
            last = list(app.query(FooterRow).results())[-1]
            palette = next(iter(app.query(FooterKey)
                .filter(".-command-palette").results()))
            used = sum(
                child.size.width
                for child in last.children
                if child is not palette
            )

            assert used + palette.size.width <= width


@pytest.mark.parametrize("hint_count", [1, 3, 9])
async def test_the_estimator_matches_what_is_rendered(
    hint_count: int,
) -> None:
    """The wrap budget and the renderer must agree, or rows overflow."""
    bindings = [
        Binding(chr(ord("a") + i), f"act{i}", f"Action {i}")
        for i in range(hint_count)
    ]

    class WideApp(FooterApp):
        ENABLE_COMMAND_PALETTE = False
        BINDINGS = bindings

    app = WideApp()

    async with app.run_test(size=(200, 6)) as pilot:
        await pilot.pause()
        for key in app.query(FooterKey).results():
            estimated = hint_width(key.key_display, key.description)

            assert key.size.width == estimated
