"""
termz.util.datetime
===================

Provides utility functions for converting and working with UNIX timestamps
and date strings.

This module offers convenient static methods for working with dates and times,
including:

- Converting UNIX timestamps to formatted date strings and vice versa.
- Calculating the number of days between two timestamps.
- Retrieving today's date or timestamp at midnight.

It supports both German-style date formatting ("DD.MM.YYYY") and English-style
formatting ("YYYY-MM-DD") for flexibility in various locales.

Every conversion is anchored in the machine's local time zone, and says so:
the datetimes built here carry their offset instead of leaving it implied. A
naive timestamp changes meaning with the daylight saving switch, with the
machine and on serialisation, and the error surfaces months later in wrongly
sorted or wrongly calculated data rather than at the call site.

"""

from datetime import UTC, datetime, time

# Without this, `from .datetime import *` in the package __init__ re-exports
# the imported `datetime` class, which then shadows this very module: after
# importing termz, `termz.util.datetime` is the class, not the module.
__all__ = [
    "DATE_FORMAT_ENGLISH",
    "DATE_FORMAT_GERMAN",
    "date_diff",
    "date_to_timestamp",
    "timestamp_to_date",
    "today_date",
    "today_timestamp",
]

DATE_FORMAT_GERMAN = "%d.%m.%Y"
DATE_FORMAT_ENGLISH = "%Y-%m-%d"


def timestamp_to_date(
    timestamp: int | None, english_format: bool = False
) -> str:
    """
    Converts a UNIX timestamp into a date string.

    Parameters
    ----------
    timestamp : int
        UNIX timestamp
    english_format : bool, optional
        If true the format is "YYYY-MM-DD" instead of
        "DD.MM.YYYY".

    Returns
    -------
    str
        Date string in the format "DD.MM.YYYY" or "YYYY-MM-DD", as seen in
        the local time zone. Empty string if the given timestamp is None.
    """
    # Return empty string if the given timestamp is None
    if timestamp is None:
        return ""

    # Convert timestamp to a date in the local zone
    date_obj = datetime.fromtimestamp(timestamp, tz=UTC).astimezone()

    return date_obj.strftime(_date_format(english_format))


def date_to_timestamp(date_str: str, english_format: bool = False) \
-> int | None:
    """
    Converts a date in the format "DD.MM.YYYY" or "YYYY-MM-DD" into
    a UNIX timestamp.

    The date is read as local midnight.

    Parameters
    ----------
    date_str : str
        Date in the format "DD.MM.YYYY".
    english_format : bool, optional
        If true the expected format is "YYYY-MM-DD"
        instead of "DD.MM.YYYY".

    Returns
    -------
    int or None
        Unix timestamp (number of seconds since 1970-01-01), or None if the
        string does not match the expected format.
    """
    # Check if the date string matches the expected format
    try:
        date_obj = datetime.strptime(date_str, _date_format(english_format))
    except ValueError:
        return None

    # astimezone() reads a naive value as local time and attaches the matching
    # offset - the assumption this module makes explicit rather than inherits
    return int(date_obj.astimezone().timestamp())


def date_diff(timestamp1: int, timestamp2: int) -> int:
    """
    Calculates the difference between two timestamps.

    Parameters
    ----------
    timestamp1 : int
        UNIX time stamp 1.
    timestamp2 : int
        UNIX time stamp 2.

    Returns
    -------
    int
        Number of days between the given timestamps.
    """
    seconds_per_day = 86400  # 60 * 60 * 24
    diff_seconds = timestamp1 - timestamp2
    diff_days = diff_seconds // seconds_per_day

    return diff_days


def today_timestamp() -> int:
    """
    Returns the time stamp of today for the time 00:00 h.

    Returns
    -------
    int
        UNIX timestamp of local midnight.
    """
    # Date of today in the local zone
    today = datetime.now(UTC).astimezone().date()

    # Combine with time 00:00 and anchor it in the local zone
    midnight = datetime.combine(today, time.min).astimezone()

    # Return unix timestamp
    return int(midnight.timestamp())


def today_date(english_format: bool = False) -> str:
    """
    Return the date of today as a string.

    Parameters
    ----------
    english_format : bool, optional
        If true the format is "YYYY-MM-DD" instead of
        "DD.MM.YYYY".

    Returns
    -------
    str
        Today's date in the format "DD.MM.YYYY" or "YYYY-MM-DD".
    """
    today = today_timestamp()
    today_str = timestamp_to_date(today, english_format)

    return today_str


def _date_format(english_format: bool) -> str:
    """Returns the strftime format for the requested locale style."""
    return DATE_FORMAT_ENGLISH if english_format else DATE_FORMAT_GERMAN
