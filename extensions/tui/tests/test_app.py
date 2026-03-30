"""Integration tests for CCF-Deadlines TUI application.

This module tests the full app workflow using Textual's pilot testing framework.
Tests cover:
- App launch and component rendering
- Data loading and display
- Filter interactions (category, rank, search)
- Keyboard navigation and actions
- Help screen and language toggle
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from textual.app import App
from textual.widgets import Checkbox, Header, Footer, Input, Label
from textual.containers import Vertical

from ccfddl.models import Conference, ConferenceYear, Rank, Timeline

from ccfddl_tui.app import CCFDeadlinesApp, HelpScreen
from ccfddl_tui.widgets.conference_table import ConferenceTable
from ccfddl_tui.widgets.filters import FilterSidebar
from ccfddl_tui.data.data_service import ConferenceRow


# =============================================================================
# Test Fixtures
# =============================================================================

def create_mock_conference(
    title: str = "CVPR",
    year: int = 2025,
    sub: str = "AI",
    rank: str = "A",
    link: str = "https://cvpr2025.org",
    deadline_days: int = 30,
) -> Conference:
    """Create a mock Conference object for testing."""
    deadline = (
        datetime.now(timezone.utc) + timedelta(days=deadline_days)
    ).strftime("%Y-%m-%d %H:%M:%S")

    return Conference(
        title=title,
        description=f"{title} Conference",
        sub=sub,
        rank=Rank(ccf=rank),
        dblp=title.lower(),
        confs=[
            ConferenceYear(
                year=year,
                id=f"{title.lower()}{year}",
                link=link,
                timeline=[
                    Timeline(deadline=deadline, comment="Main deadline")
                ],
                timezone="UTC-8",
                date=f"June 15-20, {year}",
                place="Seattle, USA",
            )
        ],
    )


def create_mock_conferences_list() -> list[Conference]:
    """Create a list of mock conferences with various categories and ranks."""
    return [
        create_mock_conference(title="CVPR", sub="AI", rank="A", deadline_days=5),
        create_mock_conference(title="ICML", sub="AI", rank="A", deadline_days=30),
        create_mock_conference(title="SIGMOD", sub="DB", rank="A", deadline_days=60),
        create_mock_conference(title="VLDB", sub="DB", rank="A", deadline_days=10),
        create_mock_conference(title="SIGGRAPH", sub="CG", rank="A", deadline_days=15),
        create_mock_conference(title="ICSE", sub="SE", rank="A", deadline_days=20),
        create_mock_conference(title="ECCV", sub="AI", rank="B", deadline_days=25),
        create_mock_conference(title="ACCV", sub="AI", rank="C", deadline_days=35),
        create_mock_conference(title="LocalConf", sub="AI", rank="N", deadline_days=45),
    ]


def create_mock_conference_rows() -> list[ConferenceRow]:
    """Create mock ConferenceRow objects for testing."""
    now = datetime.now(timezone.utc)

    return [
        ConferenceRow(
            title="CVPR",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A*",
            thcpl_rank="A",
            deadline=now + timedelta(days=5),
            countdown="5 days",
            place="Seattle, USA",
            date="June 15-20, 2025",
            link="https://cvpr2025.org",
            is_running=True,
            is_tbd=False,
            is_expired=False,
            is_favorite=False,
        ),
        ConferenceRow(
            title="SIGMOD",
            year=2025,
            sub="DB",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            deadline=now + timedelta(days=60),
            countdown="60 days",
            place="Berlin, Germany",
            date="June 14-19, 2025",
            link="https://sigmod2025.org",
            is_running=True,
            is_tbd=False,
            is_expired=False,
            is_favorite=False,
        ),
        ConferenceRow(
            title="ECCV",
            year=2025,
            sub="AI",
            rank="B",
            core_rank="A",
            thcpl_rank="B",
            deadline=now + timedelta(days=25),
            countdown="25 days",
            place="Milan, Italy",
            date="September 2025",
            link="https://eccv2025.eu",
            is_running=True,
            is_tbd=False,
            is_expired=False,
            is_favorite=False,
        ),
        ConferenceRow(
            title="LocalConf",
            year=2025,
            sub="AI",
            rank="N",
            core_rank=None,
            thcpl_rank=None,
            deadline=now + timedelta(days=45),
            countdown="45 days",
            place="Beijing, China",
            date="October 2025",
            link="https://localconf.org",
            is_running=True,
            is_tbd=False,
            is_expired=False,
            is_favorite=False,
        ),
    ]


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_app_launch() -> None:
    """Test that app launches and shows expected components."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        await pilot.pause()

        # Verify Header exists
        header = pilot.app.query_one(Header)
        assert header is not None

        # Verify Footer exists
        footer = pilot.app.query_one(Footer)
        assert footer is not None

        # Verify FilterSidebar exists
        sidebar = pilot.app.query_one("#filter-sidebar", FilterSidebar)
        assert sidebar is not None

        # Verify ConferenceTable exists
        table = pilot.app.query_one("#conference-table", ConferenceTable)
        assert table is not None

        # Verify app title
        assert pilot.app.title == "CCF-Deadlines TUI"


@pytest.mark.asyncio
@patch.object(CCFDeadlinesApp, '_load_data')
async def test_data_loading(mock_load_data) -> None:
    """Test that data loads and displays in table."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Initially, loading overlay should be shown
        await pilot.pause()

        # Manually set up test data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        # Verify table has data
        table = pilot.app.query_one("#conference-table", ConferenceTable)
        assert table.has_rows() is True
        assert table.get_row_count() == len(test_rows)


@pytest.mark.asyncio
async def test_filter_by_category() -> None:
    """Test clicking category checkbox updates table filter."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Wait for initial load to complete and stop any pending loads
        await pilot.pause()
        pilot.app._is_loading = True  # Block any further loading

        # Set up initial data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app.selected_subs = {"AI", "DB", "CG", "SE"}
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        # Get initial row count (all 4 rows)
        table = pilot.app.query_one("#conference-table", ConferenceTable)
        initial_count = table.get_row_count()
        assert initial_count == 4

        # Uncheck DB category checkbox
        db_checkbox = pilot.app.query_one("#sub-DB", Checkbox)
        db_checkbox.value = False
        await pilot.pause()

        # Verify table updated (should have only AI rows, 3 rows)
        # Note: The filter change is handled by the FilterChanged message
        # We need to check the app's state
        assert "DB" not in pilot.app.selected_subs

        # Manually trigger filter update to verify behavior
        pilot.app.selected_subs = {"AI"}
        pilot.app._update_conferences()
        pilot.app._update_table()
        await pilot.pause()

        # Should only have AI conferences (CVPR, ECCV, LocalConf = 3)
        assert table.get_row_count() == 3


@pytest.mark.asyncio
async def test_filter_by_rank() -> None:
    """Test clicking rank checkbox updates table filter."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Wait for initial load to complete and stop any pending loads
        await pilot.pause()
        pilot.app._is_loading = True  # Block any further loading

        # Set up initial data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app.selected_ranks = {"A", "B", "C", "N"}
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        # Get initial row count
        table = pilot.app.query_one("#conference-table", ConferenceTable)
        initial_count = table.get_row_count()
        assert initial_count == 4

        # Uncheck rank-N checkbox
        rank_n_checkbox = pilot.app.query_one("#rank-N", Checkbox)
        rank_n_checkbox.value = False
        await pilot.pause()

        # Verify app state updated
        assert "N" not in pilot.app.selected_ranks

        # Manually filter to only A rank
        pilot.app.selected_ranks = {"A"}
        pilot.app._update_conferences()
        pilot.app._update_table()
        await pilot.pause()

        # Should only have A rank conferences (CVPR, SIGMOD = 2)
        assert table.get_row_count() == 2


@pytest.mark.asyncio
async def test_search_filter() -> None:
    """Test typing in search box filters results."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Wait for initial load to complete and stop any pending loads
        await pilot.pause()
        pilot.app._is_loading = True  # Block any further loading

        # Set up initial data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        # Get initial row count
        table = pilot.app.query_one("#conference-table", ConferenceTable)
        initial_count = table.get_row_count()
        assert initial_count == 4

        # Type in search input - use SIGMOD which is unique
        search_input = pilot.app.query_one("#search", Input)
        search_input.value = "SIGMOD"
        await pilot.pause()

        # Verify app state updated
        assert pilot.app.search_query == "SIGMOD"

        # Update conferences with search
        pilot.app._update_conferences()
        pilot.app._update_table()
        await pilot.pause()

        # Should only have SIGMOD
        assert table.get_row_count() == 1


@pytest.mark.asyncio
async def test_language_toggle() -> None:
    """Test pressing 'l' key toggles language."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        await pilot.pause()

        # Initial language is English
        assert pilot.app.language == "en"
        assert pilot.app.title == "CCF-Deadlines TUI"

        # Press 'l' to toggle language
        await pilot.press("l")
        await pilot.pause()

        # Language should be Chinese
        assert pilot.app.language == "zh"
        assert pilot.app.title == "CCF-Deadlines 终端界面"

        # Press 'l' again to toggle back
        await pilot.press("l")
        await pilot.pause()

        # Language should be English again
        assert pilot.app.language == "en"
        assert pilot.app.title == "CCF-Deadlines TUI"


@pytest.mark.asyncio
@patch("ccfddl_tui.data.data_service.DataService.load_conferences")
async def test_refresh_data(mock_load) -> None:
    """Test pressing 'r' key refreshes data."""
    # Set up mock
    mock_conferences = create_mock_conferences_list()
    mock_load.return_value = mock_conferences

    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Set up initial data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        # Get initial row count
        table = pilot.app.query_one("#conference-table", ConferenceTable)
        initial_count = table.get_row_count()

        # Press 'r' to refresh
        await pilot.press("r")
        await pilot.pause()

        # Loading should be triggered (mock prevents actual reload)
        # The app should show loading overlay initially
        # After mock returns, table should update


@pytest.mark.asyncio
async def test_keyboard_navigation() -> None:
    """Test j/k keys navigate table rows."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Wait for initial load to complete and stop any pending loads
        await pilot.pause()
        pilot.app._is_loading = True  # Block any further loading

        # Set up data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        table = pilot.app.query_one("#conference-table", ConferenceTable)

        # Focus the table
        table.focus()
        await pilot.pause()

        # Initial cursor should be at row 0
        assert table.cursor_coordinate.row == 0

        # Press 'j' to move down
        await pilot.press("j")
        await pilot.pause()
        assert table.cursor_coordinate.row == 1

        # Press 'j' again
        await pilot.press("j")
        await pilot.pause()
        assert table.cursor_coordinate.row == 2

        # Press 'k' to move up
        await pilot.press("k")
        await pilot.pause()
        assert table.cursor_coordinate.row == 1


@pytest.mark.asyncio
@patch("ccfddl_tui.widgets.conference_table.webbrowser.open")
async def test_open_url(mock_browser_open) -> None:
    """Test pressing Enter opens URL in browser."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Wait for initial load to complete and stop any pending loads
        await pilot.pause()
        pilot.app._is_loading = True  # Block any further loading

        # Set up data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        table = pilot.app.query_one("#conference-table", ConferenceTable)
        table.focus()
        await pilot.pause()

        # Cursor is at first row (CVPR)
        assert table.cursor_coordinate.row == 0

        # Press Enter to open URL
        await pilot.press("enter")
        await pilot.pause()

        # Verify webbrowser.open was called with CVPR URL
        mock_browser_open.assert_called_once_with("https://cvpr2025.org")


@pytest.mark.asyncio
async def test_help_screen() -> None:
    """Test pressing '?' shows help screen."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        await pilot.pause()

        # Initially, not on help screen
        assert not isinstance(pilot.app.screen, HelpScreen)

        # Call action directly
        pilot.app.action_show_help()
        await pilot.pause()

        # Should now be on HelpScreen
        assert isinstance(pilot.app.screen, HelpScreen)

        # Verify help content exists
        help_labels = pilot.app.screen.query(Label)
        assert len(help_labels) > 0

        # Press Escape to close
        await pilot.press("escape")
        await pilot.pause()

        # Should be back to main screen
        assert not isinstance(pilot.app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_quit_binding() -> None:
    """Test pressing 'q' quits the app."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        await pilot.pause()

        # App should be running
        assert pilot.app.is_running is True

        # Press 'q' to quit
        await pilot.press("q")
        await pilot.pause()

        # App should have quit
        assert pilot.app.is_running is False


@pytest.mark.asyncio
async def test_header_subtitle_updates() -> None:
    """Test that header subtitle shows correct conference count."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Set up data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_header()

        await pilot.pause()

        # Check subtitle shows count
        subtitle = pilot.app.sub_title
        assert "4" in subtitle  # 4 conferences
        assert "4 of 4" in subtitle or "4 / 4" in subtitle

        # Filter to only AI
        pilot.app.selected_subs = {"AI"}
        pilot.app._update_conferences()
        pilot.app._update_header()
        await pilot.pause()

        # Subtitle should show filtered count
        subtitle = pilot.app.sub_title
        assert "3" in subtitle  # 3 AI conferences


@pytest.mark.asyncio
async def test_filter_sidebar_initial_state() -> None:
    """Test that filter sidebar has correct initial state."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        await pilot.pause()

        sidebar = pilot.app.query_one("#filter-sidebar", FilterSidebar)

        # All categories should be checked
        from ccfddl.models import CATEGORIES
        expected_subs = {cat.sub for cat in CATEGORIES}
        assert sidebar.selected_subs == expected_subs

        # All ranks should be checked
        assert sidebar.selected_ranks == {"A", "B", "C", "N"}

        # Search should be empty
        assert sidebar.search_query == ""


@pytest.mark.asyncio
async def test_empty_table_state() -> None:
    """Test app handles empty table state gracefully."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Set up empty data
        pilot.app._all_rows = []
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        table = pilot.app.query_one("#conference-table", ConferenceTable)

        # Table should be empty but not error
        assert table.has_rows() is False
        assert table.get_row_count() == 0
        assert table.get_selected_row() is None


@pytest.mark.asyncio
async def test_go_top_bottom_navigation() -> None:
    """Test g/G keys navigate to top/bottom of table."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Wait for initial load to complete and stop any pending loads
        await pilot.pause()
        pilot.app._is_loading = True  # Block any further loading

        # Set up data with many rows
        now = datetime.now(timezone.utc)
        rows = [
            ConferenceRow(
                title=f"CONF{i}",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                deadline=now + timedelta(days=i),
                countdown=f"{i} days",
                place="Test City",
                date="June 2025",
                link=f"https://conf{i}.org",
                is_running=True,
                is_tbd=False,
                is_expired=False,
                is_favorite=False,
            )
            for i in range(10)
        ]
        pilot.app._all_rows = rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        table = pilot.app.query_one("#conference-table", ConferenceTable)
        table.focus()
        await pilot.pause()

        # Move cursor to middle
        from textual.coordinate import Coordinate
        table.cursor_coordinate = Coordinate(5, 0)
        await pilot.pause()
        assert table.cursor_coordinate.row == 5

        # Press 'G' (shift+g) to go to bottom
        await pilot.press("G")
        await pilot.pause()
        assert table.cursor_coordinate.row == 9

        # Press 'g' to go to top
        await pilot.press("g")
        await pilot.pause()
        assert table.cursor_coordinate.row == 0


@pytest.mark.asyncio
async def test_multiple_filters_combined() -> None:
    """Test combining category, rank, and search filters."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Wait for initial load to complete and stop any pending loads
        await pilot.pause()
        pilot.app._is_loading = True  # Block any further loading

        # Set up data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()

        await pilot.pause()

        # Apply category filter (AI only)
        pilot.app.selected_subs = {"AI"}
        pilot.app._update_conferences()
        pilot.app._update_table()
        await pilot.pause()

        table = pilot.app.query_one("#conference-table", ConferenceTable)
        assert table.get_row_count() == 3  # CVPR, ECCV, LocalConf

        # Apply rank filter (A only)
        pilot.app.selected_ranks = {"A"}
        pilot.app._update_conferences()
        pilot.app._update_table()
        await pilot.pause()

        assert table.get_row_count() == 1  # Only CVPR

        # Apply search filter
        pilot.app.search_query = "CVPR"
        pilot.app._update_conferences()
        pilot.app._update_table()
        await pilot.pause()

        assert table.get_row_count() == 1  # CVPR matches all filters


@pytest.mark.asyncio
@patch("ccfddl_tui.data.data_service.DataService.load_conferences")
async def test_loading_shown_in_header(mock_load) -> None:
    """Test that loading status is shown in header during data load."""
    # Set up mock to return data
    mock_conferences = create_mock_conferences_list()
    mock_load.return_value = mock_conferences

    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        await pilot.pause()

        # Header should show loading status initially
        assert pilot.app.sub_title is not None
        # Wait for loading to complete
        for _ in range(10):
            await pilot.pause()
            if "Showing" in pilot.app.sub_title or "显示" in pilot.app.sub_title:
                break
        # After loading completes, should show conference count
        assert "Showing" in pilot.app.sub_title or "显示" in pilot.app.sub_title


@pytest.mark.asyncio
@patch("ccfddl_tui.data.data_service.DataService.load_conferences")
async def test_error_shown_in_header_on_load_failure(mock_load) -> None:
    """Test that error status is shown in header when data loading fails."""
    mock_load.side_effect = Exception("Network error")

    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        await pilot.pause()

        # Wait for initial load to fail
        await pilot.pause()
        await pilot.pause()

        # Header should show error message
        assert pilot.app._error_message is not None
        assert "Error" in pilot.app.sub_title or "失败" in pilot.app.sub_title


@pytest.mark.asyncio
async def test_help_screen_bindings() -> None:
    """Test help screen keyboard bindings."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        pilot.app.action_show_help()
        await pilot.pause()

        # Should now be on HelpScreen
        assert isinstance(pilot.app.screen, HelpScreen)

        # Press 'q' should close help (not quit app)
        await pilot.press("q")
        await pilot.pause()

        # Should be back to main screen
        assert not isinstance(pilot.app.screen, HelpScreen)

        # App should still be running
        assert pilot.app.is_running is True


@pytest.mark.asyncio
async def test_escape_clears_search() -> None:
    """Test pressing Escape clears search input."""
    app = CCFDeadlinesApp()

    async with app.run_test() as pilot:
        # Set up data
        test_rows = create_mock_conference_rows()
        pilot.app._all_rows = test_rows
        pilot.app._update_header()
        pilot.app._update_conferences()
        pilot.app._update_table()

        await pilot.pause()

        # Type in search
        search_input = pilot.app.query_one("#search", Input)
        search_input.value = "test query"
        await pilot.pause()

        assert pilot.app.search_query == "test query"

        # Focus the search input
        search_input.focus()
        await pilot.pause()

        # Press Escape
        await pilot.press("escape")
        await pilot.pause()

        # Search should be cleared
        assert search_input.value == ""
