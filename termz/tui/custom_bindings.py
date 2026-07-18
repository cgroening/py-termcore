"""
Key bindings for Textual applications, declared in YAML.

This module defines the class `CustomBindings` for managing custom keyboard
bindings in a Textual application. It loads key binding definitions from
a YAML file and exposes them as Textual `Binding` objects.

Reserved group naming conventions:

- `_global`      Always-visible bindings; action is used as-is (no prefix)
- `<name>_tab`   Shown only when that tab is active; action is prefixed with
                   the full group name, e.g. `tasks_tab_add_task`
- `<name>_screen` Screen-specific bindings; action is used as-is (no prefix)

YAML structure
--------------
The YAML file is a mapping of group names to lists of binding definitions.
Each binding supports the following fields:

  key         (required) Key to bind, e.g. `q`, `f1`, `ctrl+s`
  action      (required) Action name (see group-specific prefixing below)
  description (required) Short label shown in the footer
  tooltip               Longer description shown on hover
  key_display           Override how the key is rendered in the footer
  row                   Footer row index (0-based, default: 0)
  priority              bool - show binding even when a widget captures input
  show                  bool - whether to show in the footer (default: true)
  id                    Optional binding ID
  system                bool - mark as a system binding

Group naming rules
------------------
`_global`
    Bindings that are always visible. The action is used as-is (no prefix),
    e.g. `action: quit` → `quit`. When included in a Screen's `BINDINGS`
    via `get_bindings(for_screen=True)`, these actions are automatically
    prefixed with `app.` so Textual dispatches them on the App.

`<name>_tab`
    Tab-specific bindings, shown only when that tab is active. The action is
    prefixed with the group name, e.g. group `tasks_tab` + `action: add`
    → `tasks_tab_add`. Use `check_action` with the active tab name as
    `active_group` to control visibility.

`<name>_screen`
    Screen-specific bindings. The action is used as-is (no prefix), so it maps
    directly to an `action_<name>` method on the Screen.

Example
-------
.. code-block:: yaml

    # Always shown (action = <action>, no prefix)
    _global:
      - key: q
        action: quit
        description: Quit
        tooltip: Exit the application
        priority: true
        row: 1

    # Shown only when "tasks_tab" is active (action = tasks_tab_<action>)
    tasks_tab:
      - key: a
        action: add_task
        description: Add
        tooltip: Add a new task
        row: 0
      - key: d
        action: mark_done
        description: Done
        tooltip: Mark the selected task as done
        row: 0

    # Shown only on AddScreen (action used as-is)
    add_screen:
      - key: escape
        action: cancel
        description: Cancel
        tooltip: Cancel and close
        row: 0
"""
import re
from dataclasses import replace
from pathlib import Path

import yaml
from textual.binding import Binding, BindingType


def _sort_key(binding: Binding) -> str:
    """Turns a key like "F1" or "f1" into "f01", so f2 sorts before f10."""
    match = re.match(r"(f)(\d+)", binding.key.lower())
    if match:
        return f"{match.group(1)}{int(match.group(2)):02d}"

    return binding.key.lower()


class CustomBindings:
    """
    Manages the key bindings loaded from a YAML file.

    See the module docstring for the YAML structure and the group naming
    rules.

    Attributes
    ----------
    yaml_file_path : str
        Path to the YAML file containing key bindings.
    sort_alphabetically : bool
        Whether to sort bindings alphabetically by key.
        If false, they are sorted in the order they appear in the YAML file.
    bindings_dict_raw : dict[str, list[dict[str, str]]]
        Raw data loaded from the YAML file.
    bindings_dict : dict[str, list[Binding]]
        Processed key bindings grouped by their group name.
    action_to_groups : dict[str, list[str]]
        Maps actions to the groups they belong to.
    action_row_map : dict[str, int]
        Maps actions to their specified footer row index.
    global_actions : list[str]
        List of actions that are always shown globally.
    """

    _yaml_file_path: str
    _sort_alphabetically: bool
    _bindings_dict_raw: dict[str, list[dict[str, str]]]
    _bindings_dict: dict[str, list[Binding]]
    _action_to_groups: dict[str, list[str]]
    _action_row_map: dict[str, int]
    _global_actions: list[str]


    def __init__(self, yaml_file: str) -> None:
        """
        Reads the YAML file, keeping the order it declares.

        Use `CustomBindings.sorted_by_key` for a set sorted by key instead.
        """
        self._yaml_file_path = yaml_file
        self._sort_alphabetically = False
        self._bindings_dict = {}
        self._action_to_groups = {}
        self._action_row_map = {}
        self._global_actions = []
        self._read_yaml_file()
        self._process_bindings()

    @classmethod
    def sorted_by_key(cls, yaml_file: str) -> "CustomBindings":
        """
        Returns the bindings of the file, sorted by key within each group.

        Function keys sort numerically, so f2 comes before f10.

        Parameters
        ----------
        yaml_file : str
            Path to the YAML file containing the key bindings.

        Returns
        -------
        CustomBindings
            The loaded bindings, ordered by key rather than by file order.
        """
        bindings = cls(yaml_file)
        bindings._sort_alphabetically = True

        return bindings

    def _read_yaml_file(self) -> None:
        """Loads the binding definitions from the YAML file."""
        with Path(self._yaml_file_path).open(encoding="utf-8") as file:
            self._bindings_dict_raw = yaml.safe_load(file)

    def _process_bindings(self) -> None:
        """
        Turns the raw YAML data into `Binding` instances.

        Groups them by their group name, builds the `action_to_groups`
        mapping and records the global actions in `global_actions`.
        """
        # Loop groups
        for group, bindings in self._bindings_dict_raw.items():
            if group not in self._bindings_dict:
                self._bindings_dict[group] = []

            # Loop bindings
            for binding in bindings:
                key         = self._parse_key(binding.get("key"))
                action      = self._parse_action(binding.get("action"), group)
                description = self._parse_description(
                                  binding.get("description")
                              )
                show        = self._parse_show(binding.get("show"))
                key_display = self._parse_key_display(
                                  key, binding.get("key_display")
                              )
                priority    = self._parse_priority(binding.get("priority"))
                tooltip     = self._parse_tooltip(binding.get("tooltip"))
                binding_id  = self._parse_id(binding.get("id"))
                system      = self._parse_system(binding.get("system"))

                # Skip if any required field is missing
                if key is None or action is None or description is None:
                    continue

                binding_instance = Binding(
                    key        =key,
                    action     =action,
                    description=description,
                    show       =show,
                    key_display=key_display,
                    priority   =priority,
                    tooltip    =tooltip,
                    id         =binding_id,
                    system     =system
                )
                self._bindings_dict[group].append(binding_instance)

                # Add action to action_to_groups mapping
                if action not in self._action_to_groups:
                    self._action_to_groups[action] = [group]
                else:
                    self._action_to_groups[action].append(group)

                # Store row for this action
                self._action_row_map[action] = int(binding.get("row", 0))

                # Add action to global actions if applicable
                if group.startswith("_global"):
                    self._global_actions.append(action)


    def get_row_map(self) -> dict[str, int]:
        """
        Returns a row map for use with `MultiLineFooter(auto_wrap=False)`.

        Uses the `row` values defined in the YAML file. Pair this with
        `get_bindings`; a Screen wants `get_screen_row_map` instead.

        Returns
        -------
        dict[str, int]
            A mapping of action names to row numbers (0-based).
        """
        return dict(self._action_row_map)

    def get_screen_row_map(self) -> dict[str, int]:
        """
        Returns the row map as a Screen needs it.

        Global actions are keyed with the `app.` prefix, matching the actions
        `get_screen_bindings` produces. If the two disagree, the footer
        silently loses the row of every global binding.

        Returns
        -------
        dict[str, int]
            A mapping of action names to row numbers (0-based).
        """
        return {
            self._dispatch_name(action): row
            for action, row in self._action_row_map.items()
        }

    def get_bindings(self, tab_name: str | None = None) -> list[BindingType]:
        """
        Returns the bindings for the App itself.

        Includes every tab group, or just one when `tab_name` is given, plus
        the global bindings. Screen groups are left out; a Screen uses
        `get_screen_bindings`.

        Parameters
        ----------
        tab_name : str or None, optional
            Restricts the result to the bindings of that one tab.

        Returns
        -------
        list[BindingType]
            The bindings, globals last.
        """
        self._sort_groups_by_key()
        bindings: list[BindingType] = self._tab_bindings(tab_name)
        bindings.extend(self._global_bindings())

        return bindings

    def get_screen_bindings(
        self, screen_name: str | None = None
    ) -> list[BindingType]:
        """
        Returns the bindings for a Screen, with globals dispatched on the App.

        Without a name the tab bindings are included, which is what a screen
        holding a `TabbedContent` needs. With one, only that screen's own
        group is.

        Parameters
        ----------
        screen_name : str or None, optional
            Name of the screen, without the `_screen` suffix its group
            carries in the YAML file.

        Returns
        -------
        list[BindingType]
            The bindings, globals last and prefixed with `app.`.
        """
        self._sort_groups_by_key()

        bindings: list[BindingType] = (
            self._tab_bindings(None) if screen_name is None
            else self._screen_bindings(screen_name)
        )
        bindings.extend(self._app_dispatched_globals())

        return bindings

    def _sort_groups_by_key(self) -> None:
        """Sorts every group by key, if this instance was built that way."""
        if not self._sort_alphabetically:
            return

        for group, bindings in self._bindings_dict.items():
            self._bindings_dict[group] = sorted(bindings, key=_sort_key)

    def _tab_bindings(self, tab_name: str | None) -> list[BindingType]:
        """Returns the bindings of every tab group, or of one named tab."""
        bindings: list[BindingType] = []
        for group, group_bindings in self._bindings_dict.items():
            # Global and screen groups are appended by the callers instead
            if group.startswith("_global") or group.endswith("_screen"):
                continue
            if tab_name and group != tab_name.lower():
                continue

            bindings.extend(group_bindings)

        return bindings

    def _screen_bindings(self, screen_name: str) -> list[BindingType]:
        """Returns the bindings of one screen group."""
        group = f"{screen_name.lower()}_screen"

        return list(self._bindings_dict.get(group, []))

    def _global_bindings(self) -> list[BindingType]:
        """Returns the always-visible bindings, as they were declared."""
        bindings: list[BindingType] = []
        for group, group_bindings in self._bindings_dict.items():
            if group.startswith("_global"):
                bindings.extend(group_bindings)

        return bindings

    def _app_dispatched_globals(self) -> list[BindingType]:
        """
        Returns the global bindings with their action prefixed by `app.`.

        A Screen would otherwise look for `action_quit` on itself, find
        nothing, and the key would quietly do nothing.
        """
        return [
            replace(binding, action=f"app.{binding.action}")
            for binding in self._global_bindings()
            if isinstance(binding, Binding)
        ]

    def _dispatch_name(self, action: str) -> str:
        """Returns the name a Screen dispatches the given action under."""
        if action in self._global_actions:
            return f"app.{action}"

        return action

    def handle_check_action(
        self, action: str,
        _parameters: tuple[object, ...],
        active_group: str
    ) -> bool | None:
        """
        Checks whether an action should be shown in the active group.

        This is meant to be used in the check_action method of a Textual app.

        Parameters
        ----------
        action : str
            The action to check.
        parameters : tuple[object, ...]
            Parameters for the action (not used).
        active_group : str
            The currently active group or tab.

        Returns
        -------
        bool or None
            True if the action should be displayed, False otherwise.
        """
        # Ignore actions that are not defined in custom bindings
        if not self._is_custom_action(action):
            return True

        # Global actions are always shown
        if self._is_global_key(action):
            return True

        # Check if the action belongs to the current tab/group
        return active_group in self._action_to_groups[action]

    def _is_global_key(self, action: str) -> bool:
        """Checks if the given action belongs to a global key binding."""
        return action in self._global_actions

    def _is_custom_action(self, action: str) -> bool:
        """Returns True if the action is one the bindings declare."""
        return action in self._action_to_groups

    def _parse_key(self, key: str | None) -> str | None:
        """Parses the key field from the YAML binding definition."""
        return key

    def _parse_action(self, action: str | None, group: str) -> str | None:
        """Parses the action field, applying the group prefixing rules."""
        if action is None:
            return None
        if group.startswith("_global") or group.endswith("_screen"):
            return action
        return f"{group}_{action}"

    def _parse_description(self, description: str | None) -> str | None:
        """Parses the description field from the YAML binding definition."""
        return description

    def _parse_show(self, show: str | None) -> bool:
        """Parses the show field, defaulting to True."""
        if show is None:
            return True
        return bool(show)

    def _parse_key_display(
        self, key: str | None, key_display: str | None
    ) -> str | None:
        """
        Parses the key_display field of a binding.

        A function key such as "f1" is rendered as "F1"; otherwise the
        declared value is kept, and None leaves the rendering to Textual.
        """
        if key is None:
            return None

        match = re.fullmatch(r"(f)(\d+)", key.lower())
        if match:
            key_display = f"F{int(match.group(2))}"

        return key_display

    def _parse_priority(self, priority: str | None) -> bool:
        """Parses the priority field, defaulting to False."""
        if priority is None:
            return False
        return bool(priority)

    def _parse_tooltip(self, tooltip: str | None) -> str:
        """Parses the tooltip field, defaulting to an empty string."""
        if tooltip is None:
            return ""
        return tooltip

    def _parse_id(self, binding_id: str | None) -> str | None:
        """Parses the id field from the YAML binding definition."""
        return binding_id

    def _parse_system(self, system: str | None) -> bool:
        """
        Parses the system field, defaulting to False.

        A system binding is not overridden by a widget that captures input.
        """
        if system is None:
            return False
        return bool(system)
