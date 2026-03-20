"""Tests for ConferenceTable widget."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.coordinate import Coordinate

from ccfddl_tui.widgets.conference_table import ConferenceTable, RowSelected
from ccfddl_tui.data.data_service import ConferenceRow
from ccfddl_tui.utils.formatters import get_countdown_color, format_time_remaining


def create_test_row(
    title: str = "CVPR",
    year: int = 2025,
    sub: str = "AI",
    rank: str = "A",
    days_until_deadline: int | None = 30,
    place: str = "Seattle, USA",
    date: str = "June 2025",
    link: str = "https://cvpr2025.org",
) -> ConferenceRow:
    if days_until_deadline is None:
        deadline = None
        is_tbd = True
        is_running = True
        is_expired = False
    elif days_until_deadline < 0:
        deadline = datetime.now(timezone.utc) + timedelta(days=days_until_deadline)
        is_tbd = False
        is_running = False
        is_expired = True
    else:
        deadline = datetime.now(timezone.utc) + timedelta(days=days_until_deadline)
        is_tbd = False
        is_running = True
        is_expired = False

    return ConferenceRow(
        title=title,
        year=year,
        sub=sub,
        rank=rank,
        core_rank="A",
        thcpl_rank="A",
        deadline=deadline,
        countdown="",
        place=place,
        date=date,
        link=link,
        is_running=is_running,
        is_tbd=is_tbd,
        is_expired=is_expired,
        is_favorite=False,
    )


class TestConferenceTable:
    def test_import(self) -> None:
        assert ConferenceTable is not None

    def test_row_selected_message(self) -> None:
        row = create_test_row()
        msg = RowSelected(row)
        assert msg.row == row
        assert msg.row.title == "CVPR"

    def test_initialization(self) -> None:
        table = ConferenceTable()
        assert table.rows_data == []
        assert table._sort_column == ConferenceTable.COLUMN_COUNTDOWN

    def test_column_constants(self) -> None:
        assert ConferenceTable.COLUMN_TITLE == 0
        assert ConferenceTable.COLUMN_SUB == 1
        assert ConferenceTable.COLUMN_RANK == 2
        assert ConferenceTable.COLUMN_COUNTDOWN == 3
        assert ConferenceTable.COLUMN_DATE == 4
        assert ConferenceTable.COLUMN_PLACE == 5

    def test_bindings_defined(self) -> None:
        bindings = ConferenceTable.BINDINGS
        binding_keys = [b.key for b in bindings]
        assert "j" in binding_keys
        assert "k" in binding_keys
        assert "enter" in binding_keys
        assert "g" in binding_keys
        assert "G" in binding_keys

    def test_update_rows(self) -> None:
        table = ConferenceTable()
        rows = [
            create_test_row(title="CVPR", rank="A"),
            create_test_row(title="ICML", rank="A"),
        ]
        table.update_rows(rows)
        assert len(table.rows_data) == 2

    def test_has_rows(self) -> None:
        table = ConferenceTable()
        assert table.has_rows() is False

        table.update_rows([create_test_row()])
        assert table.has_rows() is True

    def test_get_row_count(self) -> None:
        table = ConferenceTable()
        assert table.get_row_count() == 0

        rows = [create_test_row(title=f"CONF{i}") for i in range(5)]
        table.update_rows(rows)
        assert table.get_row_count() == 5

    def test_clear_rows(self) -> None:
        table = ConferenceTable()
        table.update_rows([create_test_row()])
        assert len(table.rows_data) == 1

        table.clear_rows()
        assert table.has_rows() is False

    def test_format_countdown_tbd(self) -> None:
        table = ConferenceTable()
        row = create_test_row(days_until_deadline=None)
        result = table._format_countdown_live(row, datetime.now(timezone.utc))
        assert result.plain == "TBD"

    def test_format_countdown_expired(self) -> None:
        table = ConferenceTable()
        row = create_test_row(days_until_deadline=-1)
        result = table._format_countdown_live(row, datetime.now(timezone.utc))
        assert result.plain == "Expired"

    def test_format_countdown_running(self) -> None:
        table = ConferenceTable()
        row = create_test_row(days_until_deadline=5)
        result = table._format_countdown_live(row, datetime.now(timezone.utc))
        assert "day" in result.plain

    def test_countdown_color_red(self) -> None:
        """Test countdown color is red for < 1 day."""
        assert get_countdown_color(0) == "red"
        assert get_countdown_color(-1) == "red"

    def test_countdown_color_yellow(self) -> None:
        """Test countdown color is yellow for 1-6 days."""
        assert get_countdown_color(1) == "yellow"
        assert get_countdown_color(3) == "yellow"
        assert get_countdown_color(6) == "yellow"

    def test_countdown_color_blue(self) -> None:
        """Test countdown color is blue for 7-29 days."""
        assert get_countdown_color(7) == "blue"
        assert get_countdown_color(15) == "blue"
        assert get_countdown_color(29) == "blue"

    def test_countdown_color_green(self) -> None:
        """Test countdown color is green for 30+ days."""
        assert get_countdown_color(30) == "green"
        assert get_countdown_color(100) == "green"

    def test_format_time_less_than_day(self) -> None:
        """Test time formatting for less than 1 day."""
        result = format_time_remaining(0, 18000)
        assert "05:" in result

    def test_format_time_more_than_day(self) -> None:
        """Test time formatting for more than 1 day."""
        result = format_time_remaining(5, 432000)
        assert "5 day" in result

    def test_format_rank(self) -> None:
        table = ConferenceTable()
        row_a = create_test_row(rank="A")
        result_a = table._format_rank(row_a)
        assert "CCF A" in result_a.plain

        row_b = create_test_row(rank="B")
        result_b = table._format_rank(row_b)
        assert "CCF B" in result_b.plain

    def test_sort_rows_by_title(self) -> None:
        table = ConferenceTable()
        table._sort_column = ConferenceTable.COLUMN_TITLE
        table._sort_reverse = False

        rows = [
            create_test_row(title="ZZZ"),
            create_test_row(title="AAA"),
            create_test_row(title="MMM"),
        ]
        sorted_rows = table._sort_rows(rows)
        assert sorted_rows[0].title == "AAA"
        assert sorted_rows[2].title == "ZZZ"

    def test_sort_rows_by_rank(self) -> None:
        table = ConferenceTable()
        table._sort_column = ConferenceTable.COLUMN_RANK
        table._sort_reverse = False

        rows = [
            create_test_row(rank="N"),
            create_test_row(rank="A"),
            create_test_row(rank="B"),
            create_test_row(rank="C"),
        ]
        sorted_rows = table._sort_rows(rows)
        assert sorted_rows[0].rank == "A"
        assert sorted_rows[1].rank == "B"
        assert sorted_rows[2].rank == "C"
        assert sorted_rows[3].rank == "N"


class ConferenceTableApp(App):
    def compose(self) -> ComposeResult:
        yield ConferenceTable()


@pytest.mark.asyncio
async def test_widget_mounts_successfully() -> None:
    app = ConferenceTableApp()
    async with app.run_test() as pilot:
        widget = app.query_one(ConferenceTable)
        assert widget is not None
        assert widget.has_rows() is False


@pytest.mark.asyncio
async def test_update_rows_renders() -> None:
    app = ConferenceTableApp()
    async with app.run_test() as pilot:
        widget = app.query_one(ConferenceTable)
        rows = [
            create_test_row(title="CVPR"),
            create_test_row(title="ICML"),
        ]
        widget.update_rows(rows)
        assert widget.get_row_count() == 2


@pytest.mark.asyncio
async def test_keyboard_navigation() -> None:
    app = ConferenceTableApp()
    async with app.run_test() as pilot:
        widget = app.query_one(ConferenceTable)
        rows = [create_test_row(title=f"CONF{i}") for i in range(5)]
        widget.update_rows(rows)

        await pilot.press("down")
        assert widget.cursor_coordinate.row == 1

        await pilot.press("down")
        assert widget.cursor_coordinate.row == 2

        await pilot.press("up")
        assert widget.cursor_coordinate.row == 1


@pytest.mark.asyncio
async def test_go_top_bottom() -> None:
    app = ConferenceTableApp()
    async with app.run_test() as pilot:
        widget = app.query_one(ConferenceTable)
        rows = [create_test_row(title=f"CONF{i}") for i in range(10)]
        widget.update_rows(rows)

        widget.cursor_coordinate = Coordinate(5, 0)

        widget.action_go_bottom()
        assert widget.cursor_coordinate.row == 9

        widget.action_go_top()
        assert widget.cursor_coordinate.row == 0


@pytest.mark.asyncio
@patch("ccfddl_tui.widgets.conference_table.webbrowser.open")
async def test_open_url(mock_browser_open) -> None:
    app = ConferenceTableApp()
    async with app.run_test() as pilot:
        widget = app.query_one(ConferenceTable)
        rows = [create_test_row(title="CVPR", link="https://cvpr2025.org")]
        widget.update_rows(rows)

        widget.cursor_coordinate = Coordinate(0, 0)

        await pilot.press("enter")

        mock_browser_open.assert_called_once_with("https://cvpr2025.org")


@pytest.mark.asyncio
async def test_empty_state() -> None:
    app = ConferenceTableApp()
    async with app.run_test() as pilot:
        widget = app.query_one(ConferenceTable)
        assert widget.has_rows() is False
        assert widget.get_row_count() == 0
        assert widget.get_selected_row() is None