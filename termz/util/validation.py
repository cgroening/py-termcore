"""Small predicates for validating loosely typed input."""

def is_number(value: int | float | str | None) -> bool:
    """
    Returns True if the given value can be read as a number.

    Parameters
    ----------
    value : int or float or str or None
        The value to check.

    Returns
    -------
    bool
        True if `float()` accepts the value, False otherwise.
    """
    if value is None:
        return False

    try:
        float(value)
    except ValueError:
        return False
    else:
        return True
