"""
StatusBar - one line carrying standing information and a passing message.

Textual has no status widget: none of its widgets renders a permanent line of
application state. `App.notify` covers only the passing half, and only as a
box docked bottom right on its own layer that expires on a timer - it floats
above a status line rather than being one.

Place it last among the flowing widgets, above a docked footer. It does not
dock itself: Textual puts everything docked to one edge in the same place,
so a docked status bar would sit underneath the footer rather than above it.

The two halves are different things and are kept apart. `info` is state, sits
on the left and stays; `message` is an event, sits on the right and is meant
to be cleared by whoever set it - conventionally on the next key press:

    def on_key(self, _event: events.Key) -> None:
        self.query_one(StatusBar).message = ""

Nothing is truncated. Where the two would meet, the gap between them simply
closes and the line is clipped at the widget's width.
"""
from textual.content import Content
from textual.reactive import reactive
from textual.widgets import Static

from termcore.util.string import cell_width

__all__ = [
    "StatusBar",
]

# A dimmed foreground. Deliberately not `$text-muted`: that is defined as
# `auto 60%`, a colour blended against a background it never gets inside a
# Content style string, where it silently falls back to white. Only
# variables naming a real colour resolve here; in a stylesheet both do.
_DIMMED = "$foreground-darken-3"


class StatusBar(Static):
    """
    A single line of status: standing information and a passing message.

    Attributes
    ----------
    info : str
        Standing information, shown dimmed on the left.
    message : str
        A passing message, shown in the accent colour on the right. Empty
        leaves that side blank.
    """

    ALLOW_SELECT = False

    # Deliberately not docked. Textual places every widget docked to the
    # same edge in the same place, so a docked status bar and the docked
    # footer it belongs above would sit on top of one another. As a widget
    # in the normal flow it lands directly above the footer instead - give
    # the content above it `height: 1fr` so it is pushed to the bottom.
    DEFAULT_CSS: str = """
    StatusBar {
        width: 100%;
        height: 1;
        padding: 0 1;
        background: $panel;
        text-wrap: nowrap;
    }
    """

    info: reactive[str] = reactive("")
    message: reactive[str] = reactive("")

    def on_mount(self) -> None:
        """Draws the line once the width is known."""
        self._redraw()

    def on_resize(self) -> None:
        """Re-spaces the two halves when the width changes."""
        self._redraw()

    def watch_info(self, _info: str) -> None:
        """Re-draws when the standing information changes."""
        self._redraw()

    def watch_message(self, _message: str) -> None:
        """Re-draws when the passing message changes."""
        self._redraw()

    def _redraw(self) -> None:
        """Renders both halves with the gap that separates them."""
        content = Content.styled(self.info, _DIMMED)
        if self.message:
            content += Content(" " * self._gap())
            content += Content.styled(self.message, "$primary")

        self.update(content)

    def _gap(self) -> int:
        """Returns the filler between the two halves, never negative."""
        # Measured in cells, not characters: a CJK glyph is two cells wide,
        # and counting characters would push the right half off the line.
        width = self.content_size.width or self.size.width
        used = cell_width(self.info) + cell_width(self.message)

        return max(width - used, 1)
