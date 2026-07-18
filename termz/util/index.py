"""
termz.util.index
================

Index arithmetic for navigating lists, in particular the cyclic movement
selection lists in a terminal user interface are expected to have.

"""


def next_index(
    current_index: int,
    length: int,
    direction: int = 1,
    loop_behavior: bool = True
) -> int:
    """
    Calculates the next index in a list based on the current index,
    the length of the list and the direction of movement.

    Parameters
    ----------
    current_index : int
        The current index in the list.
    length : int
        The number of items in the list.
    direction : int, optional
        The direction and size of the movement (1 for one step forward,
        -1 for one step backward).
    loop_behavior : bool, optional
        If True, the index will wrap around when reaching
        the start or end of the list. If False, the index will be
        clamped within the bounds of the list.

    Returns
    -------
    int
        The calculated next index. An empty list always yields 0.

    Notes
    -----
    When `loop_behavior` is `True`, the expression
    `(current_index + direction) % length` ensures that the index
    always stays within the valid range from `0` to `length - 1`.
    The modulo operator (%) makes the index "wrap around":

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

    Without wrapping the index stops at the bounds:

    >>> next_index(4, 5, loop_behavior=False)
    4
    >>> next_index(0, 5, direction=-1, loop_behavior=False)
    0

    An empty list has no valid index, so 0 is returned:

    >>> next_index(0, 0)
    0
    """
    # An empty list has no index to move to - and % 0 would raise
    if length <= 0:
        return 0

    if loop_behavior:
        return (current_index + direction) % length

    return max(0, min(current_index + direction, length - 1))
