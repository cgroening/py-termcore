"""
AppHeader - a header carrying the application name and a wrapping tab bar.

Textual's own `Header` cannot do this: it is one line high (three with the
`-tall` class), its three slots - icon, centred title, clock - are fixed, and
its title is explicitly `text-wrap: nowrap; text-overflow: ellipsis`. Nor can
`Tabs`, which is `height: 2` with `overflow: hidden`, so tabs that do not fit
scroll rather than wrap.

This widget renders instead as one `Static`: a brand cell, then the tabs,
wrapping onto further rows whose brand cell is blank but exactly as wide.
`TabbedContent` keeps its panes - hide only its own bar with
`TabbedContent > ContentTabs { display: none; }` and drive `active` from here.

Usage:
    yield AppHeader(
        brand="Termplate",
        tabs=[HeaderTab("tasks_tab", "1", "Tasks")],
        active="tasks_tab",
    )
"""
from collections.abc import Sequence

from textual.content import Content
from textual.message import Message
from textual.reactive import reactive
from textual.style import Style
from textual.widgets import Static

from termcore.tui.custom_widgets.tab_rows import (
    SEPARATOR,
    HeaderRowPlan,
    HeaderTab,
    pack,
    tab_token,
)

__all__ = [
    "AppHeader",
    # Re-exported: an application building the bar needs the type, but the
    # packing helpers around it are ours, not its business.
    "HeaderTab",
]

# A dimmed foreground. Deliberately not `$text-muted`: that is defined as
# `auto 60%`, a colour blended against a background it never gets inside a
# Content style string, where it silently falls back to white. Only
# variables naming a real colour resolve here; in a stylesheet both do.
_DIMMED = "$foreground-darken-3"

_FALLBACK_WIDTH = 80


class AppHeader(Static):
    """
    The application header: a brand cell and a wrapping tab bar.

    Attributes
    ----------
    brand : str
        The application name, shown once in the first row.
    tabs : Sequence[HeaderTab]
        The tabs, in the order they should appear.
    active : str
        The id of the tab to highlight.
    """

    ALLOW_SELECT = False

    class TabSelected(Message):
        """
        Posted when a tab in the bar is clicked.

        Attributes
        ----------
        tab_id : str
            The id of the tab that was clicked.
        """

        def __init__(self, tab_id: str) -> None:
            """Records which tab was clicked."""
            super().__init__()
            self.tab_id = tab_id

    DEFAULT_CSS: str = """
    AppHeader {
        dock: top;
        width: 100%;
        height: auto;
        padding: 1 0;
        background: $panel;
        text-wrap: nowrap;

        /* A clickable span is a link to Textual, and it would otherwise be
           underlined and recoloured - which is exactly the dimming the tabs
           carry their meaning in. The hover keeps the affordance. */
        link-style: none;
        link-color: $foreground-darken-3;
        link-style-hover: bold;
        link-color-hover: $foreground;
        link-background-hover: transparent;
    }
    """

    active: reactive[str] = reactive("")

    def __init__(
        self,
        brand: str,
        tabs: Sequence[HeaderTab] = (),
        active: str = "",
    ) -> None:
        """Builds the header over the given tabs."""
        super().__init__()
        self._brand = brand
        self._tabs = tuple(tabs)
        self.set_reactive(AppHeader.active, active)

    def on_mount(self) -> None:
        """Draws the bar once the width is known."""
        self._redraw()

    def on_resize(self) -> None:
        """Re-wraps the tabs when the terminal width changes."""
        self._redraw()

    def watch_active(self, _active: str) -> None:
        """Re-draws so the highlight follows the active tab."""
        self._redraw()

    def set_tabs(self, tabs: Sequence[HeaderTab]) -> None:
        """
        Replaces the tabs and redraws.

        Parameters
        ----------
        tabs : Sequence[HeaderTab]
            The tabs, in the order they should appear.
        """
        self._tabs = tuple(tabs)
        self._redraw()

    def _redraw(self) -> None:
        """Packs the tabs for the current width and renders them."""
        width = self.size.width or _FALLBACK_WIDTH
        rows = pack(self._brand, self._tabs, width)
        self.update(Content("\n").join(self._row(row) for row in rows))

    def _row(self, row: HeaderRowPlan) -> Content:
        """Renders one row: the brand cell, then the separated tabs."""
        # Only the first row carries the name; the others hold spaces of the
        # same width, which is what puts every row's tabs in one column.
        content = (
            Content.styled(row.brand, "bold $primary")
            if row.brand.strip()
            else Content(row.brand)
        )

        for position, tab in enumerate(row.tabs):
            if position:
                content += Content.styled(SEPARATOR, _DIMMED)
            content += self._tab(tab)

        return content

    def _tab(self, tab: HeaderTab) -> Content:
        """Renders one tab, bold when active and clickable when not."""
        # Brightness and weight carry the distinction; there is no reverse
        # video and no background, so the bar stays quiet.
        if tab.id == self.active:
            # Deliberately not clickable. Textual restyles anything carrying
            # a click with its link colour, which would flatten the active
            # tab to the same grey as the rest - and a click on the tab one
            # is already on has nothing to do anyway.
            return Content.styled(tab_token(tab), "bold")

        # The click is carried in the span's metadata rather than measured
        # from the pointer's column, so Textual does the hit testing and the
        # wrapped rows need no arithmetic of their own.
        return Content.styled(tab_token(tab), _DIMMED).stylize(
            Style.from_meta({"@click": f"select_tab({tab.id!r})"})
        )

    def action_select_tab(self, tab_id: str) -> None:
        """
        Announces that a tab was clicked.

        The header does not switch anything itself - it does not own the
        content. It says which tab was asked for and leaves the decision to
        whoever mounted it.

        Parameters
        ----------
        tab_id : str
            The id of the clicked tab.
        """
        self.post_message(self.TabSelected(tab_id))
