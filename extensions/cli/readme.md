# ccfddl cli

CLI tool for CCFDDL - Conference Deadline Tracker

## Install

```bash
# Using pip with dev dependencies
pip install -e ".[dev]"

# Or using requirements
pip install -r req.txt
```

## Usage

```bash
# Show help
ccfddl --help

# List all categories
ccfddl --list-categories

# Filter by conference, subcategory, rank
ccfddl --conf CVPR ICCV --sub AI --rank A

# JSON output
ccfddl --json --sub AI

# Show version
ccfddl --version
```

### Arguments

| Argument | Type  | Description                          | Example            |
| -------- | ----- | ------------------------------------ | ------------------ |
| `--conf` | str[] | A list of conference IDs to filter.  | `--conf CVPR ICCV` |
| `--sub`  | str[] | A list of subcategory IDs to filter. | `--sub AI CG`      |
| `--rank` | str[] | A list of ranks to filter.           | `--rank A B`       |
| `--json` | flag  | Output in JSON format.               | `--json`           |
| `--list-categories` | flag | List all categories.          | `--list-categories`|
| `--url`  | str   | Custom URL for conference data.      | `--url https://...`|
| `--version` | flag | Show version.                       | `--version`        |

## Generate iCal/RSS Feeds

```bash
# Generate iCal files (requires xlin package)
python -m ccfddl.convert_to_ical

# Generate RSS files
python -m ccfddl.convert_to_rss
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=ccfddl --cov-report=html

# Type checking
mypy ccfddl/
```

## Python API

```python
from ccfddl import (
    Conference, ConferenceYear, Timeline, Rank, Category,
    CATEGORIES, VALID_SUBS,
    get_category_by_sub, get_all_subs, is_valid_sub,
    load_mapping, get_timezone, reverse_index,
    format_duration, parse_datetime_with_tz,
    CacheManager, get_default_cache,
)

# Get category info
cat = get_category_by_sub("AI")
print(cat.name)  # 人工智能
print(cat.name_en)  # Artificial Intelligence

# Parse timezone
from datetime import datetime
tz = get_timezone("UTC+8")
dt = datetime(2025, 1, 15, 23, 59, 59, tzinfo=tz)

# Use cache
cache = get_default_cache()
cache.set("my_key", {"data": "value"})
data = cache.get("my_key")
```
