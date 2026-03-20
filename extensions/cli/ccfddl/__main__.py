"""CCFDDL CLI - Conference Deadline Tracker.

A command-line tool for viewing and filtering conference deadlines.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import requests
import yaml
from tabulate import tabulate
from termcolor import colored

from ccfddl import __version__
from ccfddl.models import CATEGORIES, Conference, get_category_by_sub
from ccfddl.utils import format_duration, parse_datetime_with_tz


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="CCFDDL CLI - Conference Deadline Tracker",
        epilog="Example: ccfddl --conf CVPR ICML --sub AI --rank A",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--conf",
        type=str,
        nargs="+",
        help="Filter by conference IDs (e.g., --conf CVPR ICML)",
    )
    parser.add_argument(
        "--sub",
        type=str,
        nargs="+",
        help="Filter by subcategories (e.g., --sub AI CG)",
    )
    parser.add_argument(
        "--rank",
        type=str,
        nargs="+",
        help="Filter by CCF ranks (e.g., --rank A B)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List all categories",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://ccfddl.github.io/conference/allconf.yml",
        help="URL to fetch conference data (default: ccfddl.github.io)",
    )
    return parser.parse_args()


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
        return [Conference.from_dict(item) for item in data]
    except requests.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)


def process_conference_deadlines(
    conferences: list[Conference], now: datetime
) -> list[dict]:
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

            if time_obj is not None and time_obj > now:
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
    results: list[dict],
    conf_filter: list[str] | None,
    sub_filter: list[str] | None,
    rank_filter: list[str] | None,
) -> list[dict]:
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


def output_table(results: list[dict], now: datetime) -> None:
    """Output results as a formatted table."""
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


def output_json(results: list[dict]) -> None:
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
            "deadline": item["deadline_str"],
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


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.list_categories:
        list_categories()
        return

    now = datetime.now(tz=timezone.utc)
    conferences = fetch_conferences(args.url)
    results = process_conference_deadlines(conferences, now)

    filtered = filter_results(
        results,
        args.conf,
        args.sub,
        args.rank,
    )

    if args.json:
        output_json(filtered)
    else:
        output_table(filtered, now)


if __name__ == "__main__":
    main()
