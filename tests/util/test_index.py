"""Tests for the index arithmetic behind cyclic list navigation."""

from termz.util.index import next_index


class TestCyclicMovement:
    def test_forward_wraps_at_the_end(self) -> None:
        assert next_index(4, 5) == 0

    def test_backward_wraps_at_the_start(self) -> None:
        assert next_index(0, 5, direction=-1) == 4

    def test_forward_within_the_list(self) -> None:
        assert next_index(2, 5) == 3

    def test_backward_within_the_list(self) -> None:
        assert next_index(2, 5, direction=-1) == 1

    def test_a_step_larger_than_one_wraps_too(self) -> None:
        assert next_index(3, 5, direction=4) == 2

    def test_a_full_turn_returns_to_the_start(self) -> None:
        assert next_index(2, 5, direction=5) == 2

    def test_a_single_item_list_stays_on_its_only_index(self) -> None:
        assert next_index(0, 1) == 0


class TestClampedMovement:
    def test_stops_at_the_end(self) -> None:
        assert next_index(4, 5, loop_behavior=False) == 4

    def test_stops_at_the_start(self) -> None:
        assert next_index(0, 5, direction=-1, loop_behavior=False) == 0

    def test_moves_within_the_list(self) -> None:
        assert next_index(2, 5, loop_behavior=False) == 3

    def test_honours_the_step_size(self) -> None:
        # Used to hard-code a single step here while the looping branch
        # honoured `direction`, so the two disagreed for any larger step.
        assert next_index(0, 10, direction=5, loop_behavior=False) == 5

    def test_a_step_past_the_end_is_clamped(self) -> None:
        assert next_index(8, 10, direction=5, loop_behavior=False) == 9

    def test_a_step_past_the_start_is_clamped(self) -> None:
        assert next_index(1, 10, direction=-5, loop_behavior=False) == 0


class TestEmptyList:
    """Style guide 1.6: an empty list yields index 0.

    This used to raise ZeroDivisionError from the modulo, which meant every
    caller had to guard the empty case itself.
    """

    def test_looping_yields_zero(self) -> None:
        assert next_index(0, 0) == 0

    def test_clamped_yields_zero(self) -> None:
        assert next_index(0, 0, loop_behavior=False) == 0

    def test_backward_yields_zero(self) -> None:
        assert next_index(0, 0, direction=-1) == 0
