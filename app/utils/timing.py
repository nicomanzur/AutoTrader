"""
Timing utilities for TraderDesk V2.

This module provides time-related utility functions for bar alignment,
sleep operations, and timestamp management.
"""
from __future__ import annotations
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional


def get_timezone(tz_name: str) -> ZoneInfo:
    """
    Get timezone object from name.

    Args:
        tz_name: Timezone name (e.g., 'UTC', 'America/New_York')

    Returns:
        ZoneInfo object for the timezone

    Raises:
        ValueError: If timezone name is invalid
    """
    try:
        return ZoneInfo(tz_name)
    except Exception as e:
        raise ValueError(f"Invalid timezone '{tz_name}': {e}") from e


def next_quarter_close(now_tz: datetime, bar_minutes: int = 15) -> datetime:
    """
    Calculate the next bar close time (quarter hour by default).

    Args:
        now_tz: Current time in the target timezone
        bar_minutes: Bar interval in minutes (default: 15)

    Returns:
        Datetime of the next bar close
    """
    current_minute = now_tz.minute
    next_close_minute = ((current_minute // bar_minutes) + 1) * bar_minutes

    if next_close_minute >= 60:
        # Wrap to next hour
        return (now_tz.replace(minute=0, second=0, microsecond=0) +
                timedelta(hours=1))

    return now_tz.replace(minute=next_close_minute, second=0, microsecond=0)


def sleep_until(target_time: datetime, max_sleep: float = 0.5) -> None:
    """
    Sleep until a specific datetime, with periodic wakeups.

    Args:
        target_time: Target datetime to sleep until
        max_sleep: Maximum sleep interval in seconds (default: 0.5)
    """
    while True:
        now = datetime.now(target_time.tzinfo)
        remaining = (target_time - now).total_seconds()

        if remaining <= 0:
            break

        time.sleep(min(remaining, max_sleep))


def utcnow_iso() -> str:
    """
    Get current UTC time as ISO string without microseconds.

    Returns:
        ISO formatted UTC timestamp (e.g., "2024-01-15T10:30:00Z")
    """
    return (datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"))


def format_iso(dt: datetime) -> str:
    """
    Format datetime as ISO string without microseconds.

    Args:
        dt: Datetime to format

    Returns:
        ISO formatted timestamp
    """
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def calculate_lookback_days(required_bars: int, bar_minutes: int,
                            buffer_days: int = 4) -> int:
    """
    Calculate how many days of historical data to fetch.

    Args:
        required_bars: Number of bars required
        bar_minutes: Bar interval in minutes
        buffer_days: Additional buffer days (default: 4)

    Returns:
        Number of days to look back
    """
    import math
    days = math.ceil(required_bars * bar_minutes / (24 * 60))
    return max(days + buffer_days, 7)


def is_within_rth(ts_utc: datetime, rth_start: str = "09:30",
                   rth_end: str = "16:15", timezone_name: str = "America/New_York") -> bool:
    """
    Check if a UTC timestamp is within Regular Trading Hours.

    Args:
        ts_utc: UTC timestamp to check
        rth_start: RTH start time in HH:MM format
        rth_end: RTH end time in HH:MM format
        timezone_name: Timezone for RTH (default: America/New_York)

    Returns:
        True if within RTH, False otherwise
    """
    try:
        tz = ZoneInfo(timezone_name)
        ts_local = ts_utc.astimezone(tz)
        time_str = f"{ts_local.hour:02d}:{ts_local.minute:02d}"
        return rth_start <= time_str <= rth_end
    except Exception:
        return False


def add_bar_interval(dt: datetime, bar_minutes: int) -> datetime:
    """
    Add a bar interval to a datetime.

    Args:
        dt: Base datetime
        bar_minutes: Bar interval in minutes

    Returns:
        Datetime with bar interval added
    """
    return dt + timedelta(minutes=bar_minutes)


def subtract_bar_interval(dt: datetime, bar_minutes: int) -> datetime:
    """
    Subtract a bar interval from a datetime.

    Args:
        dt: Base datetime
        bar_minutes: Bar interval in minutes

    Returns:
        Datetime with bar interval subtracted
    """
    return dt - timedelta(minutes=bar_minutes)


class RetryTimer:
    """Timer for retry logic with exponential backoff."""

    def __init__(self, max_retries: int, base_interval: float,
                 max_interval: Optional[float] = None,
                 exponential: bool = False):
        """
        Initialize retry timer.

        Args:
            max_retries: Maximum number of retry attempts
            base_interval: Base interval between retries in seconds
            max_interval: Maximum interval (for exponential backoff)
            exponential: Use exponential backoff if True
        """
        self.max_retries = max_retries
        self.base_interval = base_interval
        self.max_interval = max_interval or base_interval * 10
        self.exponential = exponential
        self.attempt = 0

    def should_retry(self) -> bool:
        """Check if should continue retrying."""
        return self.attempt < self.max_retries

    def sleep(self) -> None:
        """Sleep for the calculated interval."""
        if self.exponential:
            # Exponential backoff: 2^attempt * base_interval
            interval = min(self.base_interval * (2 ** self.attempt),
                          self.max_interval)
        else:
            interval = self.base_interval

        time.sleep(interval)
        self.attempt += 1

    def reset(self) -> None:
        """Reset the retry counter."""
        self.attempt = 0
