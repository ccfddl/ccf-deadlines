"""Output formatting for CCFDDL.

This module handles formatting and displaying conference data
in various formats (table, JSON).
"""

import json
from datetime import datetime

from tabulate import tabulate
from termcolor import colored

from ccfddl.models import CATEGORIES
from ccfddl.utils import format_duration


def format_colored_duration(ddl_time: datetime, now: datetime) -> str:
    """Format duration with color coding."""
    duration_str = format_duration(ddl_time, now)
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

    table = [["Title", "Sub", "Rank", "Abs DDL", "DDL", "Link"]]

    for item in results:
        abs_ddl = (
            format_colored_duration(item["abstract_deadline"], now)
            if item.get("abstract_deadline") is not None
            else "-"
        )
        ddl = (
            format_colored_duration(item["deadline"], now)
            if item.get("deadline") is not None
            else "TBD"
        )
        table.append([
            f"{item['title']} {item['year']}",
            item["sub"],
            item["rank"],
            abs_ddl,
            ddl,
            item["link"],
        ])

    print(tabulate(table, headers="firstrow", tablefmt="fancy_grid"))


def output_json(results: list[dict[str, any]]) -> None:
    """Output results as JSON."""
    output = []
    for item in results:
        output.append({
            "title": item["title"],
            "year": item["year"],
            "id": item["id"],
            "sub": item["sub"],
            "subname": item["subname"],
            "subname_en": item["subname_en"],
            "rank": item["rank"],
            "abstract_deadline": item.get("abstract_deadline_str"),
            "deadline": item.get("deadline_str"),
            "comment": item.get("comment"),
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
