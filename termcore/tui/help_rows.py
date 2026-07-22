"""
Row building for the help overlay.

The overlay renders the same `BindingGroup` objects as the footer, so a
shortcut cannot appear in one and be missing from the other. This module
holds the filtering and the row order and none of the widgets, which is what
lets the rules below be tested without starting an application.

Where the footer lays the groups out in one dimension, the overlay uses two.
Its outer heading is the scope - the tab or screen a shortcut works on, which
is what someone opening a help screen is actually asking about. The group is
the inner heading, and it is left out where a scope holds only one of them,
since repeating "Tasks" under "Tasks" tells nobody anything.

Matching runs through Textual's own `Matcher`, the same fuzzy search its
command palette uses. Entries keep the order the file declares them in; a
score decides whether an entry survives, never where it lands.
"""
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum, auto
from itertools import groupby

from textual.binding import Binding
from textual.fuzzy import Matcher

from termcore.tui.binding_groups import (
    BindingGroup,
    dispatch_name,
    display_scope,
)
from termcore.util.string import str_with_fixed_width

# Wide enough for the chords a terminal app realistically binds, so that the
# descriptions line up into a column of their own.
KEY_COLUMN = 12

# The nesting a row sits at. Entries sit one below the heading above them,
# so they land on GROUP_LEVEL or one deeper.
SCOPE_LEVEL = 0
GROUP_LEVEL = 1

__all__ = [
    "GROUP_LEVEL",
    "KEY_COLUMN",
    "SCOPE_LEVEL",
    "HelpCoverage",
    "HelpEntry",
    "HelpHeader",
    "HelpRequest",
    "HelpRow",
    "HelpRows",
    "build_rows",
    "key_display",
]


class HelpCoverage(Enum):
    """Which bindings the overlay lists."""

    ALL = auto()
    ACTIVE = auto()


@dataclass(frozen=True, slots=True)
class HelpHeader:
    """
    The title of a scope or of a group inside one.

    Attributes
    ----------
    label : str
        The scope's display name, or the group's name.
    level : int
        `SCOPE_LEVEL` for a scope, `GROUP_LEVEL` for a group within one.
    """

    label: str
    level: int = SCOPE_LEVEL


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
    level : int
        How deep the entry sits: one below the heading above it, so one
        deeper where its scope also prints group headings.
    """

    text: str
    key: str
    description: str
    action: str
    level: int = GROUP_LEVEL


HelpRow = HelpHeader | HelpEntry


@dataclass(frozen=True, slots=True)
class HelpRequest:
    """
    What the overlay is asking for.

    Attributes
    ----------
    query : str
        The search text; empty keeps everything.
    scope : HelpCoverage
        Whether to list every declared binding or only the active ones.
    active : frozenset[str]
        The actions that are bound right now, without the `app.` prefix.
        Only consulted for `HelpCoverage.ACTIVE`.
    """

    query: str = ""
    coverage: HelpCoverage = HelpCoverage.ALL
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

    Groups are gathered under the scope they came from, and a scope appears
    only when at least one of its entries survives the filter, so a search
    never leaves an empty section behind. A scope left with a single group
    prints no group heading: the second level is there to tell groups apart,
    and there is nothing to tell apart.

    Parameters
    ----------
    groups : Sequence[BindingGroup]
        Every declared group, in file order.
    request : HelpRequest
        The search text, the coverage and the currently active actions.

    Returns
    -------
    HelpRows
        The rows to render and the number of matching entries.
    """
    matcher = Matcher(request.query) if request.query else None

    rows: list[HelpRow] = []
    matches = 0
    for scope_groups in _by_scope(groups):
        surviving = [
            (group, entries)
            for group in scope_groups
            if (entries := _entries(group, request, matcher))
        ]
        if not surviving:
            continue

        rows.append(HelpHeader(display_scope(surviving[0][0]), SCOPE_LEVEL))
        rows.extend(_scope_rows(surviving))
        matches += sum(len(entries) for _group, entries in surviving)

    return HelpRows(rows=tuple(rows), matches=matches)


def _by_scope(
    groups: Sequence[BindingGroup],
) -> list[list[BindingGroup]]:
    """Gathers neighbouring groups that came from the same scope."""
    return [
        list(scope_groups)
        for _scope, scope_groups in groupby(groups, key=lambda g: g.scope)
    ]


def _scope_rows(
    surviving: Sequence[tuple[BindingGroup, list[HelpEntry]]],
) -> list[HelpRow]:
    """Returns one scope's rows, with group headings only where they help."""
    # A single group under a scope would repeat what the scope already says,
    # so its heading is dropped and its entries move up one level.
    named = len(surviving) > 1

    rows: list[HelpRow] = []
    for group, entries in surviving:
        heading = named and bool(group.name)
        if heading:
            rows.append(HelpHeader(group.name, GROUP_LEVEL))

        level = GROUP_LEVEL + 1 if heading else GROUP_LEVEL
        rows.extend(replace(entry, level=level) for entry in entries)

    return rows


def _entries(
    group: BindingGroup, request: HelpRequest, matcher: Matcher | None
) -> list[HelpEntry]:
    """Returns the entries of one group that survive the filter."""
    entries: list[HelpEntry] = []
    for binding in group.bindings:
        action = dispatch_name(binding.action)
        hidden = (
            request.coverage is HelpCoverage.ACTIVE
            and action not in request.active
        )
        if hidden:
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
