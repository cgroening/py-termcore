"""Tests for what the help overlay lists.

The overlay and the footer read the same groups, so the rules that differ
between them are the ones worth pinning: a list needs a heading where the
footer can leave a blank gutter, and it filters where the footer does not.
"""

from textual.binding import Binding

from termcore.tui.binding_groups import BindingGroup
from termcore.tui.help_rows import (
    HelpEntry,
    HelpHeader,
    HelpRequest,
    HelpRows,
    HelpScope,
    build_rows,
)

TASKS = BindingGroup(
    name="Tasks",
    scope="tasks_tab",
    bindings=(
        Binding("a", "tasks_tab_add", "Add"),
        Binding("d", "tasks_tab_done", "Done"),
    ),
)
DONE = BindingGroup(
    name="Done",
    scope="done_tab",
    bindings=(Binding("r", "done_tab_reopen", "Reopen"),),
)
UNNAMED = BindingGroup(
    name="",
    scope="_global",
    bindings=(Binding("q", "quit", "Quit"),),
)


def headers(rows: HelpRows) -> list[str]:
    """Returns the label of every heading, in order."""
    return [row.label for row in rows.rows if isinstance(row, HelpHeader)]


def descriptions(rows: HelpRows) -> list[str]:
    """Returns the description of every entry, in order."""
    return [
        row.description for row in rows.rows if isinstance(row, HelpEntry)
    ]


class TestGrouping:
    def test_every_group_gets_a_heading(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest())

        assert headers(rows) == ["Tasks", "Done"]

    def test_an_unnamed_group_is_titled_after_its_scope(self) -> None:
        # The footer can leave the gutter blank; a list cannot.
        rows = build_rows([UNNAMED], HelpRequest())

        assert headers(rows) == ["_global"]

    def test_entries_follow_the_declared_order(self) -> None:
        rows = build_rows([TASKS], HelpRequest())

        assert descriptions(rows) == ["Add", "Done"]

    def test_a_heading_precedes_its_entries(self) -> None:
        rows = build_rows([TASKS], HelpRequest())

        assert isinstance(rows.rows[0], HelpHeader)
        assert all(isinstance(row, HelpEntry) for row in rows.rows[1:])

    def test_the_match_count_ignores_headings(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest())

        assert rows.matches == 3
        assert len(rows.rows) == 5


class TestSearch:
    def test_an_empty_query_keeps_everything(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest(query=""))

        assert rows.matches == 3

    def test_a_query_filters_the_entries(self) -> None:
        rows = build_rows([TASKS, DONE], HelpRequest(query="reopen"))

        assert descriptions(rows) == ["Reopen"]

    def test_a_group_without_a_match_loses_its_heading(self) -> None:
        # An empty section under a heading reads as a defect.
        rows = build_rows([TASKS, DONE], HelpRequest(query="reopen"))

        assert headers(rows) == ["Done"]

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


class TestScope:
    def test_all_lists_bindings_that_are_not_active(self) -> None:
        rows = build_rows(
            [TASKS, DONE],
            HelpRequest(scope=HelpScope.ALL, active=frozenset()),
        )

        assert rows.matches == 3

    def test_active_hides_what_would_not_fire(self) -> None:
        rows = build_rows(
            [TASKS, DONE],
            HelpRequest(
                scope=HelpScope.ACTIVE,
                active=frozenset({"tasks_tab_add", "tasks_tab_done"}),
            ),
        )

        assert descriptions(rows) == ["Add", "Done"]
        assert headers(rows) == ["Tasks"]

    def test_active_matches_a_global_through_its_app_prefix(self) -> None:
        # The snapshot holds bare names; the binding may carry app.
        group = BindingGroup(
            name="App", scope="_global",
            bindings=(Binding("q", "app.quit", "Quit"),),
        )

        rows = build_rows(
            [group],
            HelpRequest(scope=HelpScope.ACTIVE, active=frozenset({"quit"})),
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
