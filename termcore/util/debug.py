"""
Decorators for inspecting calls and measuring execution time.

This module offers decorators that can be used to:

- Log function calls, including arguments, keyword arguments and return values.
- Measure and display execution time of functions, with optional nanosecond
precision.

These utilities are useful for tracking function behavior and identifying
performance bottlenecks during runtime, without requiring changes to the
function logic itself.

Examples
--------
Printing arguments
~~~~~~~~~~~~~~~~~~

>>> @print_arguments
... def do_something(t: str, n: int) -> None:
...     print(f'I am not doing anything with string "{t}" and number {str(n)}.')
...
>>> do_something('ABC', 11)

Measuring execution time of a function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

>>> @timing()
... def iterate_something() -> None:
...     v: int = 0
...     for i in range(10**7):
...         v += 1
...
>>> iterate_something()

"""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

__all__ = [
    "print_arguments",
    "timing",
    "timing_ns",
]

_logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def print_arguments[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """
    Logs name, arguments and return value on every call.

    Parameters
    ----------
    fn : Callable
        The function to be decorated.

    Returns
    -------
    Callable
        A wrapper function that adds debugging output.
    """
    @wraps(fn)  # Without this fn.__name__ would be empty
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        """
        Wrapper function that prints the function's arguments and return value.

        Parameters
        ----------
        *args : P.args
            Positional arguments.
        **kwargs : P.kwargs
            Keyword arguments.

        Returns
        -------
        R
            The original return value of the decorated function.
        """
        # Report the call through the logger, so a consumer can filter
        # or silence it like any other diagnostic
        _logger.debug("Function %s called", fn.__name__)
        _logger.debug("Args: %r", args)
        _logger.debug("Kwargs: %r", kwargs)

        # Call function
        fn_result = fn(*args, **kwargs)

        _logger.debug(
            "Function %s returns: %r", fn.__name__, fn_result
        )

        return fn_result

    return wrapper


def timing() -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    A decorator factory that measures the execution time in seconds.

    Returns
    -------
    Callable
        A decorator that wraps the target function with timing logic.
    """
    return _timing(time.perf_counter, "s")


def timing_ns() -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    A decorator factory that measures the execution time in nanoseconds.

    Returns
    -------
    Callable
        A decorator that wraps the target function with timing logic.
    """
    return _timing(time.perf_counter_ns, "ns")


def _timing(
    time_fn: Callable[[], float], time_scale: str
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Builds the timing decorator around the given clock.

    Parameters
    ----------
    time_fn : Callable
        The clock to read, in the unit `time_scale` names.
    time_scale : str
        Unit suffix written to the log.

    Returns
    -------
    Callable
        A decorator that wraps the target function with timing logic.
    """
    def wrap_with_timing(fn: Callable[P, R]) -> Callable[P, R]:
        """
        Wraps the function so its execution time is measured.

        Parameters
        ----------
        fn : Callable
            Reference to the function.

        Returns
        -------
        Callable
            A wrapped version of the function with timing logic.
        """
        @wraps(fn)
        def timer(*args: P.args, **kwargs: P.kwargs) -> R:
            """
            Measures the execution time of the function call.

            Parameters
            ----------
            *args : P.args
                Positional arguments.
            **kwargs : P.kwargs
                Keyword arguments.

            Returns
            -------
            R
                The original return value of the decorated function.
            """
            # Store start time
            start_time = time_fn()

            # Call function
            fn_result = fn(*args, **kwargs)

            # Store end time + calculate and print execution time
            end_time = time_fn()
            duration = end_time - start_time
            _logger.debug(
                "Function %s took: %s %s",
                fn.__name__, duration, time_scale
            )

            return fn_result

        return timer

    return wrap_with_timing
