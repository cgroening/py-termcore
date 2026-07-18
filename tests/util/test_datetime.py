"""Tests for the timestamp and date-string conversions.

Every test runs under a pinned TZ. These functions convert through the local
time zone by design, so without pinning it the suite would assert one thing
on this machine and another on the next.
"""

import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from termz.util.datetime import (
    date_diff,
    date_to_timestamp,
    timestamp_to_date,
    today_date,
    today_timestamp,
)

BERLIN = "Europe/Berlin"
SECONDS_PER_DAY = 86400


@pytest.fixture(autouse=True)
def pinned_timezone(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Pins the process time zone, and restores it afterwards."""
    monkeypatch.setenv("TZ", BERLIN)
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


class TestTimestampToDate:
    def test_german_format_is_the_default(self) -> None:
        timestamp = int(datetime(2026, 7, 18, 12, tzinfo=UTC).timestamp())
        assert timestamp_to_date(timestamp) == "18.07.2026"

    def test_english_format_on_request(self) -> None:
        timestamp = int(datetime(2026, 7, 18, 12, tzinfo=UTC).timestamp())
        assert timestamp_to_date(timestamp, english_format=True) \
            == "2026-07-18"

    def test_none_yields_an_empty_string(self) -> None:
        assert timestamp_to_date(None) == ""

    def test_zero_is_a_timestamp_not_a_missing_value(self) -> None:
        # Berlin is ahead of UTC, so the epoch falls on 01.01.1970 locally.
        assert timestamp_to_date(0) == "01.01.1970"

    def test_the_local_zone_decides_the_date(self) -> None:
        # 22:30 UTC is already the next day in Berlin (summer time, +02:00).
        timestamp = int(datetime(2026, 7, 18, 22, 30, tzinfo=UTC).timestamp())
        assert timestamp_to_date(timestamp) == "19.07.2026"


class TestDateToTimestamp:
    def test_returns_local_midnight(self) -> None:
        timestamp = date_to_timestamp("18.07.2026")
        assert timestamp is not None
        moment = datetime.fromtimestamp(timestamp, tz=UTC).astimezone()
        assert (moment.hour, moment.minute, moment.second) == (0, 0, 0)

    def test_english_format_on_request(self) -> None:
        assert date_to_timestamp("2026-07-18", english_format=True) \
            == date_to_timestamp("18.07.2026")

    def test_a_malformed_date_yields_none(self) -> None:
        assert date_to_timestamp("not a date") is None

    def test_an_empty_string_yields_none(self) -> None:
        assert date_to_timestamp("") is None

    def test_the_wrong_format_yields_none(self) -> None:
        assert date_to_timestamp("2026-07-18") is None


class TestRoundTrip:
    def test_a_date_survives_both_conversions(self) -> None:
        timestamp = date_to_timestamp("29.02.2024")
        assert timestamp is not None
        assert timestamp_to_date(timestamp) == "29.02.2024"

    def test_a_date_across_the_dst_switch_survives(self) -> None:
        # Berlin moves to summer time on 29.03.2026, so this local midnight
        # is the last one at +01:00.
        timestamp = date_to_timestamp("29.03.2026")
        assert timestamp is not None
        assert timestamp_to_date(timestamp) == "29.03.2026"


class TestDateDiff:
    def test_counts_whole_days(self) -> None:
        assert date_diff(10 * SECONDS_PER_DAY, 3 * SECONDS_PER_DAY) == 7

    def test_the_same_timestamp_is_zero(self) -> None:
        assert date_diff(SECONDS_PER_DAY, SECONDS_PER_DAY) == 0

    def test_a_later_second_argument_gives_a_negative_result(self) -> None:
        assert date_diff(3 * SECONDS_PER_DAY, 10 * SECONDS_PER_DAY) == -7


class TestToday:
    def test_today_timestamp_is_local_midnight(self) -> None:
        moment = datetime.fromtimestamp(today_timestamp(), tz=UTC).astimezone()
        assert (moment.hour, moment.minute, moment.second) == (0, 0, 0)

    def test_today_date_matches_the_local_calendar_day(self) -> None:
        expected = datetime.now(UTC).astimezone().strftime("%d.%m.%Y")
        assert today_date() == expected

    def test_today_date_in_english_format(self) -> None:
        expected = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
        assert today_date(english_format=True) == expected

    def test_today_timestamp_and_today_date_agree(self) -> None:
        assert timestamp_to_date(today_timestamp()) == today_date()
