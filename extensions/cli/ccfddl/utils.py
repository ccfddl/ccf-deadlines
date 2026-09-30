"""Utility functions for CCFDDL.

This module provides common utilities for timezone handling, YAML loading,
and conference data processing.
"""

import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from zoneinfo import ZoneInfo

import yaml


def load_mapping(path: str = "conference/types.yml") -> dict[str, str]:
    """Load sub-category name mapping from YAML file.

    Args:
        path: Path to the types.yml file

    Returns:
        Dictionary mapping sub codes to Chinese names
    """
    with open(path, encoding="utf-8") as f:
        types = yaml.safe_load(f)
    if types is None:
        return {}
    sub_mapping: dict[str, str] = {}
    for types_data in types:
        sub_mapping[types_data["sub"]] = types_data["name"]
    return sub_mapping


def nth_sunday(year: int, month: int, n: int) -> date:
    """Return the nth Sunday of the given month."""
    first = date(year, month, 1)
    # date.weekday(): Monday=0 ... Sunday=6
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def is_us_dst(day: date) -> bool:
    """US daylight saving time: 2nd Sunday of March to 1st Sunday of November."""
    return nth_sunday(day.year, 3, 2) <= day < nth_sunday(day.year, 11, 1)


def get_timezone(tz_str: str, on_date: date | None = None) -> timezone:
    """Convert timezone string to datetime.timezone object.

    Supported formats:
        - 'AoE' (Anywhere on Earth, UTC-12)
        - 'UTC' (UTC+0)
        - 'UTC+8', 'UTC-5' (UTC with offset)
        - 'PT' (US Pacific Time, UTC-7 during DST and UTC-8 otherwise)

    Args:
        tz_str: Timezone string
        on_date: Date the deadline falls on, used to resolve daylight saving
            labels such as 'PT'. Defaults to standard time when omitted.

    Returns:
        A timezone object

    Raises:
        ValueError: If the timezone format is invalid
    """
    if tz_str == "AoE":
        return timezone(timedelta(hours=-12))
    if tz_str == "UTC":
        return timezone.utc
    if tz_str == "PT":
        if on_date is not None and is_us_dst(on_date):
            return timezone(timedelta(hours=-7))
        return timezone(timedelta(hours=-8))
    match = re.match(r"UTC([+-])(\d{1,2})$", tz_str)
    if not match:
        raise ValueError(f"Invalid timezone format: {tz_str}")
    sign, hours = match.groups()
    offset = int(hours) if sign == "+" else -int(hours)
    return timezone(timedelta(hours=offset))


def parse_datetime_with_tz(
    dt_str: str, tz_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"
) -> datetime:
    """Parse datetime string with timezone.

    Args:
        dt_str: Datetime string (e.g., '2025-01-15 23:59:59')
        tz_str: Timezone string (e.g., 'UTC-8', 'AoE')
        format_str: Datetime format string

    Returns:
        Timezone-aware datetime object

    Raises:
        ValueError: If datetime or timezone format is invalid
    """
    dt = datetime.strptime(dt_str, format_str)
    tz = get_timezone(tz_str, dt.date())
    return dt.replace(tzinfo=tz)


def parse_deadline(value: str | date, tz_str: str) -> date | datetime:
    """Preserve a valid ISO calendar date without assigning it a clock time.

    PyYAML may already have converted an unquoted date to ``date``. Precise
    timestamps still require a known source timezone; ``Unknown`` is never UTC.
    TBD and invalid values raise ValueError so callers can keep skipping them.
    """
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            raise ValueError("Deadline timestamps must use the source timezone field")
        return value.replace(tzinfo=get_timezone(tz_str, value.date()))
    if isinstance(value, date):
        day = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        day = date.fromisoformat(value)
    elif isinstance(value, str):
        return parse_datetime_with_tz(value, tz_str)
    else:
        raise ValueError(f"Invalid deadline: {value!r}")
    if tz_str != "Unknown":
        get_timezone(tz_str, day)
    return day


def deadline_has_passed(deadline: date | datetime, now: datetime, tz_str: str) -> bool:
    """Expire dates only after their whole source-zone calendar day has passed.

    For an unknown zone, UTC-12 is the last place that can still be on that
    date. This is an expiry policy, not an inferred deadline time or timezone.
    """
    if now.tzinfo is None:
        raise ValueError("Current time must be timezone-aware")
    if isinstance(deadline, datetime):
        if deadline.tzinfo is None:
            raise ValueError("Precise deadlines must be timezone-aware")
        return deadline < now
    tz = (
        ZoneInfo("America/Los_Angeles") if tz_str == "PT"
        else get_timezone("AoE" if tz_str == "Unknown" else tz_str, deadline)
    )
    return now.astimezone(tz).date() > deadline


def deadline_sort_key(deadline: date | datetime, tz_str: str) -> int:
    """Internal lower-bound ordering; never an inferred or exported deadline.

    Precise values sort chronologically. Calendar dates sort by the beginning
    of the source-zone day; Unknown uses its earliest possible start (UTC+14).
    The integer key avoids attaching a fabricated time to a date object and
    supports valid ISO boundary dates without UTC conversion overflow.
    """
    if isinstance(deadline, datetime):
        if deadline.tzinfo is None:
            raise ValueError("Precise deadlines must be timezone-aware")
        offset = deadline.utcoffset()
        seconds = deadline.hour * 3600 + deadline.minute * 60 + deadline.second
        microseconds = deadline.microsecond
    else:
        seconds = microseconds = 0
        if tz_str == "Unknown":
            offset = timedelta(hours=14)
        elif tz_str == "PT":
            # Midnight is used only to query the offset of this calendar bound.
            offset = datetime.combine(
                deadline, datetime.min.time(), ZoneInfo("America/Los_Angeles")
            ).utcoffset()
        else:
            offset = get_timezone(tz_str, deadline).utcoffset(None)
    if offset is None:
        raise ValueError("Precise deadlines must have a UTC offset")
    return (
        (deadline.toordinal() * 86400 + seconds) * 1_000_000
        + microseconds - int(offset.total_seconds() * 1_000_000)
    )


def format_duration(ddl_time: date | datetime, now: datetime) -> str:
    """Format the remaining duration until deadline.

    Args:
        ddl_time: Calendar date or timezone-aware deadline datetime
        now: Current datetime (timezone-aware)

    Returns:
        Formatted duration string
    """
    if not isinstance(ddl_time, datetime):
        return f"{ddl_time.isoformat()} (time unknown)"

    duration = ddl_time - now
    months, days = duration.days // 30, duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    day_word_str = "days" if days > 1 else "day"
    months_str, days_str = str(months).zfill(2), str(days).zfill(2)
    hours_str, minutes_str = str(hours).zfill(2), str(minutes).zfill(2)

    if days < 1:
        return f"{hours_str}:{minutes_str}:{seconds:02d}"
    if days < 30:
        return f"{days_str} {day_word_str}, {hours_str}:{minutes_str}"
    if days < 100:
        return f"{days_str} {day_word_str}"
    return f"{months_str} months"


def reverse_index(file_paths: list[str], subs: list[str]) -> dict[str, list[str]]:
    """Build reverse index of conferences by category and rank.

    Args:
        file_paths: List of YAML file paths to process
        subs: List of valid sub codes

    Returns:
        Dictionary mapping category/rank keys to file paths
    """
    index: dict[str, set[str]] = defaultdict(set)

    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            conferences = yaml.safe_load(f)

        if conferences is None:
            continue

        for conf_data in conferences:
            sub = conf_data["sub"]
            rank = conf_data["rank"]
            ccf_rank = rank.get("ccf", "N")
            core_rank = rank.get("core", "N")
            thcpl_rank = rank.get("thcpl", "N")
            rank_keys = [
                f"ccf_{ccf_rank}",
                f"core_{core_rank}",
                f"thcpl_{thcpl_rank}",
            ]

            _add_index_entry(index, sub, file_path)

            for size in range(1, len(rank_keys) + 1):
                for combo in combinations(rank_keys, size):
                    key = "_".join(combo)
                    _add_index_entry(index, key, file_path)
                    _add_index_entry(index, f"{key}_{sub}", file_path)

    return {key: sorted(paths) for key, paths in index.items()}


def _add_index_entry(index: dict[str, set[str]], key: str, file_path: str) -> None:
    """Add entry to reverse index."""
    index[key].add(file_path)
