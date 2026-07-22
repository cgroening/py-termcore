"""
Tests for the help overlay as it runs.

The overlay is a search field that drives a list while never giving up the
focus, and a scope switch that changes what the list is drawn from. Neither
of those can be checked by looking at the composed widget tree, so all of it
runs through `run_test`.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, OptionList, Static

from termcore.tui.binding_groups import BindingGroup
from termcore.tui.help_screen import HelpScreen

TASKS = BindingGroup(
    name="Tasks",
    scope="tasks_tab",
    scope_title="Tasks",
    bindings=(
        Binding("a", "tasks_tab_add", "Add"),
        Binding("d", "tasks_tab_done", "Done"),
    ),
)
DONE = BindingGroup(
    name="Done",
    scope="done_tab",
    scope_title="Done",
    bindings=(Binding("r", "done_tab_reopen", "Reopen"),),
)
GROUPS = [TASKS, DONE]


class HelpApp(App[None]):
    """An app that does nothing but show the overlay."""

    def __init__(self, active: frozenset[str] = frozenset()) -> None:
        super().__init__()
        self.active = active

    def compose(self) -> ComposeResult:
        yield Static("body")

    def on_mount(self) -> None:
        self.push_screen(HelpScreen(GROUPS, self.active))


def option_count(app: HelpApp) -> int:
    """Returns how many rows the list currently holds, headings included."""
    return app.screen.query_one(OptionList).option_count


def status(app: HelpApp) -> str:
    """Returns the text of the overlay's status line."""
    return str(app.screen.query_one(".help-status", Static).visual)


class TestOpening:
    async def test_it_lists_every_group_and_binding(self) -> None:
        # Two headings plus three shortcuts.
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            assert option_count(app) == 5

    async def test_the_search_field_takes_the_focus(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            assert isinstance(app.focused, Input)

    async def test_the_status_line_counts_the_shortcuts(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            assert status(app).startswith("3 shortcuts")


class TestSearching:
    async def test_typing_filters_the_list(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("r", "e", "o")
            await pilot.pause()

            assert option_count(app) == 2  # one heading, one shortcut
            assert status(app).startswith("1 shortcuts")

    async def test_clearing_the_query_restores_everything(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("r", "e", "o")
            await pilot.pause()
            await pilot.press("backspace", "backspace", "backspace")
            await pilot.pause()

            assert option_count(app) == 5

    async def test_a_query_matching_nothing_empties_the_list(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("z", "z", "z", "z")
            await pilot.pause()

            assert option_count(app) == 0
            assert status(app).startswith("0 shortcuts")


class TestScopeToggle:
    async def test_it_opens_showing_every_binding(self) -> None:
        # Only the tasks tab is active, but help is where you look to find
        # out what else exists.
        app = HelpApp(active=frozenset({"tasks_tab_add", "tasks_tab_done"}))

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            assert status(app).startswith("3 shortcuts")

    async def test_the_toggle_narrows_to_the_active_bindings(self) -> None:
        app = HelpApp(active=frozenset({"tasks_tab_add", "tasks_tab_done"}))

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+t")
            await pilot.pause()

            assert status(app).startswith("2 shortcuts")
            assert option_count(app) == 3  # one heading, two shortcuts

    async def test_the_toggle_goes_back(self) -> None:
        app = HelpApp(active=frozenset({"tasks_tab_add"}))

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+t")
            await pilot.pause()
            await pilot.press("ctrl+t")
            await pilot.pause()

            assert status(app).startswith("3 shortcuts")

    async def test_the_status_line_names_the_other_scope(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()

            assert "only active" in status(app)

            await pilot.press("ctrl+t")
            await pilot.pause()

            assert "show all" in status(app)


class TestNavigation:
    async def test_the_arrows_move_the_highlight(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()

            assert app.screen.query_one(OptionList).highlighted is not None

    async def test_navigating_keeps_the_focus_in_the_search_field(
        self,
    ) -> None:
        # Losing it would mean the next character typed goes nowhere.
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("down", "down")
            await pilot.pause()

            assert isinstance(app.focused, Input)

    async def test_a_heading_is_never_highlighted(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            option_list = app.screen.query_one(OptionList)

            for _ in range(6):
                await pilot.press("down")
                await pilot.pause()
                index = option_list.highlighted

                assert index is not None
                assert not option_list.get_option_at_index(index).disabled


class TestClosing:
    async def test_escape_closes_the_overlay(self) -> None:
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            assert not app.query(HelpScreen)

    async def test_the_question_mark_closes_it_too(self) -> None:
        # The key that opens it should also shut it.
        app = HelpApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()

            assert not app.query(HelpScreen)


GLOBAL_APPEARANCE = BindingGroup(
    name="Appearance",
    scope="_global",
    scope_title="Global",
    bindings=(Binding("w", "theme", "Theme"),),
)
GLOBAL_APP = BindingGroup(
    name="App",
    scope="_global",
    scope_title="Global",
    bindings=(Binding("q", "quit", "Quit"),),
)


class NestedApp(App[None]):
    """An app whose overlay has a scope holding two groups."""

    def compose(self) -> ComposeResult:
        yield Static("body")

    def on_mount(self) -> None:
        self.push_screen(
            HelpScreen([TASKS, GLOBAL_APPEARANCE, GLOBAL_APP])
        )


def prompts(app: App[None]) -> list[str]:
    """Returns the rendered text of every row, in order."""
    options = app.screen.query_one(OptionList)

    return [
        str(options.get_option_at_index(index).prompt)
        for index in range(options.option_count)
    ]


class TestTwoLevels:
    async def test_a_scope_with_one_group_shows_no_group_heading(
        self,
    ) -> None:
        app = NestedApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            rendered = prompts(app)

            assert rendered[0] == "TASKS"
            assert rendered[1].startswith("  a")

    async def test_a_scope_with_two_groups_indents_them(self) -> None:
        app = NestedApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            rendered = prompts(app)
            appearance = rendered.index("  Appearance")

            assert rendered[appearance - 1] == "GLOBAL"
            assert rendered[appearance + 1].startswith("    w")

    async def test_the_entry_indent_follows_its_heading(self) -> None:
        # An entry under a group heading sits one level deeper than one
        # whose scope prints no group heading at all.
        app = NestedApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            rendered = prompts(app)
            shallow = next(r for r in rendered if r.strip().startswith("a "))
            deep = next(r for r in rendered if r.strip().startswith("w "))

            assert len(shallow) - len(shallow.lstrip()) == 2
            assert len(deep) - len(deep.lstrip()) == 4

    async def test_neither_heading_kind_can_be_highlighted(self) -> None:
        app = NestedApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            options = app.screen.query_one(OptionList)

            for _ in range(8):
                await pilot.press("down")
                await pilot.pause()
                index = options.highlighted

                assert index is not None
                assert not options.get_option_at_index(index).disabled


class TestTheGroupHeadingIsDimmed:
    """
    The inner heading shipped with `$text-muted` and rendered white.

    An `auto` colour does not resolve inside a Content style string, so the
    group heading was brighter than the entries it was meant to sit above.
    """

    async def test_a_group_heading_is_not_white(self) -> None:
        app = NestedApp()

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            options = app.screen.query_one(OptionList)
            segment = next(
                seg
                for row in options.render_lines(options.region.size.region)
                for seg in row
                if "Appearance" in seg.text
            )
            colour = segment.style.color if segment.style else None
            triplet = colour.triplet if colour is not None else None

            assert triplet is not None
            assert (triplet.red, triplet.green, triplet.blue) != (255, 255, 255)
