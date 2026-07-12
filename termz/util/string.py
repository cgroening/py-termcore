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


def linewrap(text: str, linewidth: int):
    """
    Splits a string into multiple lines with a specified maximum width.

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
    """
    lines: list[str] = []
    while len(text) > 0:
        # Cut the maximum portion out of the given string
        maxcutpos = min(linewidth, len(text))

        # If the maximum portion doesn't end with a whitespace, cut off
        # at the last whitespace
        if len(text) > linewidth and text[maxcutpos-1] != " " \
           and text[maxcutpos] != " ":
            # Position of the last whitespace
            cutpos = max(charpos(text[0:maxcutpos-1], " "))
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


def str_with_fixed_width(text: str, width: int, align: str = "left") -> str:
    """
    Return a string truncated or padded to exactly `width` characters.

    If the text exceeds the width it is truncated with a trailing ellipsis (…).
    Supports alignment: 'left', 'right', 'center'.

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
    """
    if len(text) > width:
        if align == "right":
            return "…" + text[-(width - 1):]
        return text[:width - 1] + "…"

    if align == "left":
        return text.ljust(width)
    elif align == "right":
        return text.rjust(width)
    elif align == "center":
        return text.center(width)
    else:
        raise ValueError(f"Invalid alignment: {align}")
