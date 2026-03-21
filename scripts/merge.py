#!/usr/bin/env python3

"""
YAML Structured Merger Script

Parse and merge multiple YAML files into a single structured file.
Outputs merged YAML to stdout, progress messages to stderr.

Usage:
    python scripts/merge.py <directory> [--exclude pattern]
    python scripts/merge.py ../../conference --exclude types.yml
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def find_yml_files(
    base_path: Path, exclude_patterns: list[str] | None = None
) -> list[Path]:
    """
    Find all .yml files in the directory, excluding specified patterns.

    Args:
        base_path: Base directory to search
        exclude_patterns: List of filename patterns to exclude

    Returns:
        Sorted list of yml file paths
    """
    if exclude_patterns is None:
        exclude_patterns = ["types.yml"]

    yml_files: list[Path] = []

    for yml_file in base_path.rglob("*.yml"):
        if yml_file.name in exclude_patterns:
            continue
        yml_files.append(yml_file)

    return sorted(yml_files)


def load_yaml_file(file_path: Path) -> list[Any] | None:
    """
    Load a YAML file and return its contents as a list.

    Args:
        file_path: Path to the YAML file

    Returns:
        List of items from the YAML file, or None if loading fails
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            return []

        if isinstance(data, list):
            return data

        return [data]

    except yaml.YAMLError as e:
        print(
            f"YAML parsing error in {file_path}: {e}",
            file=sys.stderr,
        )
        return None

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None


def merge_yaml_files(
    file_paths: list[Path], verbose: bool = True
) -> list[Any]:
    """
    Merge multiple YAML files into a single list.

    Args:
        file_paths: List of YAML file paths to merge
        verbose: Whether to print progress messages

    Returns:
        Merged list of all items
    """
    all_data: list[Any] = []

    for yml_file in file_paths:
        if verbose:
            print(f"Processing: {yml_file}", file=sys.stderr)

        data = load_yaml_file(yml_file)
        if data is not None:
            all_data.extend(data)

    return all_data


def main() -> int:
    """Main entry point for the merge script."""
    parser = argparse.ArgumentParser(
        description="Merge YAML files from specified directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Directory path to search for YAML files",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["types.yml"],
        help="Filename patterns to exclude (default: types.yml)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )

    args = parser.parse_args()
    search_path = args.path

    if not search_path.is_dir():
        print(f"Error: Directory not found: {search_path}", file=sys.stderr)
        return 1

    verbose = not args.quiet

    if verbose:
        print(f"Finding YAML files in {search_path}...", file=sys.stderr)

    yml_files = find_yml_files(search_path, args.exclude)

    if not yml_files:
        print("No YAML files found!", file=sys.stderr)
        return 0

    if verbose:
        print(f"Found {len(yml_files)} YAML files", file=sys.stderr)

    all_data = merge_yaml_files(yml_files, verbose=verbose)

    yaml.dump(
        all_data,
        sys.stdout,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        indent=2,
    )

    if verbose:
        print(
            f"Successfully merged {len(yml_files)} files "
            f"with {len(all_data)} total entries",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
