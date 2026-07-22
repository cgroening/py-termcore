"""
Row building for the help overlay.

The overlay renders the same `BindingGroup` objects as the footer, so a
shortcut cannot appear in one and be missing from the other. This module
holds the filtering and the row order and none of the widgets, which is what
lets the rules below be tested without starting an application.

Matching runs through Textual's own `Matcher`, the same fuzzy search its
command palette uses. Entries keep the order the file declares them in; a
score decides whether an entry survives, never where it lands.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto

from textual.binding import Binding
from textual.fuzzy import Matcher

from termcore.tui.binding_groups import BindingGroup, dispatch_name
from termcore.util.string import str_with_fixed_width

# Wide enough for the chords a terminal app realistically binds, so that the
# descriptions line up into a column of their own.
KEY_COLUMN = 12

__all__ = [
    "KEY_COLUMN",
    "HelpEntry",
    "HelpHeader",
    "HelpRequest",
    "HelpRow",
    "HelpRows",
    "HelpScope",
    "build_rows",
    "key_display",
]


class HelpScope(Enum):
    """Which bindings the overlay lists."""

    ALL = auto()
    ACTIVE = auto()


@dataclass(frozen=True, slots=True)
class HelpHeader:
    """
    The title of one group.

    Attributes
    ----------
    label : str
        The group's name, or the scope it came from when it has none.
    """

    label: str


@dataclass(frozen=True, slots=True)
class HelpEntry:
    """
    One shortcut.

    Attributes
    ----------
    text : str
        The whole rendered line, key column and description. This is also
        the text the search matches, so that a caller highlighting the hit
        positions can apply them to it directly.
    key : str
        The key as it is rendered, without the column padding.
    description : str
        What the shortcut does.
    action : str
        The bare action name, for callers that need to identify the row.
    """

    text: str
    key: str
    description: str
    action: str


HelpRow = HelpHeader | HelpEntry


@dataclass(frozen=True, slots=True)
class HelpRequest:
    """
    What the overlay is asking for.

    Attributes
    ----------
    query : str
        The search text; empty keeps everything.
    scope : HelpScope
        Whether to list every declared binding or only the active ones.
    active : frozenset[str]
        The actions that are bound right now, without the `app.` prefix.
        Only consulted for `HelpScope.ACTIVE`.
    """

    query: str = ""
    scope: HelpScope = HelpScope.ALL
    active: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class HelpRows:
    """
    The rows to render.

    Attributes
    ----------
    rows : tuple[HelpRow, ...]
        Headers and entries, interleaved in group order.
    matches : int
        How many entries survived, headers excluded. A caller showing a
        count wants this rather than `len(rows)`.
    """

    rows: tuple[HelpRow, ...]
    matches: int


def key_display(binding: Binding) -> str:
    """
    Returns the key of a binding as it should be shown.

    Parameters
    ----------
    binding : Binding
        The binding to render the key of.

    Returns
    -------
    str
        The declared display name, falling back to the key itself.

    Examples
    --------
    >>> key_display(Binding("f1", "help", "Help", key_display="F1"))
    'F1'
    """
    return binding.key_display or binding.key


def build_rows(
    groups: Sequence[BindingGroup], request: HelpRequest
) -> HelpRows:
    """
    Turns groups into the rows the overlay lists.

    A group contributes a header only when at least one of its entries
    survives the filter, so a search never leaves an empty section behind.
    Groups declared without a name are titled after their scope, because a
    list, unlike the footer, cannot simply leave the space blank.

    Parameters
    ----------
    groups : Sequence[BindingGroup]
        Every declared group, in file order.
    request : HelpRequest
        The search text, the scope and the currently active actions.

    Returns
    -------
    HelpRows
        The rows to render and the number of matching entries.
    """
    matcher = Matcher(request.query) if request.query else None

    rows: list[HelpRow] = []
    matches = 0
    for group in groups:
        entries = _entries(group, request, matcher)
        if not entries:
            continue

        rows.append(HelpHeader(group.name or group.scope))
        rows.extend(entries)
        matches += len(entries)

    return HelpRows(rows=tuple(rows), matches=matches)


def _entries(
    group: BindingGroup, request: HelpRequest, matcher: Matcher | None
) -> list[HelpEntry]:
    """Returns the entries of one group that survive the filter."""
    entries: list[HelpEntry] = []
    for binding in group.bindings:
        action = dispatch_name(binding.action)
        if request.scope is HelpScope.ACTIVE and action not in request.active:
            continue

        key = key_display(binding)
        text = f"{str_with_fixed_width(key, KEY_COLUMN)} " \
               f"{binding.description}"
        if matcher is not None and not matcher.match(text):
            continue

        entries.append(
            HelpEntry(
                text=text,
                key=key,
                description=binding.description,
                action=action,
            )
        )

    return entries
