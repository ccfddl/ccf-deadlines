"""Data fetching and processing for CCFDDL.

This module handles fetching conference data from remote sources
and processing deadlines.
"""

import sys
from datetime import datetime

import requests
import yaml

from ccfddl.models import Conference, get_category_by_sub
from ccfddl.utils import parse_datetime_with_tz


def extract_alpha_id(with_digits: str) -> str:
    """Extract alphabetic characters from string, converted to lowercase."""
    return "".join(char for char in with_digits.lower() if char.isalpha())


def fetch_conferences(url: str) -> list[Conference]:
    """Fetch and parse conference data from URL."""
    try:
        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        content = response.content
        data = yaml.safe_load(content)
        if data is None:
            print("Warning: No data returned from URL", file=sys.stderr)
            return []
        return [Conference.from_dict(item) for item in data]
    except requests.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)


def _parse_upcoming(
    raw_deadline: str | None, timezone_str: str, now: datetime
) -> datetime | None:
    """Parse a deadline string and return it only if it is in the future."""
    if not raw_deadline or raw_deadline == "TBD":
        return None
    try:
        dt = parse_datetime_with_tz(raw_deadline, timezone_str)
        return dt if dt >= now else None
    except ValueError:
        return None


def process_conference_deadlines(
    conferences: list[Conference], now: datetime
) -> list[dict[str, any]]:
    """Process conferences and extract upcoming deadlines."""
    results = []

    for conf in conferences:
        base_info = {
            "title": conf.title,
            "description": conf.description,
            "sub": conf.sub,
            "rank": conf.rank.ccf,
            "dblp": conf.dblp,
        }

        for conf_year in conf.confs:
            best_next: datetime | None = None
            best_abs: datetime | None = None
            best_ddl: datetime | None = None
            best_comment: str | None = None

            for timeline in conf_year.timeline:
                cur_abs = _parse_upcoming(
                    timeline.abstract_deadline, conf_year.timezone, now
                )
                cur_ddl = _parse_upcoming(
                    timeline.deadline, conf_year.timezone, now
                )

                candidates = [d for d in (cur_abs, cur_ddl) if d is not None]
                if not candidates:
                    continue

                round_next = min(candidates)
                if best_next is None or round_next < best_next:
                    best_next = round_next
                    best_abs = cur_abs
                    best_ddl = cur_ddl
                    best_comment = timeline.comment

            if best_next is not None:
                category = get_category_by_sub(conf.sub)
                result = {
                    **base_info,
                    "year": conf_year.year,
                    "id": conf_year.id,
                    "link": conf_year.link,
                    "abstract_deadline": best_abs,
                    "abstract_deadline_str": (
                        best_abs.strftime("%Y-%m-%d %H:%M:%S %Z")
                        if best_abs is not None
                        else None
                    ),
                    "deadline": best_ddl,
                    "deadline_str": (
                        best_ddl.strftime("%Y-%m-%d %H:%M:%S %Z")
                        if best_ddl is not None
                        else None
                    ),
                    "next_deadline": best_next,
                    "comment": best_comment,
                    "timezone": conf_year.timezone,
                    "date": conf_year.date,
                    "place": conf_year.place,
                    "subname": category.name if category else conf.sub,
                    "subname_en": category.name_en if category else conf.sub,
                }
                results.append(result)

    results.sort(key=lambda x: x["next_deadline"])
    return results


def filter_results(
    results: list[dict[str, any]],
    conf_filter: list[str] | None,
    sub_filter: list[str] | None,
    rank_filter: list[str] | None,
) -> list[dict[str, any]]:
    """Apply filters to results."""
    filtered = []

    conf_filter_lower = [f.lower() for f in conf_filter] if conf_filter else None
    sub_filter_lower = [f.lower() for f in sub_filter] if sub_filter else None
    rank_filter_lower = [f.lower() for f in rank_filter] if rank_filter else None

    for item in results:
        if conf_filter_lower:
            id_alpha = extract_alpha_id(item["id"])
            title_alpha = extract_alpha_id(item["title"])
            if id_alpha not in conf_filter_lower and title_alpha not in conf_filter_lower:
                continue
        if sub_filter_lower and extract_alpha_id(item["sub"]) not in sub_filter_lower:
            continue
        if rank_filter_lower and item["rank"].lower() not in rank_filter_lower:
            continue
        filtered.append(item)

    return filtered
