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

"""

from datetime import datetime, time


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
        Date string in the format "DD.MM.YYYY" or "YYYY-MM-DD".
        Empty string if the given timestamp is None.
    """
    # Return empty string if the given timestamp is None
    if timestamp is None:
        return ""

    # Convert timestamp to date
    date_obj = datetime.fromtimestamp(timestamp)

    if english_format:
        format_str = "%Y-%m-%d"
    else:
        format_str = "%d.%m.%Y"

    return date_obj.strftime(format_str)


def date_to_timestamp(date_str: str, english_format: bool = False) \
-> int | None:
    """
    Converts a date in the format "DD.MM.YYYY" or "YYYY-MM-DD" into
    a UNIX timestamp.

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
        Unix timestamp (number of seconds since 1970-01-01).
    """
    if english_format:
        format_str = "%Y-%m-%d"
    else:
        format_str = "%d.%m.%Y"

    # Check if the date string matches the expected format
    try:
        date_obj = datetime.strptime(date_str, format_str)
        return int(date_obj.timestamp())
    except ValueError:
        return None


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
        UNIX timestamp.
    """
    # Date of today
    today = datetime.today().date()

    # Combine with time 00:00
    midnight = datetime.combine(today, time.min)

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
        Date string in the format "DD.MM.YYYY" or "YYYY-MM-DD".
        Empty string if the given timestamp is None.
    """
    today = today_timestamp()
    today_str = timestamp_to_date(today, english_format)

    return today_str

