"""Conference table widget for displaying conference deadlines."""

import webbrowser
from datetime import datetime, timezone
from typing import Optional

from rich.text import Text
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable

from ..data.data_service import ConferenceRow
from ..utils.formatters import format_deadline_countdown, get_countdown_color


class RowSelected(Message):
    """Message emitted when a conference row is selected."""

    def __init__(self, row: ConferenceRow) -> None:
        self.row = row
        super().__init__()


class ConferenceTable(DataTable):
    """DataTable widget for displaying conference deadlines.

    Features:
        - Real-time countdown updates (refresh every second)
        - Keyboard navigation (j/k, arrows, g/G)
        - Row selection with Enter to open conference URL
        - Zebra striping for readability
        - Color-coded countdown column
        - Sortable columns (click header to sort)
    """

    DEFAULT_CSS = """
    ConferenceTable {
        height: 100%;
        width: 100%;
    }

    ConferenceTable > .datatable--row-even {
        background: $surface;
    }

    ConferenceTable > .datatable--row-odd {
        background: $surface-darken-1;
    }

    ConferenceTable > .datatable--cursor {
        background: $primary-darken-2;
        color: $text;
    }

    ConferenceTable:focus > .datatable--hover {
        background: $primary-darken-1;
    }

    ConferenceTable > .datatable--header {
        text-style: bold;
        background: $surface-darken-2;
        color: $accent;
    }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("enter", "open_url", "Open URL", show=True),
        Binding("g", "go_top", "Top", show=False),
        Binding("G", "go_bottom", "Bottom", show=False),
    ]

    rows_data: list[ConferenceRow] = reactive(list)

    COLUMN_TITLE = 0
    COLUMN_SUB = 1
    COLUMN_RANK = 2
    COLUMN_COUNTDOWN = 3
    COLUMN_DATE = 4
    COLUMN_PLACE = 5

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            zebra_stripes=True,
            show_cursor=True,
            cursor_type="row",
        )
        self._sort_column: int = self.COLUMN_COUNTDOWN
        self._sort_reverse: bool = False
        self._pending_rows: list[ConferenceRow] = []

    def on_mount(self) -> None:
        self.add_columns(
            "★", "Title", "Sub", "CCF", "CORE", "THCPL", "Countdown", "Date", "Place"
        )
        self.set_interval(1, self._refresh_countdowns)
        if self._pending_rows:
            self._do_update_rows(self._pending_rows)
            self._pending_rows = []

    def update_rows(self, rows: list[ConferenceRow]) -> None:
        if len(self.columns) == 0:
            self._pending_rows = rows
            self.rows_data = rows
            return
        self._do_update_rows(rows)

    def _do_update_rows(self, rows: list[ConferenceRow]) -> None:
        self.rows_data = rows
        self.clear()
        if not rows:
            return
        sorted_rows = self._sort_rows(rows.copy())
        for row in sorted_rows:
            self.add_row(
                self._format_favorite(row),
                self._format_title(row),
                self._format_sub(row),
                self._format_ccf_rank(row),
                self._format_core_rank(row),
                self._format_thcpl_rank(row),
                self._format_countdown(row),
                self._format_date(row),
                self._format_place(row),
            )

    def _sort_rows(self, rows: list[ConferenceRow]) -> list[ConferenceRow]:
        if not rows:
            return rows

        def sort_key(row: ConferenceRow):
            if self._sort_column == self.COLUMN_TITLE:
                return row.title.lower()
            elif self._sort_column == self.COLUMN_SUB:
                return row.sub
            elif self._sort_column == self.COLUMN_RANK:
                rank_order = {"A": 0, "B": 1, "C": 2, "N": 3}
                return rank_order.get(row.rank, 4)
            elif self._sort_column == self.COLUMN_COUNTDOWN:
                if row.deadline is None:
                    return datetime.max.replace(tzinfo=timezone.utc)
                return row.deadline
            elif self._sort_column == self.COLUMN_DATE:
                return row.date
            elif self._sort_column == self.COLUMN_PLACE:
                return row.place.lower()
            return ""

        return sorted(rows, key=sort_key, reverse=self._sort_reverse)

    def _refresh_countdowns(self) -> None:
        if not self.rows_data or len(self.columns) == 0:
            return

        now = datetime.now(timezone.utc)
        sorted_rows = self._sort_rows(self.rows_data.copy())

        for idx, row in enumerate(sorted_rows):
            if idx < self.row_count:
                countdown_text = self._format_countdown_live(row, now)
                try:
                    self.update_cell(
                        row_key=self.get_row_at(idx),
                        column_key=self.COLUMN_COUNTDOWN,
                        value=countdown_text,
                    )
                except Exception:
                    pass

    def _format_title(self, row: ConferenceRow) -> Text:
        title = f"{row.title} {row.year}"
        if row.is_running and not row.is_tbd:
            return Text(title, style="bold")
        return Text(title, style="dim")

    def _format_sub(self, row: ConferenceRow) -> Text:
        return Text(row.sub, style="cyan")

    def _format_rank(self, row: ConferenceRow) -> Text:
        rank_colors = {
            "A": "red",
            "B": "yellow",
            "C": "green",
            "N": "dim",
        }
        color = rank_colors.get(row.rank, "white")
        return Text(f"CCF {row.rank}", style=color)

    def _format_favorite(self, row: ConferenceRow) -> Text:
        """Format favorite indicator."""
        if row.is_favorite:
            return Text("★", style="yellow")
        return Text("☆", style="dim")

    def _format_ccf_rank(self, row: ConferenceRow) -> Text:
        """Format CCF rank."""
        rank_colors = {
            "A": "red",
            "B": "yellow",
            "C": "green",
            "N": "dim",
        }
        color = rank_colors.get(row.rank, "white")
        return Text(row.rank, style=color)

    def _format_core_rank(self, row: ConferenceRow) -> Text:
        """Format CORE rank."""
        if not row.core_rank:
            return Text("-", style="dim")
        rank_colors = {
            "A*": "red bold",
            "A": "red",
            "B": "yellow",
            "C": "green",
            "N": "dim",
        }
        color = rank_colors.get(row.core_rank, "white")
        return Text(row.core_rank, style=color)

    def _format_thcpl_rank(self, row: ConferenceRow) -> Text:
        """Format THCPL rank."""
        if not row.thcpl_rank:
            return Text("-", style="dim")
        rank_colors = {
            "A": "red",
            "B": "yellow",
            "N": "dim",
        }
        color = rank_colors.get(row.thcpl_rank, "white")
        return Text(row.thcpl_rank, style=color)

    def _format_countdown(self, row: ConferenceRow) -> Text:
        """Format countdown for initial display."""
        return format_deadline_countdown(
            deadline=row.deadline,
            is_tbd=row.is_tbd,
        )

    def _format_countdown_live(self, row: ConferenceRow, now: datetime) -> Text:
        """Format countdown for live refresh."""
        return format_deadline_countdown(
            deadline=row.deadline,
            is_tbd=row.is_tbd,
            now=now,
        )

    def _format_date(self, row: ConferenceRow) -> Text:
        return Text(row.date, style="white")

    def _format_place(self, row: ConferenceRow) -> Text:
        return Text(row.place, style="white dim")

    def action_cursor_down(self) -> None:
        if self.row_count == 0:
            return
        current = self.cursor_coordinate
        new_row = min(current.row + 1, self.row_count - 1)
        self.cursor_coordinate = Coordinate(new_row, current.column)

    def action_cursor_up(self) -> None:
        if self.row_count == 0:
            return
        current = self.cursor_coordinate
        new_row = max(current.row - 1, 0)
        self.cursor_coordinate = Coordinate(new_row, current.column)

    def action_go_top(self) -> None:
        if self.row_count > 0:
            self.cursor_coordinate = Coordinate(0, 0)

    def action_go_bottom(self) -> None:
        if self.row_count > 0:
            self.cursor_coordinate = Coordinate(self.row_count - 1, 0)

    def action_open_url(self) -> None:
        if not self.rows_data:
            return

        cursor_row_idx = self.cursor_coordinate.row
        sorted_rows = self._sort_rows(self.rows_data)

        if cursor_row_idx < len(sorted_rows):
            row = sorted_rows[cursor_row_idx]
            if row.link:
                webbrowser.open(row.link)
                self.post_message(RowSelected(row))

    def on_data_table_header_selected(
        self, event: DataTable.HeaderSelected
    ) -> None:
        column_idx = event.column_index

        if column_idx == self._sort_column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column_idx
            self._sort_reverse = False

        self._do_update_rows(self.rows_data)

    def get_selected_row(self) -> Optional[ConferenceRow]:
        if not self.rows_data:
            return None

        cursor_row_idx = self.cursor_coordinate.row
        sorted_rows = self._sort_rows(self.rows_data)

        if cursor_row_idx < len(sorted_rows):
            return sorted_rows[cursor_row_idx]
        return None

    def get_row_count(self) -> int:
        return len(self.rows_data)

    def has_rows(self) -> bool:
        return len(self.rows_data) > 0

    def clear_rows(self) -> None:
        self.rows_data = []
        self._pending_rows = []
        if len(self.columns) > 0:
            self.clear()
