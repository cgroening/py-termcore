"""Tests for the string formatting helpers.

`str_with_fixed_width` promises exactly `width` terminal cells, which is the
whole reason it exists - a fixed-width column that is not fixed-width breaks
the layout it was meant to hold together. Most of the tests below are that
one promise, checked at the boundaries where it used to break.

Cells, not characters: one CJK glyph occupies two of them, and counting code
points is what pushed such a column out of alignment.
"""

import pytest

from termz.util.string import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    cell_width,
    charpos,
    linewrap,
    str_with_fixed_width,
)


class TestCharpos:
    def test_finds_every_occurrence(self) -> None:
        assert charpos("a b c", " ") == [1, 3]

    def test_returns_empty_when_absent(self) -> None:
        assert charpos("abc", " ") == []

    def test_returns_empty_for_empty_text(self) -> None:
        assert charpos("", " ") == []

    def test_a_multi_character_needle_never_matches(self) -> None:
        # It compares against single characters, so this cannot match.
        assert charpos("abab", "ab") == []


class TestLinewrap:
    def test_short_text_is_returned_unchanged(self) -> None:
        assert linewrap("short", 20) == "short"

    def test_empty_text_stays_empty(self) -> None:
        assert linewrap("", 5) == ""

    def test_breaks_at_spaces(self) -> None:
        assert linewrap("the quick brown fox jumps", 10) \
            == "the quick\nbrown fox\njumps"

    def test_no_line_exceeds_the_width(self) -> None:
        text = "the quick brown fox jumps over the lazy dog"
        for line in linewrap(text, 12).split("\n"):
            assert len(line) <= 12

    def test_a_word_longer_than_the_line_is_broken(self) -> None:
        # Used to raise ValueError, because max() ran on an empty list
        # whenever the first `linewidth` characters held no space at all.
        assert linewrap("abcdefghij", 5) == "abcde\nfghij"

    def test_a_leading_space_does_not_stall_the_loop(self) -> None:
        # The break position would be 0 here, leaving the text unconsumed.
        assert linewrap(" abcdefgh", 5) == "abcd\nefgh"

    def test_a_width_below_one_is_refused(self) -> None:
        # No progress per iteration is possible, so this used to hang.
        with pytest.raises(ValueError):
            linewrap("anything", 0)


class TestCellWidth:
    def test_ascii_is_one_cell_each(self) -> None:
        assert cell_width("abc") == 3

    def test_cjk_is_two_cells_each(self) -> None:
        assert cell_width("日本語") == 6

    def test_emoji_are_two_cells(self) -> None:
        assert cell_width("🎉") == 2

    def test_a_combining_mark_adds_nothing(self) -> None:
        # "e" plus a combining acute renders as one cell, not two.
        assert cell_width("e\u0301") == 1

    def test_empty_text_is_zero(self) -> None:
        assert cell_width("") == 0

    def test_mixed_text_adds_up(self) -> None:
        assert cell_width("ab日") == 4


class TestFixedWidthAlwaysReturnsTheRequestedWidth:
    def test_every_combination_of_length_and_alignment(self) -> None:
        texts = ("", "a", "ab", "abcdef", "abcdefghijklmnop",
                 "日", "日本", "日本語テキスト", "a日b語c", "🎉🎉🎉")
        for text in texts:
            for width in range(8):
                for align in (ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER):
                    result = str_with_fixed_width(text, width, align)
                    assert cell_width(result) == width, (
                        f"{text!r}, {width}, {align} -> {result!r}"
                    )


class TestFixedWidthTruncation:
    def test_left_keeps_the_head(self) -> None:
        assert str_with_fixed_width("abcdef", 4) == "abc…"

    def test_right_keeps_the_tail(self) -> None:
        assert str_with_fixed_width("abcdef", 4, ALIGN_RIGHT) == "…def"

    def test_center_keeps_the_head(self) -> None:
        # Nothing left to centre once the text has been cut.
        assert str_with_fixed_width("abcdef", 4, ALIGN_CENTER) == "abc…"

    def test_width_one_left_is_just_the_ellipsis(self) -> None:
        assert str_with_fixed_width("abcdef", 1) == "…"

    def test_width_one_right_is_just_the_ellipsis(self) -> None:
        # text[-(width - 1):] became text[-0:], which is the whole string,
        # so this used to return "…abcdef" - seven characters for a width
        # of one.
        assert str_with_fixed_width("abcdef", 1, ALIGN_RIGHT) == "…"

    def test_width_zero_is_empty(self) -> None:
        assert str_with_fixed_width("abcdef", 0) == ""

    def test_text_of_exactly_the_width_is_untouched(self) -> None:
        assert str_with_fixed_width("abcdef", 6) == "abcdef"


class TestFixedWidthPadding:
    def test_left_pads_on_the_right(self) -> None:
        assert str_with_fixed_width("ab", 5) == "ab   "

    def test_right_pads_on_the_left(self) -> None:
        assert str_with_fixed_width("ab", 5, ALIGN_RIGHT) == "   ab"

    def test_center_pads_on_both_sides(self) -> None:
        assert str_with_fixed_width("ab", 6, ALIGN_CENTER) == "  ab  "

    def test_empty_text_becomes_all_padding(self) -> None:
        assert str_with_fixed_width("", 3) == "   "


class TestFixedWidthRejectsBadArguments:
    def test_an_unknown_alignment_is_refused_when_padding(self) -> None:
        with pytest.raises(ValueError):
            str_with_fixed_width("ab", 5, "bogus")

    def test_an_unknown_alignment_is_refused_when_truncating(self) -> None:
        # The alignment used to be validated only on the padding path, so
        # whether a typo raised depended on how long the text happened to be.
        with pytest.raises(ValueError):
            str_with_fixed_width("abcdef", 3, "bogus")

    def test_a_negative_width_is_refused(self) -> None:
        with pytest.raises(ValueError):
            str_with_fixed_width("ab", -1)


class TestFixedWidthCountsCells:
    """A column of CJK text has to line up with a column of ASCII."""

    def test_wide_text_is_truncated_by_cells(self) -> None:
        # Three glyphs are six cells, so only two fit beside the ellipsis.
        assert str_with_fixed_width("日本語", 5) == "日本…"

    def test_wide_text_is_padded_by_cells(self) -> None:
        assert str_with_fixed_width("日本", 6) == "日本  "

    def test_a_straddling_glyph_is_not_split(self) -> None:
        # One cell is left beside the ellipsis and a glyph needs two, so the
        # result is padded to reach the width exactly.
        result = str_with_fixed_width("日本", 2)

        assert cell_width(result) == 2
        assert "日" not in result

    def test_ascii_and_cjk_columns_line_up(self) -> None:
        column = [
            str_with_fixed_width(value, 10)
            for value in ("plain", "日本語", "a日b", "")
        ]

        assert {cell_width(cell) for cell in column} == {10}
