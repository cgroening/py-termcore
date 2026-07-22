"""
Key bindings for Textual applications, declared in YAML.

This module defines the class `CustomBindings` for managing custom keyboard
bindings in a Textual application. It loads key binding definitions from
a YAML file and exposes them as Textual `Binding` objects.

Two words carry a fixed meaning here and are not interchangeable. A *scope*
is a top-level key of the YAML file; it decides when a binding is visible and
how its action is named. A *group* is one labelled row of shortcuts inside a
scope; it decides only how the footer and the help overlay lay the bindings
out. Grouping is optional - a scope may declare bindings directly.

Reserved scope naming conventions:

- `_global`       Always-visible bindings; action is used as-is (no prefix)
- `<name>_tab`    Shown only when that tab is active; action is prefixed with
                    the full scope name, e.g. `tasks_tab_add_task`
- `<name>_screen` Screen-specific bindings; action is used as-is (no prefix)

YAML structure
--------------
The file maps scope names to lists of entries. An entry carrying `bindings`
is a group; an entry carrying `key` is a single binding. Both forms may be
mixed inside one scope, and consecutive single bindings form one unnamed
group at their position, so the file reads top to bottom like the footer.

A group supports the following fields:

  group       Label shown in front of the row; omit it for an unnamed group
  bindings    (required) The bindings of the group, in the order shown

Each binding supports the following fields:

  key         (required) Key to bind, e.g. `q`, `f1`, `ctrl+s`
  action      (required) Action name (see scope-specific prefixing below)
  description (required) Short label shown in the footer
  tooltip               Longer description shown on hover
  key_display           Override how the key is rendered in the footer
  priority              bool - show binding even when a widget captures input
  show                  bool - whether to show in the footer (default: true)
  id                    Optional binding ID
  system                bool - mark as a system binding

The order of the file is the order of the footer, without exception. Nothing
is reordered on the way out, so moving a group in the file moves its row.

Scope display names
-------------------
Scope names such as `tasks_tab` are identifiers, not labels. A second file,
passed as `scopes_file`, maps each scope to a `title` - the heading of the
help overlay, and in an app that reads it, the label of the tab - and, where
the scope is a tab, to the `key` that selects it:

.. code-block:: yaml

    tasks_tab:
      title: Tasks
      key: "1"
    add_screen:
      title: Add dialog
    _global:
      title: Global

Declaring a key is what makes a scope a tab; `get_tab_bindings` turns those
keys into working shortcuts, so the key lives in one place only. The order of
that file is the order of the tab bar.

A scope with no entry there is shown under its raw name, which is meant to
look unfinished. A title naming no scope is reported, because nothing else
would ever notice it.

Scope naming rules
------------------
`_global`
    Bindings that are always visible. The action is used as-is (no prefix),
    e.g. `action: quit` → `quit`. When included in a Screen's `BINDINGS`
    via `get_screen_bindings`, these actions are automatically prefixed with
    `app.` so Textual dispatches them on the App.

`<name>_tab`
    Tab-specific bindings, shown only when that tab is active. The action is
    prefixed with the scope name, e.g. scope `tasks_tab` + `action: add`
    → `tasks_tab_add`. Use `check_action` with the active tab name as
    `active_scope` to control visibility.

`<name>_screen`
    Screen-specific bindings. The action is used as-is (no prefix), so it maps
    directly to an `action_<name>` method on the Screen.

Example
-------
.. code-block:: yaml

    # Shown only when "tasks_tab" is active (action = tasks_tab_<action>)
    tasks_tab:
      - group: Tasks
        bindings:
          - key: a
            action: add_task
            description: Add
            tooltip: Add a new task
          - key: d
            action: mark_done
            description: Done
            tooltip: Mark the selected task as done

    # Shown only on AddScreen (action used as-is)
    add_screen:
      - key: escape
        action: cancel
        description: Cancel
        tooltip: Cancel and close

    # Always shown (action = <action>, no prefix)
    _global:
      - group: App
        bindings:
          - key: q
            action: quit
            description: Quit
            tooltip: Exit the application
            priority: true
"""
import logging
import re
from dataclasses import replace
from pathlib import Path
from typing import cast

import yaml
from textual.binding import Binding, BindingType

from termcore.tui.binding_groups import BindingGroup

__all__ = [
    "CustomBindings",
]

_logger = logging.getLogger(__name__)

_GROUP_FIELD = "group"
_BINDINGS_FIELD = "bindings"
_KEY_FIELD = "key"
_TITLE_FIELD = "title"


class CustomBindings:
    """
    Manages the key bindings loaded from a YAML file.

    See the module docstring for the YAML structure and the scope naming
    rules.

    Attributes
    ----------
    yaml_file_path : str
        Path to the YAML file containing key bindings.
    bindings_dict_raw : dict[str, list[dict[str, object]]]
        Raw data loaded from the YAML file.
    bindings_dict : dict[str, list[Binding]]
        Processed key bindings, keyed by the scope that declared them.
    groups : list[BindingGroup]
        Every declared group, in the order the file declares them.
    action_to_scopes : dict[str, list[str]]
        Maps actions to the scopes they belong to.
    scope_titles : dict[str, str]
        Maps scope names to their display names, from the scopes file.
    scope_keys : dict[str, str]
        Maps tab scopes to the key that selects them, in file order.
    global_actions : list[str]
        List of actions that are always shown globally.
    """

    _yaml_file_path: str
    _scopes_file_path: str | None
    _bindings_dict_raw: dict[str, list[dict[str, object]]]
    _bindings_dict: dict[str, list[Binding]]
    _groups: list[BindingGroup]
    _action_to_scopes: dict[str, list[str]]
    _scope_titles: dict[str, str]
    _scope_keys: dict[str, str]
    _global_actions: list[str]


    def __init__(self, yaml_file: str, scopes_file: str | None = None) -> None:
        """
        Reads the YAML file, keeping the order it declares.

        Parameters
        ----------
        yaml_file : str
            Path to the file declaring the scopes, groups and bindings.
        scopes_file : str or None, optional
            Path to a file mapping scope names to display names. Without it
            every scope is shown under its raw name.
        """
        self._yaml_file_path = yaml_file
        self._scopes_file_path = scopes_file
        self._bindings_dict = {}
        self._groups = []
        self._action_to_scopes = {}
        self._scope_titles = {}
        self._scope_keys = {}
        self._global_actions = []
        self._read_yaml_file()
        self._read_scopes_file()
        self._process_bindings()
        self._warn_about_unknown_scopes()

    def _read_yaml_file(self) -> None:
        """Loads the binding definitions from the YAML file."""
        with Path(self._yaml_file_path).open(encoding="utf-8") as file:
            self._bindings_dict_raw = yaml.safe_load(file)

    def _read_scopes_file(self) -> None:
        """Loads the scope display names and tab keys, if a file was given."""
        if self._scopes_file_path is None:
            return

        with Path(self._scopes_file_path).open(encoding="utf-8") as file:
            raw = cast("dict[str, object]", yaml.safe_load(file) or {})

        for scope, entry in raw.items():
            self._read_scope_entry(scope, entry)

    def _read_scope_entry(self, scope: str, entry: object) -> None:
        """Reads one scope's display name and, where given, its tab key."""
        if not isinstance(entry, dict):
            _logger.warning(
                "Expected a mapping for scope %r, got %r; skipping it",
                scope, entry
            )
            return

        fields = cast("dict[str, object]", entry)
        title = self._parse_text(
            fields.get(_TITLE_FIELD), field=f"title of {scope!r}"
        )
        if title is not None:
            self._scope_titles[scope] = title

        key = self._parse_text(
            fields.get(_KEY_FIELD), field=f"key of {scope!r}"
        )
        if key is not None:
            self._scope_keys[scope] = key

    def _warn_about_unknown_scopes(self) -> None:
        """
        Warns about a declared title that matches no scope.

        A title left behind by a renamed or deleted scope is invisible: the
        scope it names is simply never asked about, so the stale line sits
        there looking correct.
        """
        unknown = sorted(set(self._scope_titles) - set(self._bindings_dict))
        if unknown:
            _logger.warning(
                "Scope titles without a matching scope: %s",
                ", ".join(repr(scope) for scope in unknown)
            )

    def scope_key(self, scope: str) -> str:
        """
        Returns the key that selects a scope, or "" when it is not a tab.

        Declaring a key is what makes a scope a tab: it is the only marker,
        so `_global` and the screen scopes simply have none.

        Parameters
        ----------
        scope : str
            The scope name as the YAML file spells it.

        Returns
        -------
        str
            The declared key, or an empty string.
        """
        return self._scope_keys.get(scope, "")

    def get_tab_scopes(self) -> list[str]:
        """
        Returns the scopes that declare a key, in the order of the file.

        That order is the order of the tab bar, exactly as the order of
        `bindings.yaml` is the order of the footer.

        Returns
        -------
        list[str]
            The tab scopes, in file order.
        """
        return list(self._scope_keys)

    def get_tab_bindings(self) -> list[BindingType]:
        """
        Returns bindings that switch to each tab, built from the scopes file.

        The key lives in one place only, so the bar and the shortcut cannot
        disagree about it. They are registered with `show=False`: the header
        already prints them, and repeating them in the footer would say the
        same thing twice.

        A screen consuming these implements `action_show_tab(scope)`.

        Returns
        -------
        list[BindingType]
            One binding per tab scope, in file order.
        """
        return [
            Binding(
                key=key,
                action=f"show_tab({scope!r})",
                description=self.scope_title(scope),
                show=False,
            )
            for scope, key in self._scope_keys.items()
        ]

    def scope_title(self, scope: str) -> str:
        """
        Returns the display name of a scope.

        Parameters
        ----------
        scope : str
            The scope name as the YAML file spells it, e.g. `tasks_tab`.

        Returns
        -------
        str
            The declared title, or the scope name itself when none was
            declared. The raw name is meant to look unfinished.
        """
        return self._scope_titles.get(scope, scope)

    def _process_bindings(self) -> None:
        """
        Turns the raw YAML data into `Binding` and `BindingGroup` objects.

        Groups the bindings by their scope, builds the `action_to_scopes`
        mapping and records the global actions in `global_actions`.
        """
        for scope, entries in self._bindings_dict_raw.items():
            if scope not in self._bindings_dict:
                self._bindings_dict[scope] = []

            for name, raw_bindings in self._split_entries(scope, entries):
                self._process_group(scope, name, raw_bindings)

    def _split_entries(
        self, scope: str, entries: list[dict[str, object]]
    ) -> list[tuple[str, list[dict[str, object]]]]:
        """
        Splits a scope's entries into (group name, raw bindings) pairs.

        Consecutive bindings declared without a group become one unnamed
        group at their position, which is what keeps grouping optional
        without giving the file a second reading order.
        """
        groups: list[tuple[str, list[dict[str, object]]]] = []
        loose: list[dict[str, object]] = []

        for entry in entries:
            if _BINDINGS_FIELD in entry:
                if loose:
                    groups.append(("", loose))
                    loose = []
                groups.append((
                    self._parse_group_name(entry.get(_GROUP_FIELD)),
                    self._parse_group_bindings(entry, scope),
                ))
            elif _KEY_FIELD in entry:
                loose.append(entry)
            else:
                _logger.warning(
                    "Skipping an entry in scope %r: it declares neither %r "
                    "(a binding) nor %r (a group)",
                    scope, _KEY_FIELD, _BINDINGS_FIELD
                )

        if loose:
            groups.append(("", loose))

        return groups

    def _process_group(
        self, scope: str, name: str, raw_bindings: list[dict[str, object]]
    ) -> None:
        """Builds one group's bindings and registers their actions."""
        bindings: list[Binding] = []
        for raw in raw_bindings:
            binding = self._build_binding(raw, scope)
            if binding is None:
                continue

            bindings.append(binding)
            self._register_action(binding.action, scope)

        if not bindings:
            return

        self._bindings_dict[scope].extend(bindings)
        self._groups.append(
            BindingGroup(
                name=name,
                scope=scope,
                bindings=tuple(bindings),
                scope_title=self._scope_titles.get(scope, ""),
            )
        )

    def _build_binding(
        self, raw: dict[str, object], scope: str
    ) -> Binding | None:
        """Builds one `Binding`, or None when a required field is missing."""
        key         = self._parse_key(raw.get("key"))
        action      = self._parse_action(raw.get("action"), scope)
        description = self._parse_description(raw.get("description"))
        show        = self._parse_show(raw.get("show"))
        key_display = self._parse_key_display(key, raw.get("key_display"))
        priority    = self._parse_priority(raw.get("priority"))
        tooltip     = self._parse_tooltip(raw.get("tooltip"))
        binding_id  = self._parse_id(raw.get("id"))
        system      = self._parse_system(raw.get("system"))

        # Spelled out rather than derived from the list below, so the type
        # checker can narrow the three values for the constructor call.
        if key is None or action is None or description is None:
            missing = [
                name for name, value in (
                    ("key", key),
                    ("action", action),
                    ("description", description),
                ) if value is None
            ]
            _logger.warning(
                "Skipping a binding in scope %r: %s missing",
                scope, ", ".join(missing)
            )
            return None

        return Binding(
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

    def _register_action(self, action: str, scope: str) -> None:
        """
        Records which scopes declare an action.

        A second declaration of the same action is worth saying rather than
        doing quietly: the footer matches its rows by action, so only the
        first group that declares it renders the key.
        """
        if action in self._action_to_scopes:
            self._action_to_scopes[action].append(scope)
            _logger.warning(
                "Action %r is declared more than once (%s); only the first "
                "group renders it in the footer",
                action, ", ".join(self._action_to_scopes[action])
            )
        else:
            self._action_to_scopes[action] = [scope]

        if scope.startswith("_global"):
            self._global_actions.append(action)

    def get_groups(self) -> list[BindingGroup]:
        """
        Returns every declared group, in the order the YAML file declares it.

        Pass the result to `MultiLineFooter(groups=...)` or to `HelpScreen`.
        Groups whose bindings are not currently active render no row, so one
        call covers every screen.

        Returns
        -------
        list[BindingGroup]
            The groups, in file order.
        """
        return list(self._groups)

    def get_bindings(self, tab_name: str | None = None) -> list[BindingType]:
        """
        Returns the bindings for the App itself.

        Includes every tab scope, or just one when `tab_name` is given, plus
        the global bindings. Screen scopes are left out; a Screen uses
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
        scope is.

        Parameters
        ----------
        screen_name : str or None, optional
            Name of the screen, without the `_screen` suffix its scope
            carries in the YAML file.

        Returns
        -------
        list[BindingType]
            The bindings, globals last and prefixed with `app.`.
        """
        bindings: list[BindingType] = (
            self._tab_bindings(None) if screen_name is None
            else self._screen_bindings(screen_name)
        )
        bindings.extend(self._app_dispatched_globals())

        return bindings

    def _tab_bindings(self, tab_name: str | None) -> list[BindingType]:
        """Returns the bindings of every tab scope, or of one named tab."""
        if tab_name is not None:
            self._warn_if_unknown(tab_name.lower(), tab_name)

        bindings: list[BindingType] = []
        for scope, scope_bindings in self._bindings_dict.items():
            # Global and screen scopes are appended by the callers instead
            if scope.startswith("_global") or scope.endswith("_screen"):
                continue
            if tab_name and scope != tab_name.lower():
                continue

            bindings.extend(scope_bindings)

        return bindings

    def _screen_bindings(self, screen_name: str) -> list[BindingType]:
        """Returns the bindings of one screen scope."""
        scope = f"{screen_name.lower()}_screen"
        self._warn_if_unknown(scope, screen_name)

        return list(self._bindings_dict.get(scope, []))

    def _warn_if_unknown(self, scope: str, given_name: str) -> None:
        """
        Warns when a name matches no scope in the YAML file.

        Without this a typo is indistinguishable from a tab or screen that
        genuinely declares no shortcuts of its own.
        """
        if scope in self._bindings_dict:
            return

        _logger.warning(
            "No binding scope %r for name %r; returning only the global "
            "bindings", scope, given_name
        )

    def _global_bindings(self) -> list[BindingType]:
        """Returns the always-visible bindings, as they were declared."""
        bindings: list[BindingType] = []
        for scope, scope_bindings in self._bindings_dict.items():
            if scope.startswith("_global"):
                bindings.extend(scope_bindings)

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

    def handle_check_action(
        self, action: str,
        _parameters: tuple[object, ...],
        active_scope: str
    ) -> bool | None:
        """
        Checks whether an action should be shown in the active scope.

        This is meant to be used in the check_action method of a Textual app.

        Parameters
        ----------
        action : str
            The action to check.
        parameters : tuple[object, ...]
            Parameters for the action (not used).
        active_scope : str
            The currently active scope, such as the id of the active tab.

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

        # Check if the action belongs to the current tab/scope
        return active_scope in self._action_to_scopes[action]

    def _is_global_key(self, action: str) -> bool:
        """Checks if the given action belongs to a global key binding."""
        return action in self._global_actions

    def _is_custom_action(self, action: str) -> bool:
        """Returns True if the action is one the bindings declare."""
        return action in self._action_to_scopes

    def _parse_group_name(self, name: object) -> str:
        """Parses a group's label, defaulting to an unnamed group."""
        if name is None:
            return ""
        if isinstance(name, str):
            return name

        _logger.warning(
            "Expected a string for %r, got %r; leaving the group unnamed",
            _GROUP_FIELD, name
        )

        return ""

    def _parse_group_bindings(
        self, entry: dict[str, object], scope: str
    ) -> list[dict[str, object]]:
        """Reads a group's `bindings` list, warning when it is malformed."""
        raw = entry.get(_BINDINGS_FIELD)
        if not isinstance(raw, list):
            _logger.warning(
                "Expected a list for %r in scope %r, got %r; skipping the "
                "group", _BINDINGS_FIELD, scope, raw
            )
            return []

        bindings: list[dict[str, object]] = []
        for item in cast("list[object]", raw):
            if isinstance(item, dict):
                bindings.append(cast("dict[str, object]", item))
            else:
                _logger.warning(
                    "Skipping a binding in scope %r: expected a mapping, "
                    "got %r", scope, item
                )

        return bindings

    def _parse_key(self, key: object) -> str | None:
        """Parses the key field from the YAML binding definition."""
        return self._parse_text(key, field="key")

    def _parse_action(self, action: object, scope: str) -> str | None:
        """Parses the action field, applying the scope prefixing rules."""
        parsed = self._parse_text(action, field="action")
        if parsed is None:
            return None
        if scope.startswith("_global") or scope.endswith("_screen"):
            return parsed

        return f"{scope}_{parsed}"

    def _parse_description(self, description: object) -> str | None:
        """Parses the description field from the YAML binding definition."""
        return self._parse_text(description, field="description")

    def _parse_show(self, show: object) -> bool:
        """Parses the show field, defaulting to True."""
        return self._parse_bool(show, field="show", default=True)

    def _parse_key_display(
        self, key: str | None, key_display: object
    ) -> str | None:
        """
        Parses the key_display field of a binding.

        A declared value wins - the field exists to override how the key is
        rendered. Without one, a function key such as "f1" becomes "F1", and
        anything else returns None, which leaves the rendering to Textual.
        """
        parsed = self._parse_text(key_display, field="key_display")
        if parsed is not None:
            return parsed
        if key is None:
            return None

        match = re.fullmatch(r"(f)(\d+)", key.lower())
        if match:
            return f"F{int(match.group(2))}"

        return None

    def _parse_priority(self, priority: object) -> bool:
        """Parses the priority field, defaulting to False."""
        return self._parse_bool(priority, field="priority", default=False)

    def _parse_tooltip(self, tooltip: object) -> str:
        """Parses the tooltip field, defaulting to an empty string."""
        parsed = self._parse_text(tooltip, field="tooltip")
        if parsed is None:
            return ""

        return parsed

    def _parse_id(self, binding_id: object) -> str | None:
        """Parses the id field from the YAML binding definition."""
        return self._parse_text(binding_id, field="id")

    def _parse_system(self, system: object) -> bool:
        """
        Parses the system field, defaulting to False.

        A system binding is not overridden by a widget that captures input.
        """
        return self._parse_bool(system, field="system", default=False)

    def _parse_text(self, value: object, field: str) -> str | None:
        """
        Reads a text field, refusing a value YAML resolved to another type.

        An unquoted `off` or `no` arrives here as a boolean. Accepting it
        would render `False` as a footer label instead of failing, so the
        field is dropped with a warning naming the fix.
        """
        if value is None or isinstance(value, str):
            return value

        _logger.warning(
            "Expected text for %r, got %r; quote the value in the YAML file",
            field, value
        )

        return None

    def _parse_bool(self, value: object, field: str, *, default: bool) -> bool:
        """
        Reads a YAML boolean, falling back to the documented default.

        Only a genuine boolean counts. `bool(value)` would turn the quoted
        string "false" into True, so a quoted boolean would silently mean the
        opposite of what it says.
        """
        if value is None:
            return default
        if isinstance(value, bool):
            return value

        _logger.warning(
            "Expected true or false for %r, got %r; using the default %r",
            field, value, default
        )

        return default
