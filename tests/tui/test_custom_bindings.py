"""Tests for loading key bindings from YAML and composing them per context.

The group name is a contract, not a label: it decides whether an action is
prefixed, when it is visible, and which object Textual dispatches it on. None
of that fails loudly when it drifts - the shortcut simply stops working - so
the rules are pinned here rather than left to the consumer to discover.
"""

from collections.abc import Sequence

from textual.binding import Binding

from termz.tui.custom_bindings import CustomBindings
from tests.tui.conftest import WriteBindings

BINDINGS = """
_global:
  - key: q
    action: quit
    description: Quit
    row: 1
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
    """The registry used to live in class attributes shared by every instance.

    A second CustomBindings in one process inherited the first one's groups
    and appended its own on top, so every binding appeared twice and every
    action mapped to its group twice.
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

    def test_a_second_instance_does_not_double_the_row_map(
        self, write_bindings: WriteBindings
    ) -> None:
        path = write_bindings(BINDINGS)

        first = CustomBindings(path)
        second = CustomBindings(path)

        assert second.get_row_map() == first.get_row_map()

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

    def test_a_tab_action_is_prefixed_with_its_group(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "tasks_tab_add" in actions(bindings.get_bindings())

    def test_a_screen_action_is_used_verbatim(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "cancel" in actions(bindings.get_screen_bindings("add"))

    def test_any_group_that_is_neither_prefixes_the_action(
        self, write_bindings: WriteBindings
    ) -> None:
        # Only the _global prefix and the _screen suffix are special; every
        # other group name becomes the action prefix, "_tab" or not.
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

    def test_sorting_treats_function_keys_numerically(
        self, write_bindings: WriteBindings
    ) -> None:
        # Plain string sorting would put f10 before f2.
        bindings = CustomBindings.sorted_by_key(write_bindings("""
            _global:
              - key: f10
                action: ten
                description: Ten
              - key: f2
                action: two
                description: Two
        """))

        assert actions(bindings.get_bindings()) == ["two", "ten"]


class TestGetRowMap:
    def test_rows_come_from_the_yaml(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.get_row_map()["quit"] == 1

    def test_a_missing_row_defaults_to_zero(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.get_row_map()["tasks_tab_add"] == 0

    def test_the_screen_row_map_prefixes_the_globals(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "app.quit" in bindings.get_screen_row_map()

    def test_the_screen_row_map_leaves_tab_actions_alone(
        self, write_bindings: WriteBindings
    ) -> None:
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert "tasks_tab_add" in bindings.get_screen_row_map()

    def test_the_row_map_keys_match_the_binding_actions(
        self, write_bindings: WriteBindings
    ) -> None:
        # The footer looks its rows up by action name. If the two disagree
        # about the app. prefix, every global silently loses its row.
        bindings = CustomBindings(write_bindings(BINDINGS))
        row_map = bindings.get_screen_row_map()

        for action in actions(bindings.get_screen_bindings()):
            assert action in row_map


class TestHandleCheckAction:
    def test_an_unknown_action_passes(
        self, write_bindings: WriteBindings
    ) -> None:
        # Textual's own actions must not be filtered out by this.
        bindings = CustomBindings(write_bindings(BINDINGS))

        assert bindings.handle_check_action("toggle_dark", (), "tasks_tab")

    def test_a_global_action_passes_in_any_group(
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
