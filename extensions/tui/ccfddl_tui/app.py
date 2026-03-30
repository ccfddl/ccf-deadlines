"""Main TUI application for CCF Deadlines.

This module provides the main application class that orchestrates all widgets
and handles the application lifecycle, data loading, and user interactions.
"""

from datetime import datetime, timezone
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

from ccfddl.models import CATEGORIES

from .data import ConferenceRow, DataService
from .widgets import ConferenceTable, FilterChanged, FilterSidebar


class CCFDeadlinesApp(App):
    """Main TUI application for CCF Deadlines.

    A terminal user interface for browsing and filtering conference deadlines
    with real-time countdown updates.

    Features:
        - Filter by category (10 subcategories) and CCF rank (A, B, C, N)
        - Search conferences by title
        - Real-time countdown to deadlines
        - Language toggle (English/Chinese)
        - Keyboard navigation

    Attributes:
        selected_subs: Reactive set of selected category codes.
        selected_ranks: Reactive set of selected CCF ranks.
        search_query: Reactive search query string.
        language: Reactive language setting ("en" or "zh").
        conferences: Reactive list of filtered conference rows.
    """

    CSS_PATH = "styles.tcss"
    TITLE = "CCF-Deadlines TUI"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("l", "toggle_language", "Language", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("f", "toggle_favorite", "Favorite", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("escape", "clear_search", "Clear Search", show=False),
    ]

    # Reactive state attributes
    selected_subs: set[str] = reactive(lambda: set(cat.sub for cat in CATEGORIES))
    selected_ranks: set[str] = reactive(lambda: {"A", "B", "C", "N"})
    selected_core_ranks: set[str] = reactive(lambda: {"A*", "A", "B", "C", "N"})
    selected_thcpl_ranks: set[str] = reactive(lambda: {"A", "B", "N"})
    show_expired: bool = reactive(False)
    search_query: str = reactive("")
    language: str = reactive("en")
    conferences: list[ConferenceRow] = reactive(list)

    def __init__(self, url: Optional[str] = None) -> None:
        """Initialize the CCF Deadlines app.

        Args:
            url: Optional URL override for conference data. If not provided,
                 uses the default CCFDDL allconf.yml URL.
        """
        super().__init__()
        self.data_service = DataService(url)
        self._all_rows: list[ConferenceRow] = []
        self._is_loading: bool = False
        self._error_message: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Compose the main application layout.

        Layout structure:
            - Header: Title and subtitle with conference count
            - Horizontal container:
                - FilterSidebar (left, 25% width)
                - ConferenceTable (right, 75% width)
            - Footer: Keyboard shortcuts
        """
        yield Header()

        with Horizontal(id="main-container"):
            yield FilterSidebar(id="filter-sidebar")
            with Vertical(id="table-container"):
                yield ConferenceTable(id="conference-table")

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount - load initial data."""
        self._show_loading_in_header()
        self._load_data()

    def _show_loading_in_header(self) -> None:
        """Show loading status in header."""
        if self.language == "zh":
            self.sub_title = "正在加载会议数据..."
        else:
            self.sub_title = "Loading conference data..."

    def _show_error_in_header(self, message: str) -> None:
        """Show error status in header."""
        if self.language == "zh":
            self.sub_title = f"加载失败: {message} (按 r 重试)"
        else:
            self.sub_title = f"Error: {message} (press 'r' to retry)"

    @work(exclusive=True, name="load_data")
    async def _load_data(self) -> None:
        """Load conference data asynchronously.

        Fetches data from the data service, processes it into display rows,
        and updates the table. Handles errors gracefully.
        """
        import asyncio

        self._is_loading = True
        self._error_message = None

        try:
            # Load conferences from URL (run blocking call in thread)
            await asyncio.to_thread(self.data_service.load_conferences)

            # Process into display rows
            now = datetime.now(timezone.utc)
            self._all_rows = await asyncio.to_thread(
                self.data_service.process_rows, now
            )

            # Apply initial filtering and sorting
            self._update_conferences()

            # Update UI
            self._update_table()
            self._update_header()

        except Exception as e:
            self._error_message = str(e)
            self._show_error_in_header(self._error_message)

        finally:
            self._is_loading = False

    def _update_conferences(self) -> None:
        """Apply filters and search to conference data."""
        rows = self._apply_filters(self._all_rows)

        # Apply search
        if self.search_query:
            rows = self.data_service.fuzzy_search(rows, self.search_query)

        # Sort for display
        self.conferences = self.data_service.sort_rows(rows)

    def _apply_filters(self, rows: list[ConferenceRow]) -> list[ConferenceRow]:
        """Apply all active filters to the conference rows.

        Args:
            rows: List of all conference rows.

        Returns:
            Filtered list of rows matching all active filter criteria.
        """
        # Apply category filter
        if self.selected_subs:
            rows = [r for r in rows if r.sub in self.selected_subs]

        # Apply CCF rank filter
        if self.selected_ranks:
            rows = [r for r in rows if r.rank in self.selected_ranks]

        # Apply CORE rank filter
        if self.selected_core_ranks:
            rows = [r for r in rows if r.core_rank in self.selected_core_ranks or r.core_rank is None]

        # Apply THCPL rank filter
        if self.selected_thcpl_ranks:
            rows = [r for r in rows if r.thcpl_rank in self.selected_thcpl_ranks or r.thcpl_rank is None]

        # Apply expired filter (hide expired unless show_expired is True)
        if not self.show_expired:
            rows = [r for r in rows if not r.is_expired]

        return rows

    def _update_table(self) -> None:
        """Update the conference table with current data."""
        try:
            table = self.query_one("#conference-table", ConferenceTable)
            table.update_rows(self.conferences)
        except (RuntimeError, ValueError):
            # Table might not be mounted yet
            pass

    def _update_header(self) -> None:
        """Update the header with current conference count and data source."""
        count = len(self.conferences)
        total = len(self._all_rows)

        # Add indicator for local data fallback
        source_indicator = ""
        if self.data_service.using_local_data:
            source_indicator = " [LOCAL]"

        if self.language == "zh":
            subtitle = f"显示 {count} / {total} 个会议{source_indicator}"
        else:
            subtitle = f"Showing {count} of {total} conferences{source_indicator}"

        self.sub_title = subtitle

    @on(FilterChanged)
    def on_filter_changed(self, event: FilterChanged) -> None:
        """Handle filter change events from the sidebar.

        Updates the reactive state and refreshes the table display.

        Args:
            event: The FilterChanged event containing new filter values.
        """
        self.selected_subs = event.subs
        self.selected_ranks = event.ranks
        self.selected_core_ranks = event.core_ranks
        self.selected_thcpl_ranks = event.thcpl_ranks
        self.show_expired = event.show_expired
        self.search_query = event.query

        self._update_conferences()
        self._update_table()
        self._update_header()

    def action_toggle_language(self) -> None:
        """Toggle between English and Chinese language."""
        self.language = "zh" if self.language == "en" else "en"
        self._update_header()

        # Update filter sidebar labels if needed
        try:
            sidebar = self.query_one("#filter-sidebar", FilterSidebar)
            # Re-render sidebar with new language
            # Note: FilterSidebar currently uses English labels
            pass
        except (RuntimeError, ValueError):
            pass

    def action_refresh(self) -> None:
        """Refresh conference data from source."""
        if self._is_loading:
            return

        self._show_loading_in_header()
        self._load_data()

    def action_show_help(self) -> None:
        """Show help screen with keyboard shortcuts."""
        self.push_screen(HelpScreen())

    def action_clear_search(self) -> None:
        """Clear the search input."""
        try:
            sidebar = self.query_one("#filter-sidebar", FilterSidebar)
            # Reset filters to clear search
            sidebar.reset_filters()
        except (RuntimeError, ValueError):
            pass

    def action_toggle_favorite(self) -> None:
        """Toggle favorite status for the selected conference."""
        try:
            table = self.query_one("#conference-table", ConferenceTable)
            selected_row = table.get_selected_row()

            if selected_row:
                # Toggle favorite in data service
                is_favorite = self.data_service.toggle_favorite(selected_row)

                # Update the row in our data
                for row in self._all_rows:
                    if row.title == selected_row.title and row.year == selected_row.year:
                        row.is_favorite = is_favorite
                        break

                # Re-sort and update display
                self._update_conferences()
                self._update_table()

                # Show notification
                action = "added to" if is_favorite else "removed from"
                self.notify(f"{selected_row.title} {action} favorites")
        except (RuntimeError, ValueError, AttributeError):
            pass

    def watch_language(self, old_language: str, new_language: str) -> None:
        """React to language changes.

        Args:
            old_language: Previous language setting.
            new_language: New language setting.
        """
        # Update window title with language-appropriate text
        if new_language == "zh":
            self.title = "CCF-Deadlines 终端界面"
        else:
            self.title = "CCF-Deadlines TUI"


class HelpScreen(Screen):
    """Help screen showing keyboard shortcuts."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
        height: 100%;
        width: 100%;
        background: $surface;
        padding: 2;
    }

    HelpScreen .help-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    HelpScreen .help-section {
        margin-top: 1;
        margin-bottom: 1;
    }

    HelpScreen .help-section-header {
        text-style: bold;
        color: $text;
    }

    HelpScreen .key-row {
        margin-left: 2;
        color: $text-muted;
    }

    HelpScreen .key {
        color: $primary;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Close", show=True),
        Binding("q", "app.pop_screen", "Close", show=True),
        Binding("?", "app.pop_screen", "Close", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Label("Keyboard Shortcuts", classes="help-title")

        yield Label("Navigation", classes="help-section-header")
        yield Label("  [key]j/k[/key] or [key]↑/↓[/key]  Navigate rows", classes="key-row")
        yield Label("  [key]g[/key]  Go to first row", classes="key-row")
        yield Label("  [key]G[/key]  Go to last row", classes="key-row")

        yield Label("Actions", classes="help-section-header")
        yield Label("  [key]Enter[/key]  Open conference URL", classes="key-row")
        yield Label("  [key]f[/key]  Toggle favorite", classes="key-row")
        yield Label("  [key]l[/key]  Toggle language (EN/ZH)", classes="key-row")
        yield Label("  [key]r[/key]  Refresh data", classes="key-row")
        yield Label("  [key]q[/key]  Quit", classes="key-row")

        yield Label("Search & Filter", classes="help-section-header")
        yield Label("  Type in search box to filter by title", classes="key-row")
        yield Label("  Check/uncheck categories and ranks", classes="key-row")
        yield Label("  [key]Esc[/key]  Clear search", classes="key-row")

        yield Label("", classes="help-section")
        yield Label("Press [key]?[/key] or [key]Esc[/key] to close", classes="key-row")
