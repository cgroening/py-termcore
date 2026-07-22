"""
MultiLineFooter - a multi-line footer extending Textual's built-in Footer.

Two modes, chosen by whether groups are passed:

  1. MultiLineFooter()                → keys wrap on width alone.
  2. MultiLineFooter(groups=[...])    → one row per group, labels aligned
                                        in a column on the left.

Usage:
    # Wrap on width
    yield MultiLineFooter()

    # One row per declared group
    yield MultiLineFooter(groups=CUSTOM_BINDINGS.get_groups())

Groups come from `CustomBindings.get_groups()`, so the order of the rows is
the order of the YAML file. A group whose bindings are not active right now
renders no row, which is what lets one call cover every screen.

The arithmetic lives in `footer_rows`; this module only turns row plans into
widgets.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import cast, override

from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup
from textual.reactive import reactive
from textual.widgets import Static
from textual.widgets._footer import Footer, FooterKey

from termcore.tui.binding_groups import BindingGroup
from termcore.tui.custom_widgets.footer_rows import (
    SEPARATOR,
    FooterHint,
    FooterLayout,
    FooterRowPlan,
    hint_width,
)
from termcore.util.string import cell_width

__all__ = [
    "FooterGroupLabel",
    "FooterRow",
    "FooterSeparator",
    "MultiLineFooter",
]

_FALLBACK_WIDTH = 80


class FooterRow(HorizontalGroup):
    """Horizontal row containing FooterKey widgets."""

    DEFAULT_CSS: str = """
    FooterRow {
        width: 1fr;
        height: 1;
        layout: horizontal;
        background: $footer-background;
    }
    """


class FooterGroupLabel(Static):
    """
    The label in front of a group's row.

    The text arrives already padded to the shared column width, and the
    widget is sized from it, so every row's keys start in the same column
    without a second layout pass.
    """

    ALLOW_SELECT = False

    DEFAULT_CSS: str = """
    FooterGroupLabel {
        height: 1;
        text-wrap: nowrap;
        color: $footer-description-foreground;
        background: $footer-background;
    }
    """

    def __init__(self, label: str) -> None:
        """Builds a label cell of exactly the width of the given text."""
        super().__init__(label)
        self.styles.width = cell_width(label)


class FooterSeparator(Static):
    """
    The mark between two keys of the same group.

    `FooterKey` already pads itself on both sides, so this carries the bare
    separator and lets those paddings supply the surrounding spaces.
    """

    ALLOW_SELECT = False

    DEFAULT_CSS: str = """
    FooterSeparator {
        height: 1;
        text-wrap: nowrap;
        color: $footer-description-foreground;
        background: $footer-background;
    }
    """

    def __init__(self) -> None:
        """Builds a separator cell."""
        super().__init__(SEPARATOR)
        self.styles.width = cell_width(SEPARATOR)


class MultiLineFooter(Footer):
    """
    Multi-line footer with grouped rows or width-based wrapping.

    Inherits from Textual's built-in Footer and overrides the layout to
    support multiple rows.

    Attributes
    ----------
    groups : Sequence[BindingGroup] or None, optional
        The declared groups. Given, each one becomes a row labelled on the
        left; omitted, the keys wrap on width alone.
    max_rows : int, default 0
        The most rows one group may occupy. 0 means unlimited.
    show_command_palette : bool, default True
        Show the command palette binding.
    compact : bool, default False
        Use compact styling with less whitespace.
    """

    DEFAULT_CSS: str = """
    MultiLineFooter {
        height: auto;
        layout: vertical;
        scrollbar-size: 0 0;
    }
    """

    max_rows: reactive[int] = reactive(0)
    _bindings_ready: bool

    def __init__(  # noqa: PLR0913 - mirrors Textual's Widget signature
        self,
        *,
        groups: Sequence[BindingGroup] | None = None,
        max_rows: int = 0,
        show_command_palette: bool = True,
        compact: bool = False,
        name: str | None = None,
        id: str | None = None,  # noqa: A002 - Textual's parameter name
        classes: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            show_command_palette=show_command_palette,
            compact=compact,
        )
        self._groups: tuple[BindingGroup, ...] = tuple(groups or ())
        self.set_reactive(MultiLineFooter.max_rows, max_rows)

    def _collect_hints(self) -> list[FooterHint]:
        """Collects active visible bindings, excluding the command palette."""
        active = self.screen.active_bindings
        app = cast("App[object]", self.app)
        palette_key = (
            app.COMMAND_PALETTE_BINDING
            if self.show_command_palette and app.ENABLE_COMMAND_PALETTE
            else None
        )

        return [
            FooterHint(binding, enabled, tooltip)
            for key_str, (_node, binding, enabled, tooltip) in active.items()
            if binding.show and key_str != palette_key
        ]

    def _get_palette_hint(self) -> FooterHint | None:
        """Returns the command palette hint, or None when it is hidden."""
        app = cast("App[object]", self.app)
        if not (self.show_command_palette and app.ENABLE_COMMAND_PALETTE):
            return None

        try:
            _node, binding, enabled, tooltip = self.screen.active_bindings[
                app.COMMAND_PALETTE_BINDING
            ]
        except KeyError:
            return None

        return FooterHint(binding, enabled, tooltip)

    def _available_width(self, palette: FooterHint | None) -> int:
        """
        Returns the width the rows may use.

        The command palette key is docked to the right of the last row, so
        its width is taken off the budget. Reserving it for every row costs
        a little space above, and is the price of never overlapping it.
        """
        width = self.size.width or _FALLBACK_WIDTH
        if palette is None:
            return width

        app = cast("App[object]", self.app)
        reserved = hint_width(
            app.get_key_display(palette.binding), palette.binding.description
        )

        return max(width - reserved, 1)

    def _build_rows(self, palette: FooterHint | None) -> list[FooterRowPlan]:
        """Returns the row plans for the current bindings and width."""
        app = cast("App[object]", self.app)
        layout = FooterLayout(
            key_display=app.get_key_display,
            width=self._available_width(palette),
            max_rows=self.max_rows,
        )
        hints = self._collect_hints()

        if self._groups:
            return layout.group_rows(self._groups, hints)

        return layout.flat_rows(hints)

    def _footer_key(self, hint: FooterHint, classes: str = "") -> FooterKey:
        """Builds the widget for one key."""
        app = cast("App[object]", self.app)

        return FooterKey(
            hint.binding.key,
            app.get_key_display(hint.binding),
            hint.binding.description,
            hint.binding.action,
            disabled=not hint.enabled,
            tooltip=hint.tooltip or hint.binding.description,
            classes=classes,
        )

    @override
    def compose(self) -> ComposeResult:
        if not self._bindings_ready:
            return

        palette = self._get_palette_hint()
        rows = self._build_rows(palette)

        for row_index, row in enumerate(rows):
            with FooterRow():
                if row.label:
                    yield FooterGroupLabel(row.label)

                for hint_index, hint in enumerate(row.hints):
                    if hint_index:
                        yield FooterSeparator()
                    yield self._footer_key(hint).data_bind(
                        compact=Footer.compact
                    )

                if palette is not None and row_index == len(rows) - 1:
                    yield self._footer_key(palette, "-command-palette")

    @override
    def on_mount(self) -> None:
        super().on_mount()
        # Trigger initial render (needed when the footer is mounted late)
        self._bindings_ready = True
        _ = self.call_after_refresh(self.recompose)

    def on_resize(self) -> None:
        """Re-wraps on terminal resize; both modes depend on the width."""
        if self._bindings_ready:
            _ = self.call_after_refresh(self.recompose)
