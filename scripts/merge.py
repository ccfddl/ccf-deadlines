#!/usr/bin/env python3

"""
YAML Structured Merger Script
Parse and merge multiple YAML files into a single structured file
"""

import os
import yaml
import argparse
from pathlib import Path

def find_yml_files(base_path, exclude_pattern="types.yml"):
    """
    Find all .yml files in the directory, excluding specified patterns

    Args:
        base_path: Base directory to search
        exclude_pattern: Filename pattern to exclude

    Returns:
        List of yml file paths
    """
    base_path = Path(base_path)

    yml_files = []
    for yml_file in base_path.rglob("*.yml"):
        # Skip if matches exclude pattern
        if yml_file.name == exclude_pattern:
            continue
        yml_files.append(yml_file)

    # Sort for consistent output
    return sorted(yml_files)

# Remove the separate merge function since we're doing everything in main now

def main():
    """Main function - output YAML to stdout for redirection"""

    # Command line argument parsing
    parser = argparse.ArgumentParser(description='Merge YAML files from specified directory')
    parser.add_argument('path',
                       help='Directory path to search for YAML files (e.g., ../../conference)')
    parser.add_argument('--exclude', default='types.yml',
                       help='Filename pattern to exclude (default: types.yml)')

    args = parser.parse_args()

    # Configuration
    search_path = Path(args.path)

    import sys

    # Send progress messages to stderr so they don't interfere with stdout
    print(f"🔍 Finding YAML files in {search_path}...", file=sys.stderr)
    yml_files = find_yml_files(search_path, args.exclude)

    if not yml_files:
        print("❌ No YAML files found!", file=sys.stderr)
        return

    print(f"📁 Found {len(yml_files)} YAML files", file=sys.stderr)

    # Collect all data
    all_data = []

    for yml_file in yml_files:
        print(f"Processing: {yml_file}", file=sys.stderr)
        try:
            with open(yml_file, 'r', encoding='utf-8') as file:
                # Load YAML content
                data = yaml.safe_load(file)

                # Handle different YAML structures
                if isinstance(data, list):
                    # If it's a list, extend our main list
                    all_data.extend(data)
                elif isinstance(data, dict):
                    # If it's a dict, add source info and append
                    data['_source_file'] = str(yml_file.relative_to(Path.cwd()))
                    all_data.append(data)
                elif data is not None:
                    # Handle other data types
                    data_entry = {
                        'data': data,
                        '_source_file': str(yml_file.relative_to(Path.cwd()))
                    }
                    all_data.append(data_entry)

        except yaml.YAMLError as e:
            print(f"❌ YAML parsing error in {yml_file}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Error reading {yml_file}: {e}", file=sys.stderr)

    # Output merged YAML to stdout
    yaml.dump(all_data, sys.stdout,
             default_flow_style=False,
             allow_unicode=True,
             sort_keys=False,
             indent=2)

    print(f"✅ Successfully merged {len(yml_files)} files with {len(all_data)} total entries", file=sys.stderr)

if __name__ == "__main__":
    main()
