# ccfddl cli

CLI tool for CCFDDL - Conference Deadline Tracker

## Install

```bash
# Using pip
pip install -e .

# Or using req.txt
pip install -r req.txt
```

## Usage

```bash
ccfddl

# Or
python -m ccfddl
```

| Argument | Type  | Description                          | Example            |
| -------- | ----- | ------------------------------------ | ------------------ |
| `--conf` | str[] | A list of conference IDs to filter.  | `--conf CVPR ICCV` |
| `--sub`  | str[] | A list of subcategory IDs to filter. | `--sub AI ML`      |
| `--rank` | str[] | A list of ranks to filter.           | `--rank A B`       |

## Generate iCal/RSS Feeds

```bash
# Generate iCal files
python -m ccfddl.convert_to_ical

# Generate RSS files
python -m ccfddl.convert_to_rss
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Type checking
mypy ccfddl/
```