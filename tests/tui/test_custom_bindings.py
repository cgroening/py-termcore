"""
Tests for loading key bindings from YAML and composing them per context.

The scope name is a contract, not a label: it decides whether an action is
prefixed, when it is visible, and which object Textual dispatches it on. None
of that fails loudly when it drifts - the shortcut simply stops working - so
the rules are pinned here rather than left to the consumer to discover.

The second contract is the order of `get_groups`, which is the order of the
footer. Nothing reorders it on the way out, so a test that pins file order
is what keeps that promise true.
"""

import logging
from collections.abc import Sequence

import pytest
from textual.binding import Binding

from termcore.tui.custom_bindings import CustomBindings
from tests.tui.conftest import WriteBindings, WriteScopes

BINDINGS = """
_global:
  - key: q
    action: quit
    description: Quit
tasks_tab:
  - key: a
    action: add
    description: Add
done_tab:
  - key: r
    action: reopen
    description: Reopen
add_screen:
  - key: escape
    action: cancel
    description: Cancel
"""


def actions(bindings: Sequence[object]) -> list[str]:
    """Returns the action of every binding, in order."""
    return [b.action for b in bindings if isinstance(b, Binding)]


class TestBindingsAreLoadedPerInstance:
    """
    The registry used to live in class attributes shared by every instance.

    A second CustomBindings in one process inherited the first one's groups
    and appended its own on top, so every binding appeared twice and every
    action mapped to its scope twice.
    """

    def test_a_second_instance_sees_the_same_bindings(
        self, write_bindings: WriteBindings
    ) -> None:
        path = write_bindings(BINDINGS)

        first = CustomBindings(path)
        second = CustomBindings(path)

        assert actions(second.get_bindings()) == actions(first.get_bindings())

    def test_a_second_instance_does_not_double_the_bindings(
        self, write_bindings: WriteBindings
    ) -> None:
        path = write_bindings(BINDINGS)

        CustomBindings(path)
        second = CustomBindings(path)

        assert actions(second.get_bindings()) == [
            "tasks_tab_add", "done_tab_reopen", "quit"
        ]

    def test_a_second_instance_does_not_double_the_groups(
        self, write_bindings: WriteBindings
    ) -> None:
        path = write_bindings(BINDINGS)

        first = CustomBindings(path)
        second = CustomBindings(path)

        assert second.get_groups() == first.get_groups()

    def test_two_instances_over_different_files_stay_separate(
        self, write_bindings: WriteBindings
    ) -> None:
        first = CustomBindings(write_bindings(BINDINGS))
        second = CustomBindings(write_bindings("""
            _global:
              - key: x
                action: exit
                description: Exit
        """))

        assert actions(second.get_bindings()) == ["exit"]
        assert "quit" in actions(first.get_bindings())


class TestActionPrefixing:
    def test_a_global_action_is_used_verbatim(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "quit" in actions(bindings.get_bindings())

    def test_a_tab_action_is_prefixed_with_its_scope(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "tasks_tab_add" in actions(bindings.get_bindings())

    def test_a_screen_action_is_used_verbatim(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "cancel" in actions(bindings.get_screen_bindings("add"))

    def test_any_scope_that_is_neither_prefixes_the_action(
        self, write_bindings: WriteBindings
    ) -> None:
        # Only the _global prefix and the _screen suffix are special; every
        # other scope name becomes the action prefix, "_tab" or not.
        bindings = CustomBindings(write_bindings("""
            whatever:
              - key: a
                action: go
                description: Go
        """))

        assert actions(bindings.get_bindings()) == ["whatever_go"]


class TestBindingFields:
    def test_optional_fields_have_defaults(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: q
                action: quit
                description: Quit
        """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.show is True
        assert binding.priority is False
        assert binding.tooltip == ""
        assert binding.id is None
        assert binding.system is False

    def test_declared_fields_are_carried_through(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: q
                action: quit
                description: Quit
                tooltip: Leave the application
                show: false
                priority: true
                system: true
                id: quit_binding
        """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.tooltip == "Leave the application"
        assert binding.show is False
        assert binding.priority is True
        assert binding.system is True
        assert binding.id == "quit_binding"

    def test_a_function_key_gets_a_display_name(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: f1
                action: help
                description: Help
        """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.key_display == "F1"

    def test_a_binding_without_a_key_is_dropped(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - action: quit
                description: Quit
        """))

        assert bindings.get_bindings() == []

    def test_a_binding_without_an_action_is_dropped(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: q
                description: Quit
        """))

        assert bindings.get_bindings() == []

    def test_a_binding_without_a_description_is_dropped(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: q
                action: quit
        """))

        assert bindings.get_bindings() == []


class TestGetBindings:
    def test_without_arguments_every_tab_and_the_globals_are_returned(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert actions(bindings.get_bindings()) == [
            "tasks_tab_add", "done_tab_reopen", "quit"
        ]

    def test_a_tab_name_selects_only_that_tab(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert actions(bindings.get_bindings(tab_name="tasks_tab")) == [
            "tasks_tab_add", "quit"
        ]

    def test_a_screen_name_excludes_every_tab(
        self, write_bindings: WriteBindings
    ) -> None:
        # A screen name implies the screen context, so the globals arrive
        # prefixed: a screen name implies the screen context.
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert actions(bindings.get_screen_bindings("add")) == [
            "cancel", "app.quit"
        ]

    def test_globals_come_last(self, write_bindings: WriteBindings) -> None:
        # The footer renders in this order, so it is part of the contract.
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert actions(bindings.get_bindings())[-1] == "quit"

    def test_screen_bindings_dispatch_globals_on_the_app(
        self, write_bindings: WriteBindings
    ) -> None:
        # Without the app. prefix a Screen would look for action_quit on
        # itself, find nothing, and the key would quietly do nothing.
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "app.quit" in actions(bindings.get_screen_bindings())

    def test_app_bindings_leave_globals_unprefixed(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "quit" in actions(bindings.get_bindings())

    def test_repeated_calls_do_not_stack_the_app_prefix(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        bindings.get_screen_bindings()
        second = bindings.get_screen_bindings()

        assert "app.quit" in actions(second)
        assert "app.app.quit" not in actions(second)


GROUPED = """
tasks_tab:
  - group: Tasks
    bindings:
      - key: a
        action: add
        description: Add
      - key: d
        action: done
        description: Done
  - key: x
    action: extra
    description: Extra
  - key: z
    action: zoom
    description: Zoom
  - group: Appearance
    bindings:
      - key: t
        action: theme
        description: Theme
_global:
  - group: App
    bindings:
      - key: q
        action: quit
        description: Quit
"""


def group_names(bindings: CustomBindings) -> list[str]:
    """Returns the name of every group, in the order they are returned."""
    return [group.name for group in bindings.get_groups()]


class TestGetGroups:
    """
    The order of these groups is the order of the footer rows.

    Nothing sorts them on the way out, so moving a group in the file is the
    only way to move its row - and a test is the only thing that keeps that
    promise from quietly acquiring an exception.
    """

    def test_groups_come_out_in_file_order(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(GROUPED))

        assert group_names(bindings) == ["Tasks", "", "Appearance", "App"]

    def test_bindings_keep_their_order_within_a_group(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(GROUPED))

        assert actions(bindings.get_groups()[0].bindings) == [
            "tasks_tab_add", "tasks_tab_done"
        ]

    def test_consecutive_loose_bindings_form_one_unnamed_group(
        self, write_bindings: WriteBindings
    ) -> None:
        # They sit between two named groups, so they may neither be swallowed
        # by a neighbour nor split into a row each.
        bindings = CustomBindings(write_bindings(GROUPED))
        unnamed = bindings.get_groups()[1]

        assert unnamed.name == ""
        assert actions(unnamed.bindings) == ["tasks_tab_extra",
                                             "tasks_tab_zoom"]

    def test_a_group_carries_the_scope_it_came_from(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(GROUPED))

        assert [group.scope for group in bindings.get_groups()] == [
            "tasks_tab", "tasks_tab", "tasks_tab", "_global"
        ]

    def test_the_same_name_in_two_scopes_stays_two_groups(
        self, write_bindings: WriteBindings
    ) -> None:
        # Merging them would produce one row fed from two places in the file.
        bindings = CustomBindings(write_bindings("""
            tasks_tab:
              - group: Appearance
                bindings:
                  - key: z
                    action: zoom
                    description: Zoom
            _global:
              - group: Appearance
                bindings:
                  - key: w
                    action: theme
                    description: Theme
        """))

        assert group_names(bindings) == ["Appearance", "Appearance"]
        assert [group.scope for group in bindings.get_groups()] == [
            "tasks_tab", "_global"
        ]

    def test_a_global_group_is_not_moved_to_the_end(
        self, write_bindings: WriteBindings
    ) -> None:
        # get_bindings still registers globals last, but that is Textual's
        # registration order and must not leak into the footer's layout.
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert group_names(bindings) == ["", "", "", ""]
        assert bindings.get_groups()[0].scope == "_global"

    def test_a_file_without_groups_yields_unnamed_ones(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert all(group.name == "" for group in bindings.get_groups())

    def test_every_binding_reaches_exactly_one_group(
        self, write_bindings: WriteBindings
    ) -> None:
        # A binding that no group claims is invisible in the footer while
        # its key still works, which is the hardest shape to notice.
        bindings = CustomBindings(write_bindings(GROUPED))
        grouped = [
            action
            for group in bindings.get_groups()
            for action in actions(group.bindings)
        ]

        assert sorted(grouped) == sorted(actions(bindings.get_bindings()))


class TestHandleCheckAction:
    def test_an_unknown_action_passes(
        self, write_bindings: WriteBindings
    ) -> None:
        # Textual's own actions must not be filtered out by this.
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.handle_check_action("toggle_dark", (), "tasks_tab")

    def test_a_global_action_passes_in_any_scope(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.handle_check_action("quit", (), "tasks_tab")
        assert bindings.handle_check_action("quit", (), "done_tab")

    def test_a_tab_action_passes_in_its_own_tab(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.handle_check_action("tasks_tab_add", (), "tasks_tab")

    def test_a_tab_action_is_hidden_elsewhere(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert not bindings.handle_check_action(
            "tasks_tab_add", (), "done_tab"
        )

    def test_an_app_prefixed_action_is_not_recognised(
        self, write_bindings: WriteBindings
    ) -> None:
        # It passes only because it looks like an unknown action. This is
        # why the caller has to strip the prefix before asking - see
        # termplate's MainScreen.check_action.
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.handle_check_action("app.quit", (), "tasks_tab")


class TestSilentPathsAreReported:
    """
    Each of these used to happen without a word.

    A shortcut that quietly does not exist is the hardest kind of defect to
    find, because nothing about the running app points at the YAML file.
    """

    def test_a_dropped_binding_names_the_missing_fields(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            CustomBindings(write_bindings("""
                _global:
                  - key: q
                    action: quit
            """))

        assert "Skipping a binding in scope '_global'" in caplog.text
        assert "description" in caplog.text

    def test_a_duplicate_action_is_reported(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Only scopes that do not prefix can collide, so this is a global and
        # a screen claiming the same name. The footer matches its rows by
        # action, so the second declaration never renders a key of its own.
        with caplog.at_level(logging.WARNING):
            bindings = CustomBindings(write_bindings("""
                _global:
                  - key: escape
                    action: cancel
                    description: Cancel
                add_screen:
                  - key: q
                    action: cancel
                    description: Also cancel
            """))

        assert "declared more than once" in caplog.text
        assert "_global, add_screen" in caplog.text
        assert len(bindings.get_groups()) == 2

    def test_an_unknown_tab_name_is_reported(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        with caplog.at_level(logging.WARNING):
            result = bindings.get_bindings(tab_name="no_such_tab")

        assert actions(result) == ["quit"]
        assert "No binding scope" in caplog.text

    def test_an_unknown_screen_name_is_reported(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        with caplog.at_level(logging.WARNING):
            bindings.get_screen_bindings("no_such_screen")

        assert "No binding scope" in caplog.text

    def test_a_known_name_is_silent(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        with caplog.at_level(logging.WARNING):
            bindings.get_bindings(tab_name="tasks_tab")
            bindings.get_screen_bindings("add")

        assert caplog.text == ""


class TestBooleanFieldsAreReadStrictly:
    """`bool("false")` is True, so a quoted boolean meant its opposite."""

    def test_a_quoted_false_is_refused(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            bindings = CustomBindings(write_bindings("""
                _global:
                  - key: q
                    action: quit
                    description: Quit
                    show: "false"
            """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.show is True  # the documented default, not the string
        assert "Expected true or false" in caplog.text

    def test_an_unquoted_false_is_honoured(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            bindings = CustomBindings(write_bindings("""
                _global:
                  - key: q
                    action: quit
                    description: Quit
                    show: false
            """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.show is False
        assert caplog.text == ""

    def test_a_number_is_refused_for_priority(
        self, write_bindings: WriteBindings, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            bindings = CustomBindings(write_bindings("""
                _global:
                  - key: q
                    action: quit
                    description: Quit
                    priority: 1
            """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.priority is False
        assert "Expected true or false" in caplog.text


class TestKeyDisplayPrecedence:
    def test_a_declared_value_wins_over_the_function_key_rule(
        self, write_bindings: WriteBindings
    ) -> None:
        # The field exists to override how the key is rendered, so overriding
        # it in turn was backwards.
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: f1
                action: help
                description: Help
                key_display: Hilfe
        """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.key_display == "Hilfe"

    def test_a_function_key_without_one_is_still_formatted(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: f1
                action: help
                description: Help
        """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.key_display == "F1"

    def test_an_ordinary_key_is_left_to_textual(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings("""
            _global:
              - key: ctrl+s
                action: save
                description: Save
        """))

        binding = bindings.get_bindings()[0]

        assert isinstance(binding, Binding)
        assert binding.key_display is None


class TestScopeTitles:
    """
    The display names of the scopes live in a second file.

    A second file can go stale in both directions - a scope with no title, a
    title for a scope that no longer exists - and neither shows up while the
    app runs. Both directions are pinned here.
    """

    TITLES = """
        tasks_tab:
          title: "Tasks"
          key: "1"
        _global:
          title: "Global"
    """

    def test_a_declared_title_is_returned(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = CustomBindings(
            write_bindings(BINDINGS), write_scopes(self.TITLES)
        )

        assert bindings.scope_title("tasks_tab") == "Tasks"

    def test_a_scope_without_a_title_falls_back_to_its_name(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        # The raw name is meant to look unfinished rather than be invented.
        bindings = CustomBindings(
            write_bindings(BINDINGS), write_scopes(self.TITLES)
        )

        assert bindings.scope_title("done_tab") == "done_tab"

    def test_without_a_scopes_file_every_title_is_the_raw_name(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.scope_title("tasks_tab") == "tasks_tab"

    def test_the_groups_carry_the_title(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        # The overlay reads it off the group, so the two must agree.
        bindings = CustomBindings(
            write_bindings(BINDINGS), write_scopes(self.TITLES)
        )
        titles = {g.scope: g.scope_title for g in bindings.get_groups()}

        assert titles["tasks_tab"] == "Tasks"
        assert titles["done_tab"] == ""

    def test_a_title_without_a_scope_is_reported(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        # Left behind by a renamed scope, and invisible otherwise: nothing
        # ever asks for that scope, so the stale line just sits there.
        with caplog.at_level(logging.WARNING):
            CustomBindings(
                write_bindings(BINDINGS),
                write_scopes("""
                    tasks_tab:
                      title: "Tasks"
                    gone_tab:
                      title: "Gone"
                """),
            )

        assert "'gone_tab'" in caplog.text

    def test_a_non_string_title_is_refused(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        # The Norway problem again: an unquoted "No" arrives as a bool.
        with caplog.at_level(logging.WARNING):
            bindings = CustomBindings(
                write_bindings(BINDINGS),
                write_scopes("tasks_tab:\n  title: no"),
            )

        assert "quote the value" in caplog.text
        assert bindings.scope_title("tasks_tab") == "tasks_tab"

    def test_an_empty_scopes_file_is_not_an_error(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS), write_scopes(""))

        assert bindings.scope_title("tasks_tab") == "tasks_tab"


class TestTabBindings:
    """
    Declaring a key is what makes a scope a tab.

    The key lives in the scopes file and nowhere else, so the header and the
    shortcut that actually fires cannot disagree about it.
    """

    SCOPES = """
        tasks_tab:
          title: "Tasks"
          key: "1"
        done_tab:
          title: "Done"
          key: "2"
        add_screen:
          title: "Add dialog"
        _global:
          title: "Global"
    """

    def _bindings(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> CustomBindings:
        return CustomBindings(
            write_bindings(BINDINGS), write_scopes(self.SCOPES)
        )

    def test_a_declared_key_is_returned(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = self._bindings(write_bindings, write_scopes)

        assert bindings.scope_key("tasks_tab") == "1"

    def test_a_scope_without_a_key_has_none(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = self._bindings(write_bindings, write_scopes)

        assert bindings.scope_key("_global") == ""

    def test_only_scopes_with_a_key_are_tabs(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = self._bindings(write_bindings, write_scopes)

        assert bindings.get_tab_scopes() == ["tasks_tab", "done_tab"]

    def test_the_tab_order_is_the_file_order(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        # Same rule as the footer: the file decides, nothing re-sorts.
        bindings = CustomBindings(
            write_bindings(BINDINGS),
            write_scopes("""
                done_tab:
                  title: "Done"
                  key: "2"
                tasks_tab:
                  title: "Tasks"
                  key: "1"
            """),
        )

        assert bindings.get_tab_scopes() == ["done_tab", "tasks_tab"]

    def test_a_binding_is_built_for_every_tab(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = self._bindings(write_bindings, write_scopes)
        tab_bindings = bindings.get_tab_bindings()

        assert [b.key for b in tab_bindings if isinstance(b, Binding)] == [
            "1", "2"
        ]

    def test_the_binding_carries_the_scope_as_its_argument(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = self._bindings(write_bindings, write_scopes)
        first = bindings.get_tab_bindings()[0]

        assert isinstance(first, Binding)
        assert first.action == "show_tab('tasks_tab')"

    def test_the_bindings_stay_out_of_the_footer(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        # The header already prints them; a footer row would repeat it.
        bindings = self._bindings(write_bindings, write_scopes)

        for binding in bindings.get_tab_bindings():
            assert isinstance(binding, Binding)
            assert binding.show is False

    def test_the_binding_is_described_by_the_scope_title(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes
    ) -> None:
        bindings = self._bindings(write_bindings, write_scopes)
        first = bindings.get_tab_bindings()[0]

        assert isinstance(first, Binding)
        assert first.description == "Tasks"

    def test_without_a_scopes_file_there_are_no_tabs(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.get_tab_bindings() == []

    def test_a_scope_that_is_not_a_mapping_is_reported(
        self, write_bindings: WriteBindings, write_scopes: WriteScopes,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            bindings = CustomBindings(
                write_bindings(BINDINGS), write_scopes('tasks_tab: "Tasks"')
            )

        assert "Expected a mapping" in caplog.text
        assert bindings.scope_title("tasks_tab") == "tasks_tab"
