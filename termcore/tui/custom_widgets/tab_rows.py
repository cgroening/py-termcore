"""
Row layout for the application header's tab bar.

This module holds the arithmetic and none of the widgets, so the packing can
be tested without running an application. `AppHeader` turns the row plans it
returns into rendered text and decides nothing about width itself.

The bar starts with a brand cell and then lists the tabs. When they do not
fit, they wrap onto further rows whose brand cell is blank but exactly as
wide, so the tabs line up in a column of their own.
"""
from collections.abc import Sequence
from dataclasses import dataclass

from termcore.util.string import cell_width

__all__ = [
    "BRAND_PADDING",
    "SEPARATOR",
    "HeaderRowPlan",
    "HeaderTab",
    "brand_cell",
    "pack",
    "tab_token",
]

# One space before the brand and three after it, as clibase renders it. The
# tabs of every row start at that width, continuation rows included.
BRAND_PADDING = (1, 3)
SEPARATOR = " │ "


@dataclass(frozen=True, slots=True)
class HeaderTab:
    """
    One tab of the bar.

    Attributes
    ----------
    id : str
        The scope the tab belongs to, used to tell which one is active.
    key : str
        The key that selects it, without brackets - the bar adds those.
    label : str
        The name shown after the key.
    """

    id: str
    key: str
    label: str


@dataclass(frozen=True, slots=True)
class HeaderRowPlan:
    """
    One rendered row of the bar.

    Attributes
    ----------
    brand : str
        The brand cell, padded to the column width. Blank on continuation
        rows, so the tabs stay in one column without repeating the name.
    tabs : tuple[HeaderTab, ...]
        The tabs of this row, in order.
    """

    brand: str
    tabs: tuple[HeaderTab, ...]


def brand_cell(brand: str) -> str:
    """
    Returns the brand text padded to the width every row reserves.

    Parameters
    ----------
    brand : str
        The application name.

    Returns
    -------
    str
        The padded cell.

    Examples
    --------
    >>> brand_cell("app")
    ' app   '
    """
    before, after = BRAND_PADDING

    return f"{' ' * before}{brand}{' ' * after}"


def tab_token(tab: HeaderTab) -> str:
    """
    Returns one tab as it is rendered.

    Parameters
    ----------
    tab : HeaderTab
        The tab to render.

    Returns
    -------
    str
        The bracketed key followed by the label.

    Examples
    --------
    >>> tab_token(HeaderTab("tasks_tab", "1", "Tasks"))
    '[1] Tasks'
    """
    return f"[{tab.key}] {tab.label}"


def pack(
    brand: str, tabs: Sequence[HeaderTab], width: int
) -> list[HeaderRowPlan]:
    """
    Distributes the tabs across rows that fit the given width.

    The first tab of a row is always placed, even where it alone overflows:
    a tab is never split and never dropped, so a narrow terminal loses
    nothing but alignment. Every row is charged for the brand column, the
    blank ones included, which is what keeps the tabs in a column.

    Parameters
    ----------
    brand : str
        The application name shown in the first row's brand cell.
    tabs : Sequence[HeaderTab]
        The tabs, in the order they should appear.
    width : int
        The width available to the bar, in terminal cells.

    Returns
    -------
    list[HeaderRowPlan]
        The rows to render, top to bottom. Always at least one, so the brand
        shows even before any tab exists.
    """
    cell = brand_cell(brand)
    column = cell_width(cell)
    separator = cell_width(SEPARATOR)

    rows: list[list[HeaderTab]] = [[]]
    used = column
    for tab in tabs:
        token = cell_width(tab_token(tab))
        if rows[-1] and used + separator + token > width:
            rows.append([])
            used = column

        if rows[-1]:
            used += separator
        rows[-1].append(tab)
        used += token

    return [
        HeaderRowPlan(
            brand=cell if index == 0 else " " * column,
            tabs=tuple(row),
        )
        for index, row in enumerate(rows)
    ]
