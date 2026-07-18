"""
MultiLineFooter - a multi-line footer extending Textual's built-in Footer.

Two modes:

  1. auto_wrap=True   → Bindings automatically wrap when the row is full.
  2. auto_wrap=False  → Bindings are explicitly assigned to rows via `row_map`.

Usage:
    # Auto-wrap (default)
    yield MultiLineFooter()

    # Manual row assignment
    yield MultiLineFooter(
        auto_wrap=False,
        row_map={
            "quit": 0,
            "save": 0,
            "toggle_dark": 1,
            "help": 1,
        },
    )

The `row_map` maps binding actions to row numbers (0-based).
Unassigned bindings fall into the last defined row.
"""
from __future__ import annotations

from collections import defaultdict
from typing import cast, override

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup
from textual.reactive import reactive
from textual.widgets._footer import Footer, FooterKey

__all__ = [
    "FooterRow",
    "MultiLineFooter",
]


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


class MultiLineFooter(Footer):
    """
    Multi-line footer with auto-wrap or manual row assignment.

    Inherits from Textual's built-in Footer and overrides the layout to support
    multiple rows.

    Attributes
    ----------
    auto_wrap : bool, default True
        If True, bindings wrap automatically based on terminal width.
    row_map : dict[str, int] or None, optional
        Dict mapping action names to row numbers (0-based).
        Only relevant when ``auto_wrap=False``.
    max_rows : int, default 0
        Maximum number of rows for auto-wrap. 0 means unlimited.
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

    auto_wrap: reactive[bool] = reactive(default=True)
    max_rows: reactive[int] = reactive(0)
    _bindings_ready: bool

    def __init__(  # noqa: PLR0913 - mirrors Textual's Widget signature
        self,
        *,
        auto_wrap: bool = True,
        row_map: dict[str, int] | None = None,
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
        self._row_map: dict[str, int] = row_map or {}
        self.set_reactive(MultiLineFooter.auto_wrap, auto_wrap)
        self.set_reactive(MultiLineFooter.max_rows, max_rows)

    @staticmethod
    def _estimate_key_width(key_display: str, description: str) -> int:
        """Estimates the width of a FooterKey in columns (including padding)."""
        w = 1 + len(key_display) + 1   # key padding
        if description:
            w += len(description) + 1  # description + right padding
        return w

    def _collect_bindings(self) -> list[tuple[Binding, bool, str]]:
        """Collects active visible bindings, excluding the command palette."""
        active = self.screen.active_bindings
        app = cast("App[object]", self.app)
        palette_key = (
            app.COMMAND_PALETTE_BINDING
            if self.show_command_palette and app.ENABLE_COMMAND_PALETTE
            else None
        )
        return [
            (binding, enabled, tooltip)
            for key_str, (_node, binding, enabled, tooltip) in active.items()
            if binding.show and key_str != palette_key
        ]

    def _get_palette_binding(self) -> tuple[Binding, bool, str] | None:
        """Returns the command palette binding tuple or None."""
        app = cast("App[object]", self.app)
        if not (self.show_command_palette and app.ENABLE_COMMAND_PALETTE):
            return None
        try:
            _node, binding, enabled, tooltip = self.screen.active_bindings[
                app.COMMAND_PALETTE_BINDING
            ]
        except KeyError:
            return None
        return binding, enabled, tooltip

    def _build_rows_auto(
        self, bindings: list[tuple[Binding, bool, str]]
    ) -> list[list[tuple[Binding, bool, str]]]:
        """Distributes bindings across rows based on available width."""
        available = self.size.width or 80
        rows: list[list[tuple[Binding, bool, str]]] = [[]]
        current_width = 0

        app = cast("App[object]", self.app)
        for binding, enabled, tooltip in bindings:
            key_display = app.get_key_display(binding)
            w = self._estimate_key_width(key_display, binding.description) + 1
            if current_width + w > available and rows[-1]:
                if self.max_rows > 0 and len(rows) >= self.max_rows:
                    rows[-1].append((binding, enabled, tooltip))
                    current_width += w
                    continue
                rows.append([])
                current_width = 0
            rows[-1].append((binding, enabled, tooltip))
            current_width += w

        return rows

    def _build_rows_manual(
        self, bindings: list[tuple[Binding, bool, str]]
    ) -> list[list[tuple[Binding, bool, str]]]:
        """Distributes bindings across rows using the row_map."""
        grouped: defaultdict[int, list[tuple[Binding, bool, str]]] = \
            defaultdict(list)
        fallback_row = max(self._row_map.values(), default=0)

        for binding, enabled, tooltip in bindings:
            grouped[self._row_map.get(binding.action, fallback_row)].append(
                (binding, enabled, tooltip)
            )
        if not grouped:
            return []
        return [grouped[i] for i in sorted(grouped.keys())]

    @override
    def compose(self) -> ComposeResult:
        if not self._bindings_ready:
            return

        app = cast("App[object]", self.app)
        bindings = self._collect_bindings()
        rows = (
            self._build_rows_auto(bindings)
            if self.auto_wrap
            else self._build_rows_manual(bindings)
        )
        palette = self._get_palette_binding()

        for row_idx, row_bindings in enumerate(rows):
            with FooterRow():
                for binding, enabled, tooltip in row_bindings:
                    yield FooterKey(
                        binding.key,
                        app.get_key_display(binding),
                        binding.description,
                        binding.action,
                        disabled=not enabled,
                        tooltip=tooltip or binding.description,
                    ).data_bind(compact=Footer.compact)
                # Place the command palette in the first row
                # if row_idx == 0 and palette:
                # Place the command palette in the last row
                if row_idx == len(rows) - 1 and palette:
                    b, en, tt = palette
                    yield FooterKey(
                        b.key,
                        app.get_key_display(b),
                        b.description,
                        b.action,
                        disabled=not en,
                        tooltip=tt or b.description,
                        classes="-command-palette",
                    )

    @override
    def on_mount(self) -> None:
        super().on_mount()
        # Trigger initial render (needed when the footer is mounted late)
        self._bindings_ready = True
        _ = self.call_after_refresh(self.recompose)

    def on_resize(self) -> None:
        """Re-wraps on terminal resize (auto-wrap mode only)."""
        if self.auto_wrap and self._bindings_ready:
            _ = self.call_after_refresh(self.recompose)
