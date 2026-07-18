"""
termz.util.string
=================

Provides utility functions for string manipulation and formatting.

This module contains helper methods for performing common string operations.

Included Features:
- `linewrap`: Splits long text into multiple lines, respecting a maximum line
   width and avoiding word breaks when possible.
- `charpos`: Returns all positions of a given character within a string.
- `str_with_fixed_width`: Truncates or pads a string to an exact width.

These utilities are useful for simple text formatting tasks, especially when
preparing console output or working with fixed-width layouts.

"""

ALIGN_LEFT = "left"
ALIGN_RIGHT = "right"
ALIGN_CENTER = "center"
ALIGNMENTS = (ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER)

ELLIPSIS = "…"


def linewrap(text: str, linewidth: int) -> str:
    """
    Splits a string into multiple lines with a specified maximum width.

    Words are kept intact where possible. A word longer than `linewidth` has
    nothing to break at and is cut at the width instead.

    Parameters
    ----------
    text : str
        The input text to be split into lines.
    linewidth : int
        Maximum number of characters allowed per line.

    Returns
    -------
    str
        A string with lines separated by line breaks (\n).

    Raises
    ------
    ValueError
        If `linewidth` is smaller than 1. No progress could be made per
        iteration, so the text would never be consumed.
    """
    if linewidth < 1:
        raise ValueError(f"linewidth must be at least 1, got {linewidth}")

    lines: list[str] = []
    while len(text) > 0:
        # Cut the maximum portion out of the given string
        maxcutpos = min(linewidth, len(text))

        # If the maximum portion doesn't end with a whitespace, cut off
        # at the last whitespace
        if len(text) > linewidth and text[maxcutpos-1] != " " \
           and text[maxcutpos] != " ":
            cutpos = _last_space_position(text[0:maxcutpos-1], maxcutpos)
        else:
            cutpos = maxcutpos

        # Set snippet for this line and remove it from given text
        line = text[0:cutpos].strip()
        text = text[cutpos:len(text)]

        # Add line break if it's not the last line of the text
        if maxcutpos == linewidth and len(text[0:linewidth].strip()) > 0:
            line += "\n"

        lines.append(line)

    return "".join(lines)


def _last_space_position(text: str, fallback: int) -> int:
    """
    Returns the position to break at, or `fallback` if there is no useful one.

    A word longer than the line has no space to break at, and a leading space
    would give position 0 - both would leave the text unchanged and loop
    forever, so the caller's hard cut is used instead.
    """
    space_positions = charpos(text, " ")
    if not space_positions or max(space_positions) < 1:
        return fallback
    return max(space_positions)


def charpos(text: str, char: str) -> list[int]:
    """
    Finds all positions of a specific character in a string.

    Parameters
    ----------
    text : str
        The input text to search in.
    char : str
        The character to search for.

    Returns
    -------
    list[int]
        A list of indices where the character occurs in the text.
    """
    return [pos for pos, c in enumerate(text) if c == char]


def str_with_fixed_width(
    text: str, width: int, align: str = ALIGN_LEFT
) -> str:
    """
    Return a string truncated or padded to exactly `width` characters.

    If the text exceeds the width it is truncated with an ellipsis (…). With
    `align="right"` the tail of the text is kept and the ellipsis marks the
    cut at the front; `align="left"` and `align="center"` keep the head, since
    there is nothing left to centre once the text has been cut.

    The width is counted in characters, not in terminal cells. Text
    containing full-width characters therefore renders wider than `width`.

    Parameters
    ----------
    text : str
        The input text to format.
    width : int
        The exact output width in characters.
    align : str
        One of 'left', 'right', or 'center'. Defaults to 'left'.

    Returns
    -------
    str
        A string of exactly `width` characters.

    Raises
    ------
    ValueError
        If `align` is not one of the supported alignments, or if `width` is
        negative.
    """
    if align not in ALIGNMENTS:
        raise ValueError(f"Invalid alignment: {align}")
    if width < 0:
        raise ValueError(f"width must not be negative, got {width}")
    if width == 0:
        return ""

    if len(text) > width:
        if align == ALIGN_RIGHT:
            # Sliced from len(text) rather than with a negative index:
            # at width 1 the offset is 0, and text[-0:] is the whole string.
            return ELLIPSIS + text[len(text) - (width - 1):]
        return text[:width - 1] + ELLIPSIS

    if align == ALIGN_LEFT:
        return text.ljust(width)
    if align == ALIGN_RIGHT:
        return text.rjust(width)
    return text.center(width)
