"""
Tests for the arithmetic behind the multi-line footer.

Layout defects are the quiet kind: a column that is one cell too narrow or a
group that silently renders no row looks like a design choice rather than a
bug. Every rule the footer relies on is pinned here, where it can be checked
without starting an application.
"""

from collections.abc import Sequence

from textual.binding import Binding

from termcore.tui.binding_groups import BindingGroup
from termcore.tui.custom_widgets.footer_rows import (
    LABEL_GAP,
    SEPARATOR,
    FooterHint,
    FooterLayout,
    FooterRowPlan,
    hint_width,
    label_column_width,
)
from termcore.util.string import cell_width

WIDE = 200


def binding(key: str, action: str, description: str) -> Binding:
    """Builds a binding with just the fields the footer reads."""
    return Binding(key=key, action=action, description=description)


def group(name: str, scope: str, *bindings: Binding) -> BindingGroup:
    """Builds a group of the given bindings."""
    return BindingGroup(name=name, scope=scope, bindings=bindings)


def hints(*bindings: Binding) -> list[FooterHint]:
    """Turns bindings into active hints, all enabled."""
    return [FooterHint(b, enabled=True, tooltip="") for b in bindings]


def layout(width: int = WIDE, max_rows: int = 0) -> FooterLayout:
    """Builds a layout that renders a key by its own name."""
    return FooterLayout(
        key_display=lambda b: b.key, width=width, max_rows=max_rows
    )


def keys(rows: Sequence[FooterRowPlan]) -> list[list[str]]:
    """Returns the key of every hint, row by row."""
    return [[hint.binding.key for hint in row.hints] for row in rows]


class TestLabelColumn:
    def test_the_column_fits_the_widest_label(self) -> None:
        groups = [
            group("Tasks", "tasks_tab", binding("a", "add", "Add")),
            group("Appearance", "_global", binding("w", "theme", "Theme")),
        ]

        assert label_column_width(groups) == len("Appearance:") + LABEL_GAP

    def test_a_footer_without_labels_reserves_nothing(self) -> None:
        groups = [group("", "tasks_tab", binding("a", "add", "Add"))]

        assert label_column_width(groups) == 0

    def test_every_row_shares_one_column_width(self) -> None:
        # The whole point of the column is that the keys of all rows start in
        # the same place; a per-row width would defeat it.
        rows = layout().group_rows(
            [
                group("Tasks", "tasks_tab", binding("a", "add", "Add")),
                group("Appearance", "_global", binding("w", "th", "Theme")),
            ],
            hints(binding("a", "add", "Add"), binding("w", "th", "Theme")),
        )

        widths = {cell_width(row.label) for row in rows}

        assert len(widths) == 1

    def test_an_unnamed_group_keeps_the_column_blank(self) -> None:
        rows = layout().group_rows(
            [
                group("Tasks", "tasks_tab", binding("a", "add", "Add")),
                group("", "_global", binding("q", "quit", "Quit")),
            ],
            hints(binding("a", "add", "Add"), binding("q", "quit", "Quit")),
        )

        assert rows[1].label.strip() == ""
        assert cell_width(rows[1].label) == cell_width(rows[0].label)

    def test_a_wide_label_is_measured_in_cells_not_characters(self) -> None:
        # Three CJK characters are six cells wide. Counting characters would
        # make the column too narrow and push every row out of alignment.
        groups = [group("日本語", "tasks_tab", binding("a", "add", "Add"))]

        assert label_column_width(groups) == 6 + len(":") + LABEL_GAP


class TestGroupRows:
    def test_rows_follow_the_order_of_the_groups(self) -> None:
        rows = layout().group_rows(
            [
                group("Second", "b", binding("b", "beta", "Beta")),
                group("First", "a", binding("a", "alpha", "Alpha")),
            ],
            hints(binding("a", "alpha", "Alpha"), binding("b", "beta", "B")),
        )

        assert [row.label.strip() for row in rows] == ["Second:", "First:"]

    def test_a_group_without_active_bindings_yields_no_row(self) -> None:
        # An inactive tab must not leave a blank row behind.
        rows = layout().group_rows(
            [
                group("Tasks", "tasks_tab", binding("a", "add", "Add")),
                group("Done", "done_tab", binding("r", "reopen", "Reopen")),
            ],
            hints(binding("a", "add", "Add")),
        )

        assert keys(rows) == [["a"]]

    def test_a_hidden_group_does_not_widen_the_column(self) -> None:
        rows = layout().group_rows(
            [
                group("Tasks", "tasks_tab", binding("a", "add", "Add")),
                group("A very long label", "x", binding("r", "re", "Re")),
            ],
            hints(binding("a", "add", "Add")),
        )

        assert cell_width(rows[0].label) == len("Tasks:") + LABEL_GAP

    def test_a_global_action_matches_its_app_prefixed_hint(self) -> None:
        # A screen renames a global action to app.<action> on its way in. If
        # the two are not matched, every global key vanishes from the footer.
        rows = layout().group_rows(
            [group("App", "_global", binding("q", "quit", "Quit"))],
            hints(binding("q", "app.quit", "Quit")),
        )

        assert keys(rows) == [["q"]]

    def test_an_action_declared_twice_renders_once(self) -> None:
        rows = layout().group_rows(
            [
                group("First", "_global", binding("q", "cancel", "Cancel")),
                group("Second", "add_screen", binding("x", "cancel", "Also")),
            ],
            hints(binding("q", "cancel", "Cancel")),
        )

        assert keys(rows) == [["q"]]

    def test_an_action_bound_to_two_keys_yields_two_hints(self) -> None:
        rows = layout().group_rows(
            [
                group(
                    "Nav", "tasks_tab",
                    binding("up", "move", "Up"), binding("k", "move", "Up"),
                )
            ],
            hints(binding("up", "move", "Up"), binding("k", "move", "Up")),
        )

        assert keys(rows) == [["up", "k"]]


class TestWrapping:
    def test_a_group_too_wide_for_the_row_wraps(self) -> None:
        rows = layout(width=24).group_rows(
            [
                group(
                    "Nav", "tasks_tab",
                    binding("a", "one", "First"),
                    binding("b", "two", "Second"),
                    binding("c", "three", "Third"),
                )
            ],
            hints(
                binding("a", "one", "First"),
                binding("b", "two", "Second"),
                binding("c", "three", "Third"),
            ),
        )

        assert len(rows) > 1

    def test_a_continuation_row_keeps_the_column_but_drops_the_label(
        self,
    ) -> None:
        # The hints of a wrapped row line up under the hints above them, not
        # under the label - that is the whole reason the column is blanked.
        rows = layout(width=24).group_rows(
            [
                group(
                    "Nav", "tasks_tab",
                    binding("a", "one", "First"),
                    binding("b", "two", "Second"),
                    binding("c", "three", "Third"),
                )
            ],
            hints(
                binding("a", "one", "First"),
                binding("b", "two", "Second"),
                binding("c", "three", "Third"),
            ),
        )

        assert rows[0].label.strip() == "Nav:"
        for row in rows[1:]:
            assert row.label.strip() == ""
            assert cell_width(row.label) == cell_width(rows[0].label)

    def test_no_row_exceeds_the_available_width(self) -> None:
        bindings = [
            binding(chr(ord("a") + i), f"act{i}", f"Action {i}")
            for i in range(8)
        ]
        width = 40
        rows = layout(width=width).group_rows(
            [group("Nav", "tasks_tab", *bindings)], hints(*bindings)
        )
        column = cell_width(rows[0].label)

        for row in rows:
            used = sum(
                hint_width(h.binding.key, h.binding.description)
                for h in row.hints
            ) + (len(row.hints) - 1) * cell_width(SEPARATOR)

            assert column + used <= width

    def test_max_rows_stops_a_group_from_growing(self) -> None:
        bindings = [
            binding(chr(ord("a") + i), f"act{i}", f"Action {i}")
            for i in range(8)
        ]
        rows = layout(width=24, max_rows=2).group_rows(
            [group("Nav", "tasks_tab", *bindings)], hints(*bindings)
        )

        assert len(rows) == 2

    def test_a_single_hint_never_wraps_away(self) -> None:
        # Even a key wider than the terminal has to render somewhere.
        rows = layout(width=4).group_rows(
            [group("Nav", "t", binding("ctrl+x", "act", "Something long"))],
            hints(binding("ctrl+x", "act", "Something long")),
        )

        assert keys(rows) == [["ctrl+x"]]


class TestFlatRows:
    def test_without_groups_the_keys_flow_without_a_column(self) -> None:
        rows = layout().flat_rows(
            hints(binding("a", "add", "Add"), binding("q", "quit", "Quit"))
        )

        assert keys(rows) == [["a", "q"]]
        assert rows[0].label == ""

    def test_flat_rows_wrap_on_width(self) -> None:
        bindings = [
            binding(chr(ord("a") + i), f"act{i}", f"Action {i}")
            for i in range(8)
        ]

        rows = layout(width=30).flat_rows(hints(*bindings))

        assert len(rows) > 1

    def test_no_hints_produce_no_rows(self) -> None:
        assert layout().flat_rows([]) == []


class TestHintWidth:
    def test_a_key_without_a_description_is_narrower(self) -> None:
        assert hint_width("q", "") < hint_width("q", "Quit")

    def test_a_wide_key_is_measured_in_cells(self) -> None:
        assert hint_width("日", "") == hint_width("ab", "")
