"""Utility functions for CCFDDL.

This module provides common utilities for timezone handling, YAML loading,
and conference data processing.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from itertools import combinations

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


def get_timezone(tz_str: str) -> timezone:
    """Convert timezone string to datetime.timezone object.

    Supported formats:
        - 'AoE' (Anywhere on Earth, UTC-12)
        - 'UTC' (UTC+0)
        - 'UTC+8', 'UTC-5' (UTC with offset)

    Args:
        tz_str: Timezone string

    Returns:
        A timezone object

    Raises:
        ValueError: If the timezone format is invalid
    """
    if tz_str == "AoE":
        return timezone(timedelta(hours=-12))
    if tz_str == "UTC":
        return timezone.utc
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
    tz = get_timezone(tz_str)
    dt = datetime.strptime(dt_str, format_str)
    return dt.replace(tzinfo=tz)


def format_duration(ddl_time: datetime, now: datetime) -> str:
    """Format the remaining duration until deadline.

    Args:
        ddl_time: Deadline datetime (timezone-aware)
        now: Current datetime (timezone-aware)

    Returns:
        Formatted duration string
    """
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
