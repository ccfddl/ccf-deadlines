# Changes Summary

This document summarizes the changes made to optimize the CCF-Deadlines project.

## Overview

- **Total Tests**: 105 tests (24 in scripts/tests + 81 in extensions/cli/tests)
- **Files Modified**: 10 files
- **Files Created**: 13 files

---

## 1. CLI Extension Optimization (`extensions/cli/`)

### 1.1 Fixed Dependencies (`req.txt`)

- Removed duplicate `yaml` (already included in `pyyaml`)
- Added missing dependencies: `icalendar`, `xlin`

### 1.2 Refactored `__main__.py`

| Issue | Fix |
|-------|-----|
| Type annotation error (`string` module instead of `str` type) | Changed to proper `str` type hints |
| Performance issue with `deepcopy` | Replaced with dict merge operator `{**base, **conf}` |
| Overly broad exception handling | Changed `except Exception` to `except ValueError` |
| Redundant imports | Removed unused `import string`, `from copy import deepcopy` |
| Poor function naming | Renamed `alpha_id` to `extract_alpha_id` |
| Missing type hints | Added type hints to all functions |

### 1.3 Created `utils.py`

Extracted common utility functions:
- `load_mapping()` - Load conference type mappings
- `get_timezone()` - Convert timezone string to `datetime.timezone`
- `reverse_index()` - Build reverse index for conferences by category/rank
- `format_duration()` - Format remaining time until deadline
- `parse_datetime_with_tz()` - Parse datetime with timezone

### 1.4 Optimized `convert_to_ical.py`

- Fixed mutable default argument (`SUB_MAPPING={}` → `sub_mapping: dict | None = None`)
- Added proper type hints
- Changed to absolute imports (`from ccfddl.utils import ...`)
- Removed duplicate code (functions now imported from utils.py)

### 1.5 Optimized `convert_to_rss.py`

- Changed to absolute imports
- Fixed mutable default argument
- Added type hints

### 1.6 Added `pyproject.toml`

Modern Python packaging configuration:
- Replaced legacy `setup.py`
- Added test configuration (pytest)
- Added type checking configuration (mypy)
- Defined CLI entry point: `ccfddl` command

### 1.7 Updated `__init__.py`

- Added `__version__` and `__author__`
- Exported public API functions

---

## 2. Scripts Optimization (`scripts/`)

### 2.1 Refactored `validate.py`

| Before | After |
|--------|-------|
| Used `unittest` framework | Pure functions, easier to test |
| Global variables | Clean function signatures |
| No type hints | Full type hints |
| Mixed concerns | Separated validation logic |
| Poor error messages | Detailed, actionable error messages |

**New functions:**
- `load_conference_yaml_schema()` - Load YAML schema with type hints
- `validate_single_conference()` - Validate one file, return error list
- `validate_all_conferences()` - Validate all files in directory
- `run_validation()` - Main validation entry point

### 2.2 Refactored `merge.py`

| Before | After |
|--------|-------|
| No type hints | Full type hints |
| Single monolithic function | Modular functions |
| Hard-coded behavior | Configurable via arguments |
| No `--quiet` option | Added `-q` flag for silent operation |

**New functions:**
- `find_yml_files()` - Find YAML files with exclude patterns
- `load_yaml_file()` - Load and parse YAML file
- `merge_yaml_files()` - Merge multiple files into list

---

## 3. Data Models Migration (NEW)

Migrated data models from Rust/WASM frontend (`src/components/conf.rs`) to Python.

### 3.1 New `models.py`

Dataclasses for conference data:

| Class | Description |
|-------|-------------|
| `Rank` | Conference ranking (ccf, core, thcpl) |
| `Timeline` | Deadline timeline entry |
| `ConferenceYear` | Conference info for a specific year |
| `Conference` | Full conference data |
| `Category` | Conference category with Chinese/English names |
| `AccYear` | Acceptance rate for a year |
| `ConfAccRate` | Conference acceptance rates |

### 3.2 Category Constants

Migrated from `get_categories()` function:

```python
CATEGORIES: list[Category] = [
    Category(name="计算机体系结构/...", name_en="Computer Architecture", sub="DS"),
    Category(name="计算机网络", name_en="Network System", sub="NW"),
    # ... 10 categories total
]
```

Helper functions:
- `get_category_by_sub(sub)` - Get category by sub code
- `get_all_subs()` - Get all valid sub codes
- `is_valid_sub(sub)` - Validate sub code

---

## 4. CLI Feature Enhancements (NEW)

### 4.1 New Command-Line Options

| Option | Description |
|--------|-------------|
| `--json` | Output results in JSON format |
| `--list-categories` | List all available categories |
| `--url URL` | Custom URL for conference data |

### 4.2 New `cache.py`

Local cache management for offline usage:
- `CacheManager` class with configurable expiry
- `get()`, `set()`, `clear()` methods
- `get_default_cache()` for default instance

---

## 5. Unit Tests

### 5.1 CLI Tests (`extensions/cli/tests/`)

| File | Tests | Coverage |
|------|-------|----------|
| `test_utils.py` | 8 | `get_timezone`, `load_mapping`, `reverse_index` |
| `test_main.py` | 24 | `parse_args`, `format_duration`, `extract_alpha_id`, `main` |
| `test_models.py` | 22 | All data models, category constants |
| `test_cache.py` | 9 | Cache management, expiry |
| `test_convert_to_ical.py` | 7 | iCal generation, multiple files, Chinese/English |
| `test_convert_to_rss.py` | 8 | RSS structure, channel info, items |
| **Total** | **81** | |

### 5.2 Scripts Tests (`scripts/tests/`)

| File | Tests | Coverage |
|------|-------|----------|
| `test_validate.py` | 10 | Schema loading, single file validation, batch validation |
| `test_merge.py` | 14 | File finding, YAML loading, merging |
| **Total** | **24** | |

---

## 6. File Structure After Changes

```
ccf-deadlines/
├── AGENTS.md                    # Updated with new guidelines
├── changes.md                   # This file
├── scripts/
│   ├── validate.py              # Refactored
│   ├── merge.py                 # Refactored
│   └── tests/
│       ├── __init__.py
│       ├── test_validate.py
│       └── test_merge.py
└── extensions/cli/
    ├── pyproject.toml
    ├── req.txt
    ├── readme.md
    └── ccfddl/
        ├── __init__.py          # Updated with new exports
        ├── __main__.py          # Refactored with new features
        ├── models.py            # NEW - Data models
        ├── utils.py             # Updated with new functions
        ├── cache.py             # NEW - Cache management
        ├── convert_to_ical.py
        └── convert_to_rss.py
        └── tests/
            ├── test_utils.py
            ├── test_main.py
            ├── test_models.py
            ├── test_cache.py      # NEW
            ├── test_convert_to_ical.py
            └── test_convert_to_rss.py
```

---

## 7. How to Run Tests

```bash
# Run scripts tests
python -m pytest scripts/tests/ -v

# Run CLI tests
cd extensions/cli
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=ccfddl --cov-report=html
```

---

## 8. Usage Examples

```bash
# Basic usage
ccfddl --conf CVPR ICML --sub AI --rank A

# JSON output
ccfddl --json --sub AI

# List all categories
ccfddl --list-categories

# Use custom URL
ccfddl --url https://example.com/conferences.yml
```