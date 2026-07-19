"""The metaclass implementing the singleton pattern."""

from typing import Any, cast

__all__ = [
    "Singleton",
]

# Keyed by class, so that two classes using this metaclass keep their own
# instance. Holding the registry here rather than on the metaclass is also
# what lets __call__ report the constructed class as its return type.
_instances: dict[type, object] = {}


class Singleton(type):
    """
    Metaclass for the singleton pattern.

    Ensures that a class has only one instance and provides global access
    to it.

    Examples
    --------
    >>> class SomeClass(metaclass=Singleton):
    ...     pass
    >>> SomeClass() is SomeClass()
    True
    """

    def __call__[T](cls: type[T], *args: Any, **kwargs: Any) -> T:  # noqa: ANN401
        """
        Returns the one instance, building it on the first call.

        The arguments are whatever the class itself takes, which is what Any
        says here. The return type is the class, so that a consumer sees the
        type it asked for instead of `object`.
        """
        if cls not in _instances:
            _instances[cls] = super().__call__(*args, **kwargs)  # pyright: ignore[reportAny]

        return cast("T", _instances[cls])

    @property
    def instance(cls) -> object | None:
        """Returns the single instance, or None before it was built."""
        return _instances.get(cls)
