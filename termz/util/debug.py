"""
termz.util.debug
================

Provides decorator-based debugging utilities for function call inspection and
performance measurement.

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

import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def print_arguments(fn: Callable[P, R]) -> Callable[P, R]:
    """
    A decorator that prints the arguments, keyword arguments, function name
    and return value each time the decorated function is called.

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
        # Print function name + args and kwargs
        print(f"Function {fn.__name__} called")
        print(f"Args: {args}")
        print(f"Kwargs: {kwargs}")

        # Call function
        fn_result = fn(*args, **kwargs)

        # Print return value of the function
        print(f"Function {fn.__name__} returns: {fn_result}")

        return fn_result

    return wrapper


def timing(use_ns_timer: bool = False) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    A decorator factory that measures the execution time of the decorated
    function.

    The time unit can be set to either seconds or nanoseconds.

    Parameters
    ----------
    use_ns_timer : bool, optional
        If True nanosecond precision timing is used.

    Returns
    -------
    Callable
        A decorator that wraps the target function with timing logic.
    """
    if use_ns_timer:
        # Use nanosecond precision timing
        time_fn = time.perf_counter_ns
        time_scale = "ns"
    else:
        # Use second precision timing
        time_fn = time.perf_counter  # type: ignore
        time_scale = "s"

    def wrap_with_timing(fn: Callable[P, R]) -> Callable[P, R]:
        """
        Wrapper function that measures and prints the execution time of the
        decorated function.

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
            print(f"Function {fn.__name__} took: {duration} {time_scale}")

            return fn_result

        return timer

    return wrap_with_timing
