#!/usr/bin/env python3

"""
Pre-commit hook to validate conference YAML files.

Usage:
    python scripts/validate.py
    python scripts/validate.py --help

To use as git pre-commit hook, install dependencies:
    pip install PyYAML jsonschema
"""

import os
import sys
from io import StringIO
from pathlib import Path
from typing import Any
from unittest import TestCase, TestLoader, TextTestRunner

import jsonschema
import yaml

ROOT = Path(__file__).parent.parent
DATA_ROOT = ROOT / "conference"
SCHEMA_PATH = ROOT / "conference-yaml-schema.yml"


def load_conference_yaml_schema(schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    """Load and return the YAML validation schema."""
    with open(schema_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_single_conference(
    conf_path: Path, schema: dict[str, Any]
) -> list[str]:
    """Validate a single conference YAML file. Returns list of error messages."""
    errors = []
    
    if conf_path.suffix == ".yaml":
        errors.append(
            f"{conf_path.name} should be renamed as {conf_path.stem}.yml"
        )
        return errors
    
    if conf_path.suffix != ".yml":
        return errors
    
    try:
        with open(conf_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax in {conf_path.name}: {e}")
        return errors
    except Exception as e:
        errors.append(f"Error reading {conf_path.name}: {e}")
        return errors
    
    try:
        jsonschema.validate(content, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema validation failed for {conf_path.name}: {e.message}")
    
    return errors


def validate_all_conferences(
    data_root: Path = DATA_ROOT, schema: dict[str, Any] | None = None
) -> list[str]:
    """Validate all conference YAML files. Returns list of all error messages."""
    if schema is None:
        schema = load_conference_yaml_schema()
    
    all_errors: list[str] = []
    
    if not data_root.is_dir():
        all_errors.append(f"Data directory not found: {data_root}")
        return all_errors
    
    for sub_dir in sorted(data_root.iterdir()):
        if not sub_dir.is_dir():
            continue
        
        for conf_file in sorted(sub_dir.iterdir()):
            if conf_file.is_file():
                errors = validate_single_conference(conf_file, schema)
                all_errors.extend(errors)
    
    return all_errors


def run_validation() -> bool:
    """Run validation and return True if all files are valid."""
    schema = load_conference_yaml_schema()
    errors = validate_all_conferences(schema=schema)
    
    if errors:
        print("\n\033[1;31mValidation Errors:\033[m")
        for error in errors:
            print(f"  - {error}")
        print(
            f"\n\033[1;31mFound {len(errors)} error(s). "
            f"Please fix and commit again.\033[m"
        )
        return False
    
    print("\033[1;32mAll conference YAML files are valid.\033[m")
    return True


def main() -> int:
    """Main entry point for the validation script."""
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return 0
    
    return 0 if run_validation() else 1


if __name__ == "__main__":
    sys.exit(main())