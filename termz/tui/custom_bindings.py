"""
termz.tui.custom_bindings
=========================

Module for managing custom key bindings in Textual applications using
YAML configuration.

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
  priority              bool – show binding even when a widget captures input
  show                  bool – whether to show in the footer (default: true)
  id                    Optional binding ID
  system                bool – mark as a system binding

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
import yaml
from textual.binding import Binding, BindingType


class CustomBindings():
    """
    Singleton class to manage custom key bindings loaded from a YAML file for
    use in a Textual application. See module docstring for details on
    YAML structure and usage.

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


    def __init__(
        self,
        yaml_file: str,
        sort_alphabetically: bool = False,
    ) -> None:
        """
        Reads the YAML file and processes the bindings into a structured format.
        """
        self._yaml_file_path = yaml_file
        self._sort_alphabetically = sort_alphabetically
        self._bindings_dict = {}
        self._action_to_groups = {}
        self._action_row_map = {}
        self._global_actions = []
        self._read_yaml_file()
        self._process_bindings()

    def _read_yaml_file(self):
        """
        Loads the binding definitions from the YAML file into a dictionary.
        """
        with open(self._yaml_file_path, "r", encoding="utf-8") as file:
            self._bindings_dict_raw = yaml.safe_load(file)

    def _process_bindings(self):
        """
        Processes the raw data from the YAML file into a structured format
        suitable for use in the Textual application. It converts each binding
        into a `Binding` instance and organizes them by their group name.
        Also builds the `action_to_groups` mapping and stores the name of
        global actions in `global_actions`.
        """
        # Loop groups
        for group, bindings in self._bindings_dict_raw.items():
            if group not in self._bindings_dict:
                self._bindings_dict[group] = []

            # Loop bindings
            for binding in bindings:
                key         = self._parse_key(binding.get("key"))
                action      = self._parse_action(binding.get("action"), group)
                description = self._parse_description(binding.get("description"))
                show        = self._parse_show(binding.get("show"))
                key_display = self._parse_key_display(
                                  key, binding.get("key_display")
                              )
                priority    = self._parse_priority(binding.get("priority"))
                tooltip     = self._parse_tooltip(binding.get("tooltip"))
                id          = self._parse_id(binding.get("id"))
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
                    id         =id,
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

        # logging.debug(f'Bindings: {pprint.pformat(self.bindings_dict)}')

    def get_row_map(
        self, for_screen: bool = False, screen_name: str | None = None
    ) -> dict[str, int]:
        """
        Returns a row map for use with `MultiLineFooter(auto_wrap=False)`,
        using the `row` values defined in the YAML file.

        When `for_screen=True` or `screen_name` is given, global action
        keys are prefixed with `app.` to match the binding actions produced
        by `get_bindings(for_screen=True)`.

        Returns
        -------
        dict[str, int]
            A mapping of action names to row numbers (0-based).
        """
        use_app_prefix = for_screen or bool(screen_name)
        row_map: dict[str, int] = {}
        for action, row in self._action_row_map.items():
            key = f"app.{action}" if use_app_prefix and action in self._global_actions else action
            row_map[key] = row
        return row_map

    def get_bindings(
        self, tab_name: str | None = None, screen_name: str | None = None,
        for_screen: bool = False
    ) -> list[BindingType]:
        """
        Returns a list (sorted by key if `self.sort_alphabetically` is `True`)
        of all bindings across all groups.

        If `tab_name` or `screen_name` is provided, only bindings for that
        specific tab/screen are returned. Otherwise, bindings from all groups
        - except tab/ screen-specific ones (beginning with '_screen_') -
        are included.

        Parameters
        ----------
        tab_name : str or None, optional
            Optional name of the tab for which to get bindings.
        screen_name : str or None, optional
            Optional name of the screen for which to get bindings.

        Returns
        -------
        list[BindingType]
            A list of `Binding` instances sorted by their key.
        """
        def get_sort_key(binding: Binding):
            """Transforms a key like "F1" or "f1" to "f01" for sorting."""
            match = re.match(r"(f)(\d+)", binding.key.lower())
            if match:
                return f"{match.group(1)}{int(match.group(2)):02d}"
            return binding.key.lower()

        # Sort each group of bindings by their key
        if self._sort_alphabetically:
            for group, bindings in self._bindings_dict.items():
                self._bindings_dict[group] = sorted(bindings, key=get_sort_key)

        # Collect global bindings (non-destructive)
        global_groups = [g for g in self._bindings_dict if g.startswith("_global")]
        global_bindings: list[BindingType] = []
        for g in global_groups:
            global_bindings.extend(self._bindings_dict.get(g, []))

        # Combine all bindings into a single list - excluding global and screen ones
        bindings_list: list[BindingType] = []
        for group, bindings in self._bindings_dict.items():
            # Always skip global and screen groups in the main loop
            if group.startswith("_global") or group.endswith("_screen"):
                continue
            # If a tab name is given, only include bindings for that tab
            if tab_name:
                if group != tab_name.lower():
                    continue
            # If a screen name is given, skip all tab bindings
            elif screen_name:
                continue

            bindings_list.extend(bindings)

        # Append screen-specific bindings when screen_name is given
        if screen_name:
            screen_group = f"{screen_name.lower()}_screen"
            bindings_list.extend(self._bindings_dict.get(screen_group, []))

        # Append global bindings, prefixed with 'app.' for screen context
        if screen_name or for_screen:
            global_bindings = [
                Binding(
                    key=b.key,
                    action=f"app.{b.action}",
                    description=b.description,
                    show=b.show,
                    key_display=b.key_display,
                    priority=b.priority,
                    tooltip=b.tooltip,
                    id=b.id,
                    system=b.system,
                )
                for b in global_bindings if isinstance(b, Binding)
            ]
        bindings_list.extend(global_bindings)

        # logging.debug(f'All bindings: {pprint.pformat(self.bindings_dict)}')
        # logging.debug(f'Return value: {pprint.pformat(bindings_list)}')

        return bindings_list

    def handle_check_action(
        self, action: str,
        _parameters: tuple[object, ...],
        active_group: str
    ) -> bool | None:
        """
        Checks if a given action should be displayed based on the current
        active group.

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
        # logging.debug(
        #     f'Checking action "{action}" for active group "{active_group}"'
        # )
        if active_group in self._action_to_groups[action]:
            return True

        return False

    def _is_global_key(self, action: str) -> bool:
        """Checks if the given action belongs to a global key binding."""
        return action in self._global_actions

    def _is_custom_action(self, action: str) -> bool:
        """
        Returns true if the given action is a custom action defined in
        the bindings.
        """
        return action in self._action_to_groups

    def _parse_key(self, key: str | None) -> str | None:
        """Parses the key field from the YAML binding definition."""
        return key

    def _parse_action(self, action: str | None, group: str) -> str | None:
        """
        Parses the action field from the YAML binding definition, applying
        group-specific prefixing rules.
        """
        if action is None:
            return None
        if group.startswith("_global") or group.endswith("_screen"):
            return action
        return f"{group}_{action}"

    def _parse_description(self, description: str | None) -> str | None:
        """Parses the description field from the YAML binding definition."""
        return description

    def _parse_show(self, show: str | None) -> bool:
        """
        Parses the show field from the YAML binding definition, defaulting
        to True.
        """
        if show is None:
            return True
        else:
            return bool(show)

    def _parse_key_display(
        self, key: str | None, key_display: str | None
    ) -> str | None:
        """
        Parses the key_display field from the YAML binding definition. For
        function keys (e.g. "f1") it formats them as "F1"; otherwise the
        declared value is kept, and None leaves the rendering to Textual.
        """
        if key is None:
            return None

        match = re.fullmatch(r"(f)(\d+)", key.lower())
        if match:
            key_display = f"F{int(match.group(2))}"

        return key_display

    def _parse_priority(self, priority: str | None) -> bool:
        """
        Parses the priority field from the YAML binding definition, defaulting
        to False.
        """
        if priority is None:
            return False
        else:
            return bool(priority)

    def _parse_tooltip(self, tooltip: str | None) -> str:
        """
        Parses the tooltip field from the YAML binding definition, defaulting to
        an empty string.
        """
        if tooltip is None:
            return ""
        else:
            return tooltip

    def _parse_id(self, id: str | None) -> str | None:
        """Parses the id field from the YAML binding definition."""
        if id is None:
            return None
        else:
            return id

    def _parse_system(self, system: str | None) -> bool:
        """
        Parses the system field from the YAML binding definition, defaulting to
        False. System bindings are marked as such to prevent them from being
        overridden by widgets that capture input.
        """
        if system is None:
            return False
        else:
            return bool(system)
