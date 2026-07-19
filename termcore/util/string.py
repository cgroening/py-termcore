"""
Provides utility functions for string manipulation and formatting.

This module contains helper methods for performing common string operations.

Included Features:
- `linewrap`: Splits long text into multiple lines, respecting a maximum line
   width and avoiding word breaks when possible.
- `charpos`: Returns all positions of a given character within a string.
- `cell_width`: Counts the terminal cells a string occupies.
- `str_with_fixed_width`: Truncates or pads a string to an exact width.

These utilities are useful for simple text formatting tasks, especially when
preparing console output or working with fixed-width layouts.

Widths here are counted in terminal cells, not in code points: a CJK glyph
occupies two cells and a combining mark none. Counting characters instead is
what pushes a fixed-width column out of alignment as soon as the data is not
plain ASCII.

"""

import unicodedata
from collections.abc import Iterable

__all__ = [
    "ALIGNMENTS",
    "ALIGN_CENTER",
    "ALIGN_LEFT",
    "ALIGN_RIGHT",
    "ELLIPSIS",
    "cell_width",
    "charpos",
    "linewrap",
    "str_with_fixed_width",
]

ALIGN_LEFT = "left"
ALIGN_RIGHT = "right"
ALIGN_CENTER = "center"
ALIGNMENTS = (ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER)

ELLIPSIS = "…"


def linewrap(text: str, linewidth: int) -> str:
    r"""
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


def cell_width(text: str) -> int:
    """
    Returns the number of terminal cells the given text occupies.

    A character whose East Asian width is wide or fullwidth takes two cells,
    a combining mark takes none, everything else takes one.

    Parameters
    ----------
    text : str
        The text to measure.

    Returns
    -------
    int
        The number of cells the text occupies when rendered.

    Examples
    --------
    >>> cell_width("abc")
    3
    >>> cell_width("日本語")
    6
    """
    return sum(_char_cells(char) for char in text)


def _char_cells(char: str) -> int:
    """Returns how many terminal cells a single character occupies."""
    if unicodedata.combining(char):
        return 0

    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def str_with_fixed_width(
    text: str, width: int, align: str = ALIGN_LEFT
) -> str:
    """
    Return a string occupying exactly `width` terminal cells.

    If the text is wider it is truncated with an ellipsis (…). With
    `align="right"` the tail of the text is kept and the ellipsis marks the
    cut at the front; `align="left"` and `align="center"` keep the head,
    since there is nothing left to centre once the text has been cut.

    A double-width character cannot be split, so where one would straddle the
    boundary the result is padded with a space to reach the width exactly.

    Parameters
    ----------
    text : str
        The input text to format.
    width : int
        The exact output width in terminal cells.
    align : str
        One of 'left', 'right', or 'center'. Defaults to 'left'.

    Returns
    -------
    str
        A string occupying exactly `width` cells.

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

    if cell_width(text) > width:
        return _truncated(text, width, align)

    return _padded(text, width, align)


def _truncated(text: str, width: int, align: str) -> str:
    """Cuts the text to `width` cells, marking the cut with an ellipsis."""
    room = width - _char_cells(ELLIPSIS)

    if align == ALIGN_RIGHT:
        kept = _take_cells(reversed(text), room)[::-1]
        return _pad_left(ELLIPSIS + kept, width)

    kept = _take_cells(text, room)

    return _pad_right(kept + ELLIPSIS, width)


def _take_cells(chars: Iterable[str], room: int) -> str:
    """Takes characters while they still fit into `room` cells."""
    taken: list[str] = []
    used = 0
    for char in chars:
        cells = _char_cells(char)
        if used + cells > room:
            break
        taken.append(char)
        used += cells

    return "".join(taken)


def _padded(text: str, width: int, align: str) -> str:
    """Pads the text with spaces until it occupies `width` cells."""
    missing = width - cell_width(text)

    if align == ALIGN_LEFT:
        return text + " " * missing
    if align == ALIGN_RIGHT:
        return " " * missing + text

    left = missing // 2

    return " " * left + text + " " * (missing - left)


def _pad_right(text: str, width: int) -> str:
    """Fills up to `width` cells on the right, for a straddling glyph."""
    return text + " " * (width - cell_width(text))


def _pad_left(text: str, width: int) -> str:
    """Fills up to `width` cells on the left, for a straddling glyph."""
    return " " * (width - cell_width(text)) + text
