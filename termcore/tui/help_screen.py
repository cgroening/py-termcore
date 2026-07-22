"""
The help overlay: every shortcut, grouped, with a fuzzy search over them.

Section 1.8 of the style guide asks every terminal interface for a scrollable
overlay on `?` listing the shortcuts by group. This is that overlay, built on
the same `BindingGroup` objects the footer renders, so a shortcut cannot show
up in one and be missing from the other.

The list starts with every declared binding, because a help screen is where
someone looks to find out what the application can do. `ctrl+t` narrows it to
the bindings that would actually fire right now.

Search and scrolling are Textual's: `Matcher` is the fuzzy search its command
palette uses, and `OptionList` brings the cursor, the scrollbar and the rule
that a disabled option - here a group heading - is skipped over.
"""
from collections.abc import Sequence

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.content import Content
from textual.fuzzy import Matcher
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from termcore.tui.binding_groups import BindingGroup
from termcore.tui.help_rows import (
    HelpEntry,
    HelpHeader,
    HelpRequest,
    HelpRow,
    HelpScope,
    build_rows,
)

__all__ = [
    "HelpScreen",
]

_SCOPE_HINTS = {
    HelpScope.ALL: "ctrl+t only active  ·  esc close",
    HelpScope.ACTIVE: "ctrl+t show all  ·  esc close",
}


class HelpScreen(ModalScreen[None]):
    """
    A modal listing every shortcut, grouped and searchable.

    Attributes
    ----------
    groups : Sequence[BindingGroup]
        The groups to list, in the order they were declared.
    active : frozenset[str]
        The actions bound where the overlay was opened from. Snapshot these
        before pushing the screen - once it is on top, the active bindings
        are the overlay's own.
    """

    DEFAULT_CSS: str = """
    HelpScreen {
        align: center middle;
        background: $background 60%;
    }

    HelpScreen > Vertical {
        width: 80%;
        max-width: 80;
        height: 80%;
        border: round $primary;
        background: $surface;
        padding: 0 1;
    }

    HelpScreen Input {
        border: none;
        background: $surface;
        padding: 0;
    }

    HelpScreen OptionList {
        height: 1fr;
        border: none;
        background: $surface;
        scrollbar-size-vertical: 1;
    }

    /* Height is auto so a narrow terminal wraps the hints instead of
       cutting the last one off. */
    HelpScreen .help-status {
        height: auto;
        color: $text-muted;
    }
    """

    BINDINGS: list[BindingType] = [  # noqa: RUF012 - Textual class attribute
        Binding("escape,question_mark", "close", "Close", priority=True),
        Binding("ctrl+t", "toggle_scope", "All or active", priority=True),
        Binding("up", "cursor_up", "Up", show=False, priority=True),
        Binding("down", "cursor_down", "Down", show=False, priority=True),
        Binding("pageup", "page_up", "Page up", show=False, priority=True),
        Binding(
            "pagedown", "page_down", "Page down", show=False, priority=True
        ),
    ]

    def __init__(
        self,
        groups: Sequence[BindingGroup],
        active: frozenset[str] = frozenset(),
    ) -> None:
        """Builds the overlay over the given groups."""
        super().__init__()
        self._groups = tuple(groups)
        self._active = active
        self._scope = HelpScope.ALL

    def compose(self) -> ComposeResult:
        """Builds the search field, the list and the status line."""
        with Vertical():
            yield Input(placeholder="Search shortcuts", id="help_search")
            yield OptionList(id="help_list")
            yield Static("", classes="help-status")

    def on_mount(self) -> None:
        """Fills the list and leaves the focus in the search field."""
        self._populate()
        self.query_one(Input).focus()

    def on_input_changed(self, _event: Input.Changed) -> None:
        """Re-filters the list on every keystroke."""
        self._populate()

    def action_close(self) -> None:
        """Closes the overlay."""
        self.dismiss(None)

    def action_toggle_scope(self) -> None:
        """Switches between every binding and the currently active ones."""
        self._scope = (
            HelpScope.ACTIVE if self._scope is HelpScope.ALL
            else HelpScope.ALL
        )
        self._populate()

    def action_cursor_up(self) -> None:
        """Moves the highlight up without leaving the search field."""
        self.query_one(OptionList).action_cursor_up()

    def action_cursor_down(self) -> None:
        """Moves the highlight down without leaving the search field."""
        self.query_one(OptionList).action_cursor_down()

    def action_page_up(self) -> None:
        """Scrolls the list up by one page."""
        self.query_one(OptionList).action_page_up()

    def action_page_down(self) -> None:
        """Scrolls the list down by one page."""
        self.query_one(OptionList).action_page_down()

    def _populate(self) -> None:
        """Rebuilds the list from the current query and scope."""
        query = self.query_one(Input).value
        rows = build_rows(
            self._groups,
            HelpRequest(query=query, scope=self._scope, active=self._active),
        )
        matcher = Matcher(query) if query else None

        option_list = self.query_one(OptionList)
        option_list.clear_options()
        option_list.add_options(
            [self._option(row, matcher) for row in rows.rows]
        )

        self.query_one(Static).update(
            f"{rows.matches} shortcuts  ·  {_SCOPE_HINTS[self._scope]}"
        )

    @staticmethod
    def _option(row: HelpRow, matcher: Matcher | None) -> Option:
        """Turns one row into an option, headers being unselectable."""
        if isinstance(row, HelpHeader):
            return Option(
                Content.styled(row.label.upper(), "bold $primary"),
                disabled=True,
            )

        entry: HelpEntry = row
        if matcher is None:
            return Option(Content(entry.text))

        return Option(matcher.highlight(entry.text))
