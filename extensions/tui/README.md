# CCF-Deadlines TUI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)]()

Terminal User Interface for tracking academic conference deadlines. Browse, filter, and search CCF-ranked conferences with real-time countdown timers, all from your terminal.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CCF-Deadlines TUI - Showing 156 of 312 conferences                     [?] │
├──────────────────────┬────────────────────────────────────────────────────┤
│ Filters              │ ★   Title      Sub  CCF  CORE  THCPL  Countdown    │
│ Categories           │ ───────────────────────────────────────────────────│
│ [x] AI - AI          │ ★   NeurIPS    AI   A    A*     A     15 days...   │
│ [x] CG - Graphics    │ ☆   ICLR       AI   A    A      A     28 days...   │
│ [x] CT - Theory      │ ☆   CVPR       AI   A    A*     A     Expired      │
│ [x] DB - Database    │ ───────────────────────────────────────────────────│
│ [x] DS - Arch/Stor   │                                                    │
│ [x] HI - HCI         │                                                    │
│ [x] MX - Interdisc   │                                                    │
│ [x] NW - Network     │                                                    │
│ [x] SC - Security    │                                                    │
│ [x] SE - Soft/OS/PL  │                                                    │
│ CCF Ranks            │                                                    │
│ [x] CCF A            │                                                    │
│ [x] CCF B            │                                                    │
│ [x] CCF C            │                                                    │
│ [x] CCF N            │                                                    │
│ CORE Ranks           │                                                    │
│ [x] CORE A*          │                                                    │
│ [x] CORE A           │                                                    │
│ [x] CORE B           │                                                    │
│ [x] CORE C           │                                                    │
│ [x] CORE N           │                                                    │
│ THCPL Ranks          │                                                    │
│ [x] THCPL A          │                                                    │
│ [x] THCPL B          │                                                    │
│ [x] THCPL N          │                                                    │
│ Options              │                                                    │
│ [ ] Show Expired     │                                                    │
│ Search               │                                                    │
│ [neur____________]   │                                                    │
├──────────────────────┴────────────────────────────────────────────────────┤
│ Quit: q  Language: l  Refresh: r  Favorite: f  Open URL: Enter  Help: ?  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

- **Real-time Countdown** - Live countdown timers that update every second
- **10 Research Categories** - Filter by AI, DB, CG, CT, DS, HI, MX, NW, SC, SE
- **Multi-rank Filtering** - Filter by CCF, CORE, and THCPL rankings
- **Favorites** - Star conferences to pin them to the top of the list
- **Fuzzy Search** - Quick search by conference title with smart matching
- **Bilingual Support** - Toggle between English and Chinese interface
- **Vim-style Navigation** - Familiar j/k keys for power users
- **Direct URL Opening** - Open conference websites with a single keypress
- **Color-coded Countdown** - Visual urgency indicators (red < 1 day, yellow < 7 days, blue < 30 days, green >= 30 days)
- **Auto-sorting** - Favorites first, then running conferences sorted by deadline, expired sorted by year
- **Local Fallback** - Automatically falls back to local data when remote is unavailable

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Install from Source

```bash
# Clone the repository
git clone https://github.com/ccfddl/ccf-deadlines.git
cd ccf-deadlines/extensions/tui

# Install the package
pip install -e .
```

### Install with Development Dependencies

```bash
# Install with dev tools (pytest, mypy, etc.)
pip install -e ".[dev]"
```

### Dependencies

The TUI requires these packages (installed automatically):

- `textual>=0.47.0` - Terminal UI framework
- `pyyaml` - YAML parsing
- `requests` - HTTP requests
- `python-dateutil` - Date handling

## Usage

### Basic Launch

```bash
# Launch with default data source
ccfddl-tui
```

### Custom Data Source

```bash
# Use a custom conference data URL
ccfddl-tui --url https://example.com/conferences.yml
```

### Command Line Options

```bash
# Show help
ccfddl-tui --help

# Show version
ccfddl-tui --version
```

| Option | Description |
|--------|-------------|
| `--url URL` | Custom URL for conference data (default: https://ccfddl.github.io/conference/allconf.yml) |
| `--version` | Show version number |
| `--help` | Show help message |

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `j` / `↓` | Move down one row |
| `k` / `↑` | Move up one row |
| `g` | Go to first row |
| `G` | Go to last row |

### Actions

| Key | Action |
|-----|--------|
| `Enter` | Open selected conference URL in browser |
| `f` | Toggle favorite (★) for selected conference |
| `l` | Toggle language (English/Chinese) |
| `r` | Refresh data from source |
| `q` | Quit application |

### Search & Filter

| Key | Action |
|-----|--------|
| Type in search box | Fuzzy filter by conference title |
| Click checkboxes | Toggle category/rank filters |
| `Esc` | Clear search input |

### Help

| Key | Action |
|-----|--------|
| `?` | Show help screen |
| `Esc` | Close help screen |

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_conference_table.py -v

# Run with coverage
pytest tests/ --cov=ccfddl_tui --cov-report=html
```

### Type Checking

```bash
# Run mypy type checker
mypy ccfddl_tui/
```

### Project Structure

```
extensions/tui/
├── ccfddl_tui/
│   ├── __init__.py
│   ├── main.py           # CLI entry point
│   ├── app.py            # Main TUI application
│   ├── styles.tcss       # Textual CSS styles
│   ├── data/
│   │   ├── __init__.py
│   │   └── data_service.py  # Data loading & filtering
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── conference_table.py  # Conference display table
│   │   ├── filters.py     # Filter sidebar widget
│   │   └── countdown.py   # Countdown utilities
│   └── utils/
│       ├── __init__.py
│       └── formatters.py  # Shared formatting utilities
├── tests/
│   ├── conftest.py        # Shared test fixtures
│   ├── test_app.py        # Application tests
│   ├── test_conference_table.py
│   ├── test_filters.py
│   ├── test_data_service.py
│   ├── test_countdown.py
│   ├── test_favorites.py
│   └── test_extended_filters.py
├── pyproject.toml
└── README.md
```

## Architecture

The TUI is built on [Textual](https://github.com/Textualize/textual), a modern Python framework for building terminal user interfaces.

### Components

#### `DataService`
Handles data loading and processing:
- Fetches conference YAML from remote URL with local fallback
- Converts raw data to display rows
- Provides fuzzy search and filtering
- Manages favorites persistence (~/.ccfddl/favorites.json)
- Sorts conferences by favorites, deadline status

#### `FilterSidebar`
Left sidebar with filter controls:
- Category checkboxes (10 research areas)
- CCF rank checkboxes (A/B/C/N)
- CORE rank checkboxes (A*/A/B/C/N)
- THCPL rank checkboxes (A/B/N)
- Show Expired toggle
- Search input field
- Emits `FilterChanged` messages on updates

#### `ConferenceTable`
Main data display widget:
- Real-time countdown updates (1 second interval)
- Sortable columns (click headers)
- Zebra striping for readability
- Color-coded countdown urgency
- Row selection with URL opening
- Favorite indicator (★/☆)

#### `CCFDeadlinesApp`
Main application orchestrator:
- Manages reactive state (filters, search, language)
- Coordinates between widgets
- Handles keyboard bindings
- Shows loading/error overlays

### Data Flow

```
[Remote YAML]
     │
     ▼
[DataService.load_conferences()] ──fallback──▶ [Local YAML files]
     │
     ▼
[DataService.process_rows()]
     │
     ▼
[FilterSidebar] ──FilterChanged──▶ [App._update_conferences()]
     │                                    │
     ▼                                    ▼
[App.selected_subs/ranks/query]    [ConferenceTable.update_rows()]
                                              │
                                              ▼
                                    [Real-time countdown refresh]
```

## Troubleshooting

### Terminal Colors Not Displaying Correctly

Ensure your terminal supports 256 colors or true color:

```bash
# Check terminal color support
echo $TERM

# Set terminal type if needed
export TERM=xterm-256color
```

### Conference Data Not Loading

1. Check your internet connection
2. Verify the data URL is accessible:
   ```bash
   curl -I https://ccfddl.github.io/conference/allconf.yml
   ```
3. Try with a custom URL:
   ```bash
   ccfddl-tui --url https://ccfddl.top/conference/allconf.yml
   ```
4. If remote fails, the app automatically falls back to local data (shows `[LOCAL]` indicator)

### URL Not Opening in Browser

The TUI uses Python's `webbrowser` module. If URLs don't open:
- On Linux, ensure `xdg-open` is available
- On macOS, ensure the default browser is set
- Set the `BROWSER` environment variable:
   ```bash
   export BROWSER=firefox
   ```

### App Crashes on Start

1. Check Python version (3.10+ required):
   ```bash
   python --version
   ```
2. Reinstall dependencies:
   ```bash
   pip install --force-reinstall -e .
   ```

## Contributing

We welcome contributions! Please see the [main project contributing guidelines](https://github.com/ccfddl/ccf-deadlines#contribution) for details.

### Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/ccfddl/ccf-deadlines/issues) with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your terminal and Python version

## Related Projects

- [CCF-Deadlines Web](https://ccfddl.github.io/) - Main web portal
- [CCF-Deadlines CLI](../cli/) - Command-line interface
- [CCF-Deadlines Chrome Extension](../chrome/) - Browser extension
- [Raycast Extension](https://www.raycast.com/ViGeng/ccfddl) - macOS launcher

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/ccfddl/ccf-deadlines/blob/main/LICENSE) file for details.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual) - The Python TUI framework
- Conference data from [CCF-Deadlines](https://github.com/ccfddl/ccf-deadlines)
- Maintained by the [@ccfddl](https://github.com/ccfddl) community
