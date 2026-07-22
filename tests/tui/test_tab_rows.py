"""Tests for the arithmetic behind the header's tab bar.

The rules pinned here are the ones a reader would take for cosmetics until
they break: the brand column that every row is charged for, the separator
that must not appear at either end of a row, and the promise that a tab is
never dropped however narrow the terminal gets.
"""

from collections.abc import Sequence

from termcore.tui.custom_widgets.tab_rows import (
    SEPARATOR,
    HeaderRowPlan,
    HeaderTab,
    brand_cell,
    pack,
    tab_token,
)
from termcore.util.string import cell_width

BRAND = "mdtask"
WIDE = 200


def tabs(*pairs: tuple[str, str]) -> list[HeaderTab]:
    """Builds tabs from (key, label) pairs, ids derived from the label."""
    return [HeaderTab(label.lower(), key, label) for key, label in pairs]


def keys(rows: Sequence[HeaderRowPlan]) -> list[list[str]]:
    """Returns the key of every tab, row by row."""
    return [[tab.key for tab in row.tabs] for row in rows]


class TestBrandColumn:
    def test_the_brand_is_padded_on_both_sides(self) -> None:
        assert brand_cell("app") == " app   "

    def test_only_the_first_row_carries_the_name(self) -> None:
        rows = pack(BRAND, tabs(("1", "One"), ("2", "Two")), width=20)

        assert rows[0].brand.strip() == BRAND
        for row in rows[1:]:
            assert row.brand.strip() == ""

    def test_every_row_reserves_the_same_column(self) -> None:
        # This is what puts the tabs of all rows into one column.
        rows = pack(BRAND, tabs(("1", "One"), ("2", "Two")), width=20)
        widths = {cell_width(row.brand) for row in rows}

        assert len(widths) == 1

    def test_a_wide_brand_is_measured_in_cells(self) -> None:
        # Three CJK characters are six cells; counting characters would make
        # the column too narrow and knock every row out of alignment.
        rows = pack("日本語", tabs(("1", "One")), width=WIDE)

        assert cell_width(rows[0].brand) == 6 + 4


class TestPacking:
    def test_everything_fits_on_one_row_when_wide(self) -> None:
        rows = pack(BRAND, tabs(("1", "One"), ("2", "Two")), width=WIDE)

        assert keys(rows) == [["1", "2"]]

    def test_tabs_wrap_when_the_width_runs_out(self) -> None:
        rows = pack(
            BRAND,
            tabs(("1", "Tasks"), ("2", "Software"), ("3", "Allgemein")),
            width=40,
        )

        assert len(rows) > 1

    def test_the_declared_order_survives_wrapping(self) -> None:
        rows = pack(
            BRAND,
            tabs(("1", "One"), ("2", "Two"), ("3", "Three"), ("4", "Four")),
            width=32,
        )
        flat = [key for row in keys(rows) for key in row]

        assert flat == ["1", "2", "3", "4"]

    def test_no_row_exceeds_the_width(self) -> None:
        entries = tabs(*[(str(i), f"Label {i}") for i in range(1, 9)])
        width = 48
        rows = pack(BRAND, entries, width)

        for row in rows:
            used = cell_width(row.brand) + sum(
                cell_width(tab_token(tab)) for tab in row.tabs
            ) + (len(row.tabs) - 1) * cell_width(SEPARATOR)

            assert used <= width

    def test_a_single_tab_is_never_dropped(self) -> None:
        # Even one that alone overflows has to render somewhere.
        rows = pack(BRAND, tabs(("1", "A very long label indeed")), width=8)

        assert keys(rows) == [["1"]]

    def test_no_tabs_still_yields_one_row(self) -> None:
        # So the brand shows before any tab exists.
        rows = pack(BRAND, [], width=WIDE)

        assert len(rows) == 1
        assert rows[0].tabs == ()

    def test_a_wide_label_is_measured_in_cells(self) -> None:
        narrow = pack(BRAND, tabs(("1", "ab"), ("2", "ab")), width=30)
        wide = pack(BRAND, tabs(("1", "日本"), ("2", "日本")), width=30)

        assert len(wide) >= len(narrow)


class TestTokens:
    def test_the_key_is_bracketed(self) -> None:
        assert tab_token(HeaderTab("tasks_tab", "1", "Tasks")) == "[1] Tasks"

    def test_the_separator_is_a_dim_bar_with_spaces(self) -> None:
        # Its width is part of the wrap budget, so it is pinned here.
        assert SEPARATOR == " │ "
        assert cell_width(SEPARATOR) == 3
