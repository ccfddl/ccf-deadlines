"""Filter widgets for CCF Deadlines TUI.

This module provides filter sidebar widgets for filtering conferences
by category, rank, and search query.
"""

from typing import Set

from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Checkbox, Input, Label, Static

from ccfddl.models import CATEGORIES


class FilterChanged(Message):
    """Message emitted when filter state changes.

    Attributes:
        subs: Set of selected category codes (e.g., {"AI", "DB"}).
        ranks: Set of selected CCF ranks (e.g., {"A", "B"}).
        core_ranks: Set of selected CORE ranks.
        thcpl_ranks: Set of selected THCPL ranks.
        show_expired: Whether to show expired conferences.
        query: Search query string.
    """

    def __init__(
        self, 
        subs: Set[str], 
        ranks: Set[str], 
        core_ranks: Set[str],
        thcpl_ranks: Set[str],
        show_expired: bool,
        query: str
    ) -> None:
        """Initialize the FilterChanged message.

        Args:
            subs: Set of selected category codes.
            ranks: Set of selected CCF ranks.
            core_ranks: Set of selected CORE ranks.
            thcpl_ranks: Set of selected THCPL ranks.
            show_expired: Whether to show expired conferences.
            query: Search query string.
        """
        self.subs = subs
        self.ranks = ranks
        self.core_ranks = core_ranks
        self.thcpl_ranks = thcpl_ranks
        self.show_expired = show_expired
        self.query = query
        super().__init__()


class FilterSidebar(Vertical):
    """Sidebar widget containing category, rank filters and search input.

    This widget provides a vertical sidebar with:
        - Category checkboxes (10 categories from CATEGORIES)
        - Rank checkboxes (A, B, C, N)
        - Search input field

    All checkboxes are checked by default. Changes to any filter emit
    a FilterChanged message with the current filter state.

    Attributes:
        selected_subs: Reactive set of selected category codes.
        selected_ranks: Reactive set of selected CCF ranks.
        search_query: Reactive search query string.
    """

    DEFAULT_CSS = """
    FilterSidebar {
        width: 45;
        height: 100%;
        padding: 1;
        background: $surface;
        border-right: solid $primary;
    }

    FilterSidebar .filter-header {
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
        color: $accent;
    }

    FilterSidebar .section-label {
        text-style: bold;
        margin-top: 1;
        color: $text-muted;
    }

    FilterSidebar Checkbox {
        margin-left: 1;
    }

    FilterSidebar Input {
        margin-top: 1;
        margin-bottom: 1;
    }
    """

    # Reactive attributes for filter state
    selected_subs: Set[str] = reactive(lambda: set(cat.sub for cat in CATEGORIES))
    selected_ranks: Set[str] = reactive(lambda: {"A", "B", "C", "N"})
    selected_core_ranks: Set[str] = reactive(lambda: {"A*", "A", "B", "C", "N"})
    selected_thcpl_ranks: Set[str] = reactive(lambda: {"A", "B", "N"})
    show_expired: bool = reactive(False)
    search_query: str = reactive("")

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialize the FilterSidebar.

        Args:
            name: The name of the widget.
            id: The ID of the widget in the DOM.
            classes: Space-separated list of class names.
            disabled: Whether the widget is disabled.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

    def compose(self):
        """Compose the filter sidebar layout.

        Yields:
            Widget components in vertical order: header, categories, ranks, search.
        """
        yield Label("Filters", classes="filter-header")

        yield Label("Categories", classes="section-label")
        for cat in CATEGORIES:
            yield Checkbox(
                f"{cat.sub} - {cat.name_en}",
                value=True,
                id=f"sub-{cat.sub}",
            )

        yield Label("CCF Ranks", classes="section-label")
        for rank in ["A", "B", "C", "N"]:
            yield Checkbox(f"CCF {rank}", value=True, id=f"rank-{rank}")

        yield Label("CORE Ranks", classes="section-label")
        for rank in ["A*", "A", "B", "C", "N"]:
            safe_id = rank.replace("*", "star")
            yield Checkbox(f"CORE {rank}", value=True, id=f"core-rank-{safe_id}")

        yield Label("THCPL Ranks", classes="section-label")
        for rank in ["A", "B", "N"]:
            yield Checkbox(f"THCPL {rank}", value=True, id=f"thcpl-rank-{rank}")

        yield Label("Options", classes="section-label")
        yield Checkbox("Show Expired", value=False, id="show-expired")

        yield Label("Search", classes="section-label")
        yield Input(placeholder="Search conferences...", id="search")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes.

        Updates the appropriate reactive set based on the checkbox ID
        and emits a FilterChanged message.

        Args:
            event: The checkbox changed event.
        """
        checkbox_id = event.checkbox.id
        if checkbox_id is None:
            return

        if checkbox_id.startswith("sub-"):
            sub_code = checkbox_id[4:]
            if event.value:
                self.selected_subs = self.selected_subs | {sub_code}
            else:
                self.selected_subs = self.selected_subs - {sub_code}
        elif checkbox_id.startswith("rank-"):
            rank = checkbox_id[5:]
            if event.value:
                self.selected_ranks = self.selected_ranks | {rank}
            else:
                self.selected_ranks = self.selected_ranks - {rank}
        elif checkbox_id.startswith("core-rank-"):
            rank = checkbox_id[10:].replace("star", "*")
            if event.value:
                self.selected_core_ranks = self.selected_core_ranks | {rank}
            else:
                self.selected_core_ranks = self.selected_core_ranks - {rank}
        elif checkbox_id.startswith("thcpl-rank-"):
            rank = checkbox_id[11:]
            if event.value:
                self.selected_thcpl_ranks = self.selected_thcpl_ranks | {rank}
            else:
                self.selected_thcpl_ranks = self.selected_thcpl_ranks - {rank}
        elif checkbox_id == "show-expired":
            self.show_expired = event.value

        self._emit_filter_changed()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes.

        Updates the search query and emits a FilterChanged message.

        Args:
            event: The input changed event.
        """
        if event.input.id == "search":
            self.search_query = event.value
            self._emit_filter_changed()

    def _emit_filter_changed(self) -> None:
        """Emit a FilterChanged message with current filter state."""
        self.post_message(
            FilterChanged(
                subs=self.selected_subs.copy(),
                ranks=self.selected_ranks.copy(),
                core_ranks=self.selected_core_ranks.copy(),
                thcpl_ranks=self.selected_thcpl_ranks.copy(),
                show_expired=self.show_expired,
                query=self.search_query,
            )
        )

    def get_filter_state(self) -> tuple[Set[str], Set[str], Set[str], Set[str], bool, str]:
        """Get the current filter state.

        Returns:
            A tuple of (selected_subs, selected_ranks, selected_core_ranks, 
                       selected_thcpl_ranks, show_expired, search_query).
        """
        return (
            self.selected_subs.copy(),
            self.selected_ranks.copy(),
            self.selected_core_ranks.copy(),
            self.selected_thcpl_ranks.copy(),
            self.show_expired,
            self.search_query,
        )

    def reset_filters(self) -> None:
        """Reset all filters to default state (all checked, empty search, hide expired)."""
        self.selected_subs = set(cat.sub for cat in CATEGORIES)
        self.selected_ranks = {"A", "B", "C", "N"}
        self.selected_core_ranks = {"A*", "A", "B", "C", "N"}
        self.selected_thcpl_ranks = {"A", "B", "N"}
        self.show_expired = False
        self.search_query = ""

        for cat in CATEGORIES:
            checkbox = self.query_one(f"#sub-{cat.sub}", Checkbox)
            checkbox.value = True

        for rank in ["A", "B", "C", "N"]:
            checkbox = self.query_one(f"#rank-{rank}", Checkbox)
            checkbox.value = True

        for rank in ["A*", "A", "B", "C", "N"]:
            safe_id = rank.replace("*", "star")
            checkbox = self.query_one(f"#core-rank-{safe_id}", Checkbox)
            checkbox.value = True

        for rank in ["A", "B", "N"]:
            checkbox = self.query_one(f"#thcpl-rank-{rank}", Checkbox)
            checkbox.value = True

        show_expired_checkbox = self.query_one("#show-expired", Checkbox)
        show_expired_checkbox.value = False

        search_input = self.query_one("#search", Input)
        search_input.value = ""

        self._emit_filter_changed()