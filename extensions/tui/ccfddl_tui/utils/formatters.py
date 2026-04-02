"""Formatting utilities for CCF-Deadlines TUI.

This module provides shared formatting functions for countdowns, colors,
and other display-related utilities to avoid code duplication.
"""

from datetime import datetime, timedelta
from typing import Optional

from rich.text import Text


def get_countdown_color(days: int) -> str:
    """Determine the color based on remaining days.

    Args:
        days: Number of remaining days.

    Returns:
        Color string for Rich markup (e.g., "red", "yellow", "blue", "green").
    """
    if days < 1:
        return "red"
    elif days < 7:
        return "yellow"
    elif days < 30:
        return "blue"
    else:
        return "green"


def format_time_remaining(days: int, total_seconds: int) -> str:
    """Format the remaining time as a human-readable string.

    Args:
        days: Number of remaining days.
        total_seconds: Total remaining seconds.

    Returns:
        Formatted time string (e.g., "5 days 12:34:56" or "23:59:59").
    """
    hours, remainder = divmod(total_seconds, 3600)
    hours = hours % 24
    minutes, seconds = divmod(remainder, 60)

    if days >= 1:
        day_word = "day" if days == 1 else "days"
        return f"{days} {day_word} {hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        total_hours = total_seconds // 3600
        return f"{total_hours:02d}:{minutes:02d}:{seconds:02d}"


def format_deadline_countdown(
    deadline: Optional[datetime],
    is_tbd: bool = False,
    now: Optional[datetime] = None,
) -> Text:
    """Format a deadline countdown with appropriate styling.

    This is the main function for formatting countdowns, used by both
    ConferenceTable and CountdownWidget to ensure consistent display.

    Args:
        deadline: The deadline datetime (timezone-aware) or None.
        is_tbd: Whether the deadline is TBD (to be determined).
        now: Current datetime for comparison. If None, uses current UTC time.

    Returns:
        Rich Text object with formatted countdown and styling.
    """
    if is_tbd:
        return Text("TBD", style="dim")

    if deadline is None:
        return Text("N/A", style="dim")

    if now is None:
        from datetime import timezone
        now = datetime.now(timezone.utc)

    if deadline <= now:
        return Text("Expired", style="red")

    remaining = deadline - now
    total_days = remaining.days
    total_seconds = int(remaining.total_seconds())

    color = get_countdown_color(total_days)
    time_str = format_time_remaining(total_days, total_seconds)

    return Text(time_str, style=color)


def format_countdown_from_timedelta(remaining: timedelta) -> tuple[str, str]:
    """Format a timedelta into countdown string and color.

    Args:
        remaining: timedelta object representing remaining time.

    Returns:
        Tuple of (formatted_string, color_string).
    """
    total_days = remaining.days
    total_seconds = int(remaining.total_seconds())

    color = get_countdown_color(total_days)
    time_str = format_time_remaining(total_days, total_seconds)

    return time_str, color
