"""
Tests for what the help overlay lists.

The overlay and the footer read the same groups but lay them out on different
axes, so the rules worth pinning are the ones where they differ: the overlay
heads its sections with the scope, adds the group only as a second level, and
filters where the footer does not.
"""

from textual.binding import Binding

from termcore.tui.binding_groups import BindingGroup
from termcore.tui.help_rows import (
    GROUP_LEVEL,
    SCOPE_LEVEL,
    HelpCoverage,
    HelpEntry,
    HelpHeader,
    HelpRequest,
    HelpRows,
    build_rows,
)

TASKS = BindingGroup(
    name="Tasks",
    scope="tasks_tab",
    scope_title="Tasks",
    bindings=(
        Binding("a", "tasks_tab_add", "Add"),
        Binding("d", "tasks_tab_done", "Done"),
    ),
)
DONE = BindingGroup(
    name="Done",
    scope="done_tab",
    scope_title="Done",
    bindings=(Binding("r", "done_tab_reopen", "Reopen"),),
)
# Two groups under one scope, which is what makes the second level appear.
APPEARANCE = BindingGroup(
    name="Appearance",
    scope="_global",
    scope_title="Global",
    bindings=(Binding("w", "prev_theme", "Previous Theme"),),
)
APP = BindingGroup(
    name="App",
    scope="_global",
    scope_title="Global",
    bindings=(
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help"),
    ),
)
UNTITLED = BindingGroup(
    name="Misc",
    scope="misc_tab",
    bindings=(Binding("m", "misc_tab_go", "Go"),),
)
UNNAMED = BindingGroup(
    name="",
    scope="other_tab",
    scope_title="Other",
    bindings=(Binding("o", "other_tab_go", "Go"),),
)


def headings(rows: HelpRows, level: int | None = None) -> list[str]:
    """Returns the label of every heading, optionally of one level only."""
    return [
        row.label
        for row in rows.rows
        if isinstance(row, HelpHeader)
        and (level is None or row.level == level)
    ]


def descriptions(rows: HelpRows) -> list[str]:
    """Returns the description of every entry, in order."""
    return [
        row.description for row in rows.rows if isinstance(row, HelpEntry)
    ]


class TestScopeHeadings:
    def test_a_scope_heads_its_section(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest())

        assert headings(rows, SCOPE_LEVEL) == ["Tasks", "Done"]

    def test_scopes_follow_the_declared_order(self) -> None:
        rows = build_rows([DONE, TASKS], HelpRequest())

        assert headings(rows, SCOPE_LEVEL) == ["Done", "Tasks"]

    def test_a_scope_without_a_title_shows_its_raw_name(self) -> None:
        # Meant to look unfinished: it is a prompt to declare the title.
        rows = build_rows([UNTITLED], HelpRequest())

        assert headings(rows, SCOPE_LEVEL) == ["misc_tab"]

    def test_the_groups_of_one_scope_share_one_heading(self) -> None:
        rows = build_rows([APPEARANCE, APP], HelpRequest())

        assert headings(rows, SCOPE_LEVEL) == ["Global"]

    def test_a_scope_heading_precedes_its_entries(self) -> None:
        rows = build_rows([TASKS], HelpRequest())

        assert rows.rows[0] == HelpHeader("Tasks", SCOPE_LEVEL)


class TestGroupHeadings:
    def test_a_scope_with_one_group_prints_no_group_heading(self) -> None:
        # "Tasks" under "Tasks" would say the same thing twice.
        rows = build_rows([TASKS], HelpRequest())

        assert headings(rows, GROUP_LEVEL) == []

    def test_a_scope_with_two_groups_prints_both(self) -> None:
        rows = build_rows([APPEARANCE, APP], HelpRequest())

        assert headings(rows, GROUP_LEVEL) == ["Appearance", "App"]

    def test_an_unnamed_group_never_gets_a_heading(self) -> None:
        rows = build_rows([UNNAMED], HelpRequest())

        assert headings(rows, GROUP_LEVEL) == []
        assert headings(rows, SCOPE_LEVEL) == ["Other"]

    def test_a_search_that_leaves_one_group_drops_its_heading(self) -> None:
        # The second level exists to tell groups apart; with one left there
        # is nothing to tell apart, filtered down or not.
        rows = build_rows([APPEARANCE, APP], HelpRequest(query="theme"))

        assert headings(rows, SCOPE_LEVEL) == ["Global"]
        assert headings(rows, GROUP_LEVEL) == []


class TestLevels:
    def test_entries_sit_below_their_scope(self) -> None:
        rows = build_rows([TASKS], HelpRequest())
        levels = {
            row.level for row in rows.rows if isinstance(row, HelpEntry)
        }

        assert levels == {GROUP_LEVEL}

    def test_entries_sit_one_deeper_under_a_group_heading(self) -> None:
        rows = build_rows([APPEARANCE, APP], HelpRequest())
        levels = {
            row.level for row in rows.rows if isinstance(row, HelpEntry)
        }

        assert levels == {GROUP_LEVEL + 1}


class TestFiltering:
    def test_an_empty_query_keeps_everything(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest(query=""))

        assert rows.matches == 3

    def test_a_query_filters_the_entries(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest(query="reopen"))

        assert descriptions(rows) == ["Reopen"]

    def test_a_scope_without_a_match_loses_its_heading(self) -> None:
        # An empty section under a heading reads as a defect.
        rows = build_rows([TASKS, DONE], HelpRequest(query="reopen"))

        assert headings(rows, SCOPE_LEVEL) == ["Done"]

    def test_matching_is_fuzzy_rather_than_substring(self) -> None:
        rows = build_rows([DONE], HelpRequest(query="rpn"))

        assert descriptions(rows) == ["Reopen"]

    def test_a_query_matching_nothing_yields_no_rows(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest(query="zzzz"))

        assert rows.rows == ()
        assert rows.matches == 0

    def test_the_key_is_searchable_too(self) -> None:
        rows = build_rows([TASKS], HelpRequest(query="d"))

        assert "Done" in descriptions(rows)

    def test_filtering_does_not_reorder_the_entries(self) -> None:
        # Ranking by score would fight the rule that the file decides order.
        group = BindingGroup(
            name="Nav", scope="tasks_tab",
            bindings=(
                Binding("z", "tasks_tab_z", "aaa match"),
                Binding("a", "tasks_tab_a", "match"),
            ),
        )

        rows = build_rows([group], HelpRequest(query="match"))

        assert descriptions(rows) == ["aaa match", "match"]

    def test_the_match_count_ignores_headings(self) -> None:
        rows = build_rows([APPEARANCE, APP], HelpRequest())

        assert rows.matches == 3
        assert len(rows.rows) == 6  # one scope, two groups, three entries


class TestCoverage:
    def test_all_lists_bindings_that_are_not_active(self) -> None:
        rows = build_rows(
            [TASKS, DONE],
            HelpRequest(coverage=HelpCoverage.ALL, active=frozenset()),
        )

        assert rows.matches == 3

    def test_active_hides_what_would_not_fire(self) -> None:
        rows = build_rows(
            [TASKS, DONE],
            HelpRequest(
                coverage=HelpCoverage.ACTIVE,
                active=frozenset({"tasks_tab_add", "tasks_tab_done"}),
            ),
        )

        assert descriptions(rows) == ["Add", "Done"]
        assert headings(rows, SCOPE_LEVEL) == ["Tasks"]

    def test_active_matches_a_global_through_its_app_prefix(self) -> None:
        # The snapshot holds bare names; the binding may carry app.
        group = BindingGroup(
            name="App", scope="_global", scope_title="Global",
            bindings=(Binding("q", "app.quit", "Quit"),),
        )

        rows = build_rows(
            [group],
            HelpRequest(
                coverage=HelpCoverage.ACTIVE, active=frozenset({"quit"})
            ),
        )

        assert descriptions(rows) == ["Quit"]


class TestEntryText:
    def test_the_matched_text_is_the_rendered_text(self) -> None:
        # A highlight applies its hit positions to this string, so the two
        # drifting apart would colour the wrong characters.
        rows = build_rows([TASKS], HelpRequest())
        entry = rows.rows[1]

        assert isinstance(entry, HelpEntry)
        assert entry.key in entry.text
        assert entry.description in entry.text

    def test_the_indent_is_not_part_of_the_matched_text(self) -> None:
        # The overlay prepends it when rendering; baking it in here would
        # shift every highlight position by the indent's width.
        rows = build_rows([APPEARANCE, APP], HelpRequest())
        entries = [r for r in rows.rows if isinstance(r, HelpEntry)]

        assert all(not entry.text.startswith(" ") for entry in entries)

    def test_descriptions_line_up_in_a_column(self) -> None:
        group = BindingGroup(
            name="Nav", scope="t",
            bindings=(
                Binding("a", "t_a", "Short"),
                Binding("ctrl+x", "t_x", "Long"),
            ),
        )

        rows = build_rows([group], HelpRequest())
        starts = {
            row.text.index(row.description)
            for row in rows.rows if isinstance(row, HelpEntry)
        }

        assert len(starts) == 1
