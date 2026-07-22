"""
Shortcut groups shared by the footer and the help overlay.

A `BindingGroup` is one labelled row of shortcuts: the bindings a YAML file
declares under one `group:` entry, in the order it declares them. Both the
footer and the help overlay render from this one structure, so a change to
the grouping reaches both without either of them knowing about the other.

A group is identified by the pair of its scope and its name. The same name
declared under two scopes stays two groups, so that every rendered row has
exactly one source.
"""
from dataclasses import dataclass

from textual.binding import Binding
from textual.screen import Screen

__all__ = [
    "APP_PREFIX",
    "BindingGroup",
    "active_actions",
    "dispatch_name",
]

APP_PREFIX = "app."


@dataclass(frozen=True, slots=True)
class BindingGroup:
    """
    One labelled row of shortcuts.

    Attributes
    ----------
    name : str
        The label shown in front of the row, or an empty string when the
        bindings were declared without a group.
    scope : str
        The YAML scope the bindings came from, such as `_global` or
        `tasks_tab`. Part of the group's identity, not decoration.
    bindings : tuple[Binding, ...]
        The bindings of this group, in the order the file declares them.
    """

    name: str
    scope: str
    bindings: tuple[Binding, ...]


def dispatch_name(action: str) -> str:
    """
    Returns an action name without the prefix a Screen dispatches it under.

    Global bindings reach a Screen as `app.quit` so that Textual dispatches
    them on the App. Anything matching bindings by action has to compare the
    bare name, or every global binding silently fails to match.

    Parameters
    ----------
    action : str
        An action name, with or without the `app.` prefix.

    Returns
    -------
    str
        The action name without the prefix.

    Examples
    --------
    >>> dispatch_name("app.quit")
    'quit'
    >>> dispatch_name("tasks_tab_add_task")
    'tasks_tab_add_task'
    """
    return action.removeprefix(APP_PREFIX)


def active_actions(screen: Screen[object]) -> frozenset[str]:
    """
    Returns the actions currently bound on the given screen.

    Names are returned without the `app.` prefix, so they can be compared
    against what `BindingGroup` holds. Use it to snapshot the context before
    opening a modal - once the modal is pushed, the active bindings are the
    modal's own.

    Parameters
    ----------
    screen : Screen[object]
        The screen to read the active bindings from.

    Returns
    -------
    frozenset[str]
        The bare action names that are currently bound.
    """
    active = screen.active_bindings.values()

    return frozenset(
        dispatch_name(binding.action)
        for _node, binding, _enabled, _tooltip in active
    )
