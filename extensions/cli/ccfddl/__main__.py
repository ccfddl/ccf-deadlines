"""CCFDDL CLI - Conference Deadline Tracker.

A command-line tool for viewing and filtering conference deadlines.
"""

import argparse
from datetime import datetime, timezone

from ccfddl import __version__
from ccfddl.fetch import fetch_conferences, filter_results, process_conference_deadlines
from ccfddl.output import list_categories, output_json, output_table


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
