"""Output formatting for CCFDDL.

This module handles formatting and displaying conference data
in various formats (table, JSON).
"""

import json
from datetime import date, datetime, timezone

from tabulate import tabulate
from termcolor import colored

from ccfddl.models import CATEGORIES
from ccfddl.utils import format_duration


def format_colored_duration(ddl_time: date | datetime, now: datetime) -> str:
    """Format duration with color coding."""
    duration_str = format_duration(ddl_time, now)
    if not isinstance(ddl_time, datetime):
        return duration_str
    days = (ddl_time - now).days

    if days < 1:
        return colored(duration_str, "red")
    elif days < 30:
        return colored(duration_str, "yellow")
    elif days < 100:
        return colored(duration_str, "blue")
    else:
        return colored(duration_str, "green")


def output_table(results: list[dict[str, any]], now: datetime) -> None:
    """Output results as a formatted table."""
    if not results:
        print("No upcoming deadlines found.")
        return

    table = [["Title", "Sub", "Rank", "DDL", "Link"]]

    for item in results:
        table.append([
            f"{item['title']} {item['year']}",
            item["sub"],
            item["rank"],
            format_colored_duration(item["deadline"], now),
            item["link"],
        ])

    print(tabulate(table, headers="firstrow", tablefmt="fancy_grid"))


def output_json(results: list[dict[str, any]]) -> None:
    """Output results as JSON."""
    output = []
    for item in results:
        deadline = item["deadline"]
        precise = isinstance(deadline, datetime)
        output.append({
            "title": item["title"],
            "year": item["year"],
            "id": item["id"],
            "sub": item["sub"],
            "subname": item["subname"],
            "subname_en": item["subname_en"],
            "rank": item["rank"],
            "deadline": item["deadline_str"],
            "precision": "datetime" if precise else "date",
            "deadline_at": (
                deadline.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if precise else None
            ),
            "deadline_date": None if precise else deadline.isoformat(),
            "timezone": item["timezone"],
            "date": item["date"],
            "place": item["place"],
            "link": item["link"],
            "dblp": item["dblp"],
        })
    print(json.dumps(output, indent=2, ensure_ascii=False))


def list_categories() -> None:
    """Print all available categories."""
    print("Available Categories:")
    print("-" * 60)
    for cat in CATEGORIES:
        print(f"  {cat.sub:4s} | {cat.name_en:30s} | {cat.name}")
    print("-" * 60)
    print(f"Total: {len(CATEGORIES)} categories")
