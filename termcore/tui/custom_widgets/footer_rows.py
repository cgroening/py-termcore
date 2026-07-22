"""
Row layout for the multi-line footer.

This module holds the arithmetic and none of the widgets, so the layout can
be tested without running an application. `MultiLineFooter` turns the plans
it returns into widgets and does not decide anything about width itself.

A group becomes one row. When its hints do not fit the available width they
wrap onto continuation rows, which carry a blank label cell so that the hints
line up under the hints above them rather than under the label.
"""
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from textual.binding import Binding

from termcore.tui.binding_groups import BindingGroup, dispatch_name
from termcore.util.string import cell_width, str_with_fixed_width

__all__ = [
    "LABEL_GAP",
    "LABEL_SUFFIX",
    "SEPARATOR",
    "FooterHint",
    "FooterLayout",
    "FooterRowPlan",
    "hint_width",
    "label_column_width",
]

# `FooterKey` already carries one cell of padding on its left, so a single
# gap here renders as the two cells the design asks for.
LABEL_GAP = 1
LABEL_SUFFIX = ":"
SEPARATOR = "·"


@dataclass(frozen=True, slots=True)
class FooterHint:
    """
    One key as the footer needs it.

    Attributes
    ----------
    binding : Binding
        The binding this hint renders.
    enabled : bool
        False when the action cannot run right now.
    tooltip : str
        Tooltip text, falling back to the description when empty.
    """

    binding: Binding
    enabled: bool
    tooltip: str


@dataclass(frozen=True, slots=True)
class FooterRowPlan:
    """
    One rendered row.

    Attributes
    ----------
    label : str
        The label cell, already padded to the column width. Empty when no
        group in the footer carries a label.
    hints : tuple[FooterHint, ...]
        The keys of this row, in order.
    """

    label: str
    hints: tuple[FooterHint, ...]


def hint_width(key_display: str, description: str) -> int:
    """
    Returns the cells one key occupies, its padding included.

    Mirrors what `FooterKey` renders: one cell of padding either side of the
    key, and one after the description. A row that miscounts this overflows
    by exactly one cell per key, which is why the renderer and this function
    are guarded by a shared test.

    Parameters
    ----------
    key_display : str
        The key as it is rendered, not as it is declared.
    description : str
        The label after the key; may be empty.

    Returns
    -------
    int
        The number of terminal cells the key occupies.
    """
    width = 1 + cell_width(key_display) + 1
    if description:
        width += cell_width(description) + 1

    return width


def label_column_width(groups: Sequence[BindingGroup]) -> int:
    """
    Returns the width of the label column, or 0 when no group is named.

    Every label shares one column so that the hints of all rows start in the
    same place. A footer whose groups are all unnamed reserves nothing, and
    the keys start at the left edge as they did before grouping existed.

    Parameters
    ----------
    groups : Sequence[BindingGroup]
        The groups that will actually render a row.

    Returns
    -------
    int
        The column width in terminal cells.
    """
    widest = max(
        (
            cell_width(group.name + LABEL_SUFFIX)
            for group in groups if group.name
        ),
        default=0,
    )

    return widest + LABEL_GAP if widest else 0


@dataclass(frozen=True, slots=True)
class FooterLayout:
    """
    Turns groups and active keys into row plans.

    Attributes
    ----------
    key_display : Callable[[Binding], str]
        Renders a binding's key the way the app displays it.
    width : int
        The width available to the whole footer, in cells.
    max_rows : int
        The most rows one group may occupy; 0 means unlimited. Hints beyond
        the limit pile into that group's last row.
    """

    key_display: Callable[[Binding], str]
    width: int
    max_rows: int = field(default=0)

    def group_rows(
        self,
        groups: Sequence[BindingGroup],
        hints: Sequence[FooterHint],
    ) -> list[FooterRowPlan]:
        """
        Returns one row per group, in the order the groups were declared.

        Only bindings that are currently active produce a hint, so a group
        belonging to an inactive tab yields no row at all rather than an
        empty one. The label column is measured over the surviving groups,
        so a hidden long label does not widen the gutter.

        Parameters
        ----------
        groups : Sequence[BindingGroup]
            Every declared group, in file order.
        hints : Sequence[FooterHint]
            The keys that are active right now.

        Returns
        -------
        list[FooterRowPlan]
            The rows to render, top to bottom.
        """
        matched = [
            (group, group_hints)
            for group, group_hints in self._match(groups, hints)
            if group_hints
        ]
        label_column = label_column_width([group for group, _ in matched])

        rows: list[FooterRowPlan] = []
        for group, group_hints in matched:
            rows.extend(self._wrap(group.name, group_hints, label_column))

        return rows

    def flat_rows(self, hints: Sequence[FooterHint]) -> list[FooterRowPlan]:
        """
        Returns rows that wrap on width alone, without any labels.

        This is the shape a footer takes when no groups are declared.

        Parameters
        ----------
        hints : Sequence[FooterHint]
            The keys that are active right now, in order.

        Returns
        -------
        list[FooterRowPlan]
            The rows to render, top to bottom.
        """
        return self._wrap("", hints, label_column=0)

    def _match(
        self,
        groups: Sequence[BindingGroup],
        hints: Sequence[FooterHint],
    ) -> list[tuple[BindingGroup, list[FooterHint]]]:
        """
        Pairs each group with the active hints of its bindings.

        Matching runs by action rather than by key, because a screen renames
        a global action to `app.<action>` on its way in. Each hint is handed
        out once, so an action declared twice renders in the first group
        that claims it instead of in both.
        """
        available: defaultdict[str, list[FooterHint]] = defaultdict(list)
        for hint in hints:
            available[dispatch_name(hint.binding.action)].append(hint)

        matched: list[tuple[BindingGroup, list[FooterHint]]] = []
        for group in groups:
            group_hints: list[FooterHint] = []
            for binding in group.bindings:
                pending = available[dispatch_name(binding.action)]
                if pending:
                    group_hints.append(pending.pop(0))

            matched.append((group, group_hints))

        return matched

    def _wrap(
        self, name: str, hints: Sequence[FooterHint], label_column: int
    ) -> list[FooterRowPlan]:
        """Breaks one group's hints into rows that fit the width."""
        budget = max(self.width - label_column, 1)
        separator = cell_width(SEPARATOR)

        rows: list[list[FooterHint]] = [[]]
        used = 0
        for hint in hints:
            width = self._hint_width(hint)
            extra = width + separator if rows[-1] else width
            if rows[-1] and used + extra > budget and not self._is_full(rows):
                rows.append([])
                used = 0
                extra = width

            rows[-1].append(hint)
            used += extra

        return self._plans(name, rows, label_column)

    def _is_full(self, rows: Sequence[Sequence[FooterHint]]) -> bool:
        """Returns True once a group may not start another row."""
        return self.max_rows > 0 and len(rows) >= self.max_rows

    def _hint_width(self, hint: FooterHint) -> int:
        """Returns the cells one hint occupies once rendered."""
        return hint_width(
            self.key_display(hint.binding), hint.binding.description
        )

    @staticmethod
    def _plans(
        name: str, rows: Sequence[Sequence[FooterHint]], label_column: int
    ) -> list[FooterRowPlan]:
        """Labels the first row of a group and blanks the continuations."""
        label = (
            str_with_fixed_width(name + LABEL_SUFFIX, label_column)
            if name and label_column
            else " " * label_column
        )

        return [
            FooterRowPlan(
                label=label if index == 0 else " " * label_column,
                hints=tuple(row),
            )
            for index, row in enumerate(rows) if row
        ]
