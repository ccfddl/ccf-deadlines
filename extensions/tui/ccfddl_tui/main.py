"""CLI entry point for ccfddl-tui."""

import argparse
import sys

from ccfddl_tui.app import CCFDeadlinesApp


def main() -> None:
    """Main entry point for the TUI application.

    Parses command-line arguments and launches the CCF Deadlines TUI.
    """
    parser = argparse.ArgumentParser(
        prog="ccfddl-tui",
        description="Terminal User Interface for CCF Conference Deadlines",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Custom URL for conference data (default: https://ccfddl.github.io/conference/allconf.yml)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    try:
        app = CCFDeadlinesApp(url=args.url)
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()