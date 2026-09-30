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
            time_obj = None

            for timeline in conf_year.timeline:
                deadline_str = timeline.deadline
                if not deadline_str or deadline_str == "TBD":
                    continue

                try:
                    cur_d = parse_datetime_with_tz(deadline_str, conf_year.timezone)
                    if cur_d < now:
                        continue
                    if time_obj is None or cur_d < time_obj:
                        time_obj = cur_d
                except ValueError:
                    continue

            if time_obj is not None:
                category = get_category_by_sub(conf.sub)
                result = {
                    **base_info,
                    "year": conf_year.year,
                    "id": conf_year.id,
                    "link": conf_year.link,
                    "deadline": time_obj,
                    "deadline_str": time_obj.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    "timezone": conf_year.timezone,
                    "date": conf_year.date,
                    "place": conf_year.place,
                    "subname": category.name if category else conf.sub,
                    "subname_en": category.name_en if category else conf.sub,
                }
                results.append(result)

    results.sort(key=lambda x: x["deadline"])
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
