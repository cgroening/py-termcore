"""
Index arithmetic for navigating lists.

In particular the cyclic movement selection lists in a terminal user
interface are expected to have.

Two functions rather than one with a switch: `next_index` wraps around at
both ends, `clamped_index` stops at them. Which one a view wants is a
property of that view, and naming it at the call site says so.

"""



__all__ = [
    "clamped_index",
    "next_index",
]


def next_index(current_index: int, length: int, direction: int = 1) -> int:
    """
    Calculates the next index in a list, wrapping around at both ends.

    Parameters
    ----------
    current_index : int
        The current index in the list.
    length : int
        The number of items in the list.
    direction : int, optional
        The direction and size of the movement (1 for one step forward,
        -1 for one step backward).

    Returns
    -------
    int
        The calculated next index. An empty list always yields 0.

    Notes
    -----
    The expression `(current_index + direction) % length` keeps the index
    within the valid range from `0` to `length - 1`. The modulo operator
    makes it "wrap around":

        - If the index moves past the end of the list, it wraps back
          to 0.
        - If the index moves before the beginning, it wraps to the
          last position.

    Examples
    --------
    For a list of length 5 (indices 0 to 4):

    >>> next_index(4, 5)  # moves from the end to the start
    0
    >>> next_index(0, 5, direction=-1)  # moves from the start to the end
    4
    >>> next_index(2, 5)  # normal forward movement
    3
    >>> next_index(2, 5, direction=-1)  # normal backward movement
    1

    An empty list has no valid index, so 0 is returned:

    >>> next_index(0, 0)
    0
    """
    # An empty list has no index to move to - and % 0 would raise
    if length <= 0:
        return 0

    return (current_index + direction) % length


def clamped_index(current_index: int, length: int, direction: int = 1) -> int:
    """
    Calculates the next index in a list, stopping at both ends.

    Parameters
    ----------
    current_index : int
        The current index in the list.
    length : int
        The number of items in the list.
    direction : int, optional
        The direction and size of the movement (1 for one step forward,
        -1 for one step backward).

    Returns
    -------
    int
        The calculated next index, never outside the list. An empty list
        always yields 0.

    Examples
    --------
    For a list of length 5 (indices 0 to 4):

    >>> clamped_index(4, 5)  # already at the end, stays there
    4
    >>> clamped_index(0, 5, direction=-1)  # already at the start
    0
    >>> clamped_index(2, 5)  # normal forward movement
    3
    >>> clamped_index(0, 5, direction=10)  # a step past the end is clamped
    4
    """
    if length <= 0:
        return 0

    return max(0, min(current_index + direction, length - 1))
