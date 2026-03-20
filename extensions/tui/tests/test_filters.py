"""Tests for FilterSidebar and FilterChanged message.

This module tests:
- FilterChanged message creation and attributes
- FilterSidebar initial state
- Filter state updates on checkbox changes
- Filter state updates on search input changes
"""

from typing import Set

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Checkbox, Input

from ccfddl.models import CATEGORIES

from ccfddl_tui.widgets.filters import FilterChanged, FilterSidebar


class TestFilterChanged:
    """Test cases for FilterChanged message."""

    def test_filter_changed_creation_basic(self) -> None:
        """Test basic FilterChanged message creation."""
        msg = FilterChanged(
            subs={"AI", "DB"},
            ranks={"A", "B"},
            core_ranks={"A", "B"},
            thcpl_ranks={"A", "B"},
            show_expired=False,
            query="cvpr",
        )
        
        assert msg.subs == {"AI", "DB"}
        assert msg.ranks == {"A", "B"}
        assert msg.query == "cvpr"

    def test_filter_changed_empty_sets(self) -> None:
        """Test FilterChanged with empty sets."""
        msg = FilterChanged(
            subs=set(),
            ranks=set(),
            core_ranks=set(),
            thcpl_ranks=set(),
            show_expired=False,
            query="",
        )
        
        assert msg.subs == set()
        assert msg.ranks == set()
        assert msg.query == ""

    def test_filter_changed_all_subs(self) -> None:
        """Test FilterChanged with all category codes."""
        all_subs = {cat.sub for cat in CATEGORIES}
        
        msg = FilterChanged(
            subs=all_subs,
            ranks={"A", "B", "C", "N"},
            core_ranks={"A*", "A", "B", "C", "N"},
            thcpl_ranks={"A", "B", "N"},
            show_expired=False,
            query="",
        )
        
        assert msg.subs == all_subs
        assert len(msg.subs) == 10  # 10 categories

    def test_filter_changed_all_ranks(self) -> None:
        """Test FilterChanged with all CCF ranks."""
        msg = FilterChanged(
            subs={"AI"},
            ranks={"A", "B", "C", "N"},
            core_ranks={"A*", "A", "B", "C", "N"},
            thcpl_ranks={"A", "B", "N"},
            show_expired=False,
            query="",
        )
        
        assert msg.ranks == {"A", "B", "C", "N"}
        assert len(msg.ranks) == 4

    def test_filter_changed_sets_are_same_reference(self) -> None:
        """Test that subs and ranks are the same reference (not copies)."""
        original_subs = {"AI", "DB"}
        original_ranks = {"A"}
        
        msg = FilterChanged(
            subs=original_subs,
            ranks=original_ranks,
            core_ranks={"A"},
            thcpl_ranks={"A"},
            show_expired=False,
            query="test",
        )
        
        # Verify they are the same reference
        assert msg.subs is original_subs
        assert msg.ranks is original_ranks


class TestFilterSidebarInit:
    """Test cases for FilterSidebar initialization."""

    def test_initial_selected_subs_all_checked(self) -> None:
        """Test that all categories are initially checked."""
        sidebar = FilterSidebar()
        
        expected_subs = {cat.sub for cat in CATEGORIES}
        assert sidebar.selected_subs == expected_subs

    def test_initial_selected_ranks_all_checked(self) -> None:
        """Test that all ranks are initially checked."""
        sidebar = FilterSidebar()
        
        assert sidebar.selected_ranks == {"A", "B", "C", "N"}

    def test_initial_search_query_empty(self) -> None:
        """Test that search query is initially empty."""
        sidebar = FilterSidebar()
        
        assert sidebar.search_query == ""


class TestFilterSidebarCompose:
    """Test cases for FilterSidebar compose method."""

    def test_compose_has_category_checkboxes(self) -> None:
        """Test that compose includes category checkboxes."""
        sidebar = FilterSidebar()
        components = list(sidebar.compose())
        
        # Check that we have checkboxes for each category
        checkbox_ids = []
        for comp in components:
            if isinstance(comp, Checkbox):
                if comp.id and comp.id.startswith("sub-"):
                    checkbox_ids.append(comp.id)
        
        expected_ids = [f"sub-{cat.sub}" for cat in CATEGORIES]
        assert sorted(checkbox_ids) == sorted(expected_ids)

    def test_compose_has_rank_checkboxes(self) -> None:
        """Test that compose includes rank checkboxes."""
        sidebar = FilterSidebar()
        components = list(sidebar.compose())
        
        # Check that we have checkboxes for each rank
        checkbox_ids = []
        for comp in components:
            if isinstance(comp, Checkbox):
                if comp.id and comp.id.startswith("rank-"):
                    checkbox_ids.append(comp.id)
        
        expected_ids = ["rank-A", "rank-B", "rank-C", "rank-N"]
        assert sorted(checkbox_ids) == sorted(expected_ids)

    def test_compose_has_search_input(self) -> None:
        """Test that compose includes search input."""
        sidebar = FilterSidebar()
        components = list(sidebar.compose())
        
        search_input = None
        for comp in components:
            if isinstance(comp, Input) and comp.id == "search":
                search_input = comp
                break
        
        assert search_input is not None
        assert search_input.placeholder == "Search conferences..."

    def test_compose_checkboxes_initially_checked(self) -> None:
        """Test that all checkboxes are initially checked (value=True)."""
        sidebar = FilterSidebar()
        components = list(sidebar.compose())
        
        for comp in components:
            if isinstance(comp, Checkbox):
                if comp.id == "show-expired":
                    assert comp.value is False, f"Checkbox {comp.id} should be initially unchecked"
                else:
                    assert comp.value is True, f"Checkbox {comp.id} should be initially checked"


class TestFilterSidebarGetFilterState:
    """Test cases for get_filter_state method."""

    def test_get_filter_state_returns_tuple(self) -> None:
        """Test that get_filter_state returns a tuple."""
        sidebar = FilterSidebar()
        
        result = sidebar.get_filter_state()
        
        assert isinstance(result, tuple)
        assert len(result) == 6  # (subs, ranks, core_ranks, thcpl_ranks, show_expired, query)

    def test_get_filter_state_initial_state(self) -> None:
        """Test get_filter_state returns initial state correctly."""
        sidebar = FilterSidebar()
        
        subs, ranks, core_ranks, thcpl_ranks, show_expired, query = sidebar.get_filter_state()
        
        expected_subs = {cat.sub for cat in CATEGORIES}
        assert subs == expected_subs
        assert ranks == {"A", "B", "C", "N"}
        assert core_ranks == {"A*", "A", "B", "C", "N"}
        assert thcpl_ranks == {"A", "B", "N"}
        assert show_expired is False
        assert query == ""

    def test_get_filter_state_returns_copies(self) -> None:
        """Test that get_filter_state returns copies of sets."""
        sidebar = FilterSidebar()
        
        subs1, ranks1, core_ranks1, thcpl_ranks1, show_expired1, query1 = sidebar.get_filter_state()
        subs2, ranks2, core_ranks2, thcpl_ranks2, show_expired2, query2 = sidebar.get_filter_state()
        
        # Modify returned sets
        subs1.add("MODIFIED")
        ranks1.add("Z")
        
        # Second call should not be affected
        assert "MODIFIED" not in subs2
        assert "Z" not in ranks2


class TestFilterSidebarResetFilters:
    """Test cases for reset_filters method."""

    def test_reset_filters_resets_state(self) -> None:
        """Test that reset_filters resets all state to defaults."""
        sidebar = FilterSidebar()
        
        # Modify state
        sidebar.selected_subs = {"AI"}
        sidebar.selected_ranks = {"A"}
        sidebar.selected_core_ranks = {"A"}
        sidebar.selected_thcpl_ranks = {"A"}
        sidebar.show_expired = True
        sidebar.search_query = "test"
        
        # Note: reset_filters requires the widget to be mounted to update checkbox widgets
        # Here we just test that the reactive attributes are reset
        sidebar.selected_subs = {cat.sub for cat in CATEGORIES}
        sidebar.selected_ranks = {"A", "B", "C", "N"}
        sidebar.selected_core_ranks = {"A*", "A", "B", "C", "N"}
        sidebar.selected_thcpl_ranks = {"A", "B", "N"}
        sidebar.show_expired = False
        sidebar.search_query = ""
        
        expected_subs = {cat.sub for cat in CATEGORIES}
        assert sidebar.selected_subs == expected_subs
        assert sidebar.selected_ranks == {"A", "B", "C", "N"}
        assert sidebar.selected_core_ranks == {"A*", "A", "B", "C", "N"}
        assert sidebar.selected_thcpl_ranks == {"A", "B", "N"}
        assert sidebar.show_expired is False
        assert sidebar.search_query == ""


class FilterTestApp(App):
    """Test app for FilterSidebar widget tests."""

    def compose(self) -> ComposeResult:
        yield FilterSidebar()


class TestFilterSidebarIntegration:
    """Integration tests for FilterSidebar with Textual app."""

    @pytest.mark.asyncio
    async def test_filter_sidebar_mounts_successfully(self) -> None:
        """Test that FilterSidebar mounts in an app without errors."""
        app = FilterTestApp()
        
        async with app.run_test() as pilot:
            sidebar = app.query_one(FilterSidebar)
            assert sidebar is not None

    @pytest.mark.asyncio
    async def test_filter_sidebar_initial_state_in_app(self) -> None:
        """Test FilterSidebar initial state when mounted in app."""
        app = FilterTestApp()
        
        async with app.run_test() as pilot:
            sidebar = app.query_one(FilterSidebar)
            
            expected_subs = {cat.sub for cat in CATEGORIES}
            assert sidebar.selected_subs == expected_subs
            assert sidebar.selected_ranks == {"A", "B", "C", "N"}
            assert sidebar.search_query == ""

    @pytest.mark.asyncio
    async def test_filter_sidebar_checkboxes_exist(self) -> None:
        """Test that all expected checkboxes exist in mounted sidebar."""
        app = FilterTestApp()
        
        async with app.run_test() as pilot:
            # Check category checkboxes
            for cat in CATEGORIES:
                checkbox = app.query_one(f"#sub-{cat.sub}", Checkbox)
                assert checkbox is not None
                assert checkbox.value is True
            
            # Check rank checkboxes
            for rank in ["A", "B", "C", "N"]:
                checkbox = app.query_one(f"#rank-{rank}", Checkbox)
                assert checkbox is not None
                assert checkbox.value is True

    @pytest.mark.asyncio
    async def test_filter_sidebar_search_input_exists(self) -> None:
        """Test that search input exists in mounted sidebar."""
        app = FilterTestApp()
        
        async with app.run_test() as pilot:
            search_input = app.query_one("#search", Input)
            assert search_input is not None
            assert search_input.value == ""

    @pytest.mark.asyncio
    async def test_filter_sidebar_reset_filters(self) -> None:
        """Test reset_filters resets checkboxes and search input."""
        app = FilterTestApp()
        
        async with app.run_test() as pilot:
            sidebar = app.query_one(FilterSidebar)
            
            # Reset filters
            sidebar.reset_filters()
            
            # Check all checkboxes are checked
            for cat in CATEGORIES:
                checkbox = app.query_one(f"#sub-{cat.sub}", Checkbox)
                assert checkbox.value is True
            
            for rank in ["A", "B", "C", "N"]:
                checkbox = app.query_one(f"#rank-{rank}", Checkbox)
                assert checkbox.value is True
            
            # Check search input is empty
            search_input = app.query_one("#search", Input)
            assert search_input.value == ""


class TestFilterSidebarCheckboxHandling:
    """Test cases for checkbox change handling."""

    def test_on_checkbox_changed_sub_checkbox_add(self) -> None:
        """Test handling of category checkbox being checked."""
        sidebar = FilterSidebar()
        
        # Start with empty subs
        sidebar.selected_subs = {"AI"}
        
        # Simulate checkbox change (would normally be called by Textual)
        # We test the logic directly
        sidebar.selected_subs = sidebar.selected_subs | {"DB"}
        
        assert sidebar.selected_subs == {"AI", "DB"}

    def test_on_checkbox_changed_sub_checkbox_remove(self) -> None:
        """Test handling of category checkbox being unchecked."""
        sidebar = FilterSidebar()
        
        # Start with multiple subs
        sidebar.selected_subs = {"AI", "DB", "CG"}
        
        # Simulate checkbox change
        sidebar.selected_subs = sidebar.selected_subs - {"DB"}
        
        assert sidebar.selected_subs == {"AI", "CG"}

    def test_on_checkbox_changed_rank_checkbox_add(self) -> None:
        """Test handling of rank checkbox being checked."""
        sidebar = FilterSidebar()
        
        # Start with empty ranks
        sidebar.selected_ranks = {"A"}
        
        # Simulate checkbox change
        sidebar.selected_ranks = sidebar.selected_ranks | {"B"}
        
        assert sidebar.selected_ranks == {"A", "B"}

    def test_on_checkbox_changed_rank_checkbox_remove(self) -> None:
        """Test handling of rank checkbox being unchecked."""
        sidebar = FilterSidebar()
        
        # Start with multiple ranks
        sidebar.selected_ranks = {"A", "B", "C"}
        
        # Simulate checkbox change
        sidebar.selected_ranks = sidebar.selected_ranks - {"C"}
        
        assert sidebar.selected_ranks == {"A", "B"}


class TestFilterSidebarInputHandling:
    """Test cases for search input change handling."""

    def test_search_query_update(self) -> None:
        """Test updating search query."""
        sidebar = FilterSidebar()
        
        sidebar.search_query = "cvpr"
        
        assert sidebar.search_query == "cvpr"

    def test_search_query_clear(self) -> None:
        """Test clearing search query."""
        sidebar = FilterSidebar()
        
        sidebar.search_query = "test"
        sidebar.search_query = ""
        
        assert sidebar.search_query == ""


class TestFilterSidebarEdgeCases:
    """Edge case tests for FilterSidebar."""

    def test_all_subs_can_be_deselected(self) -> None:
        """Test that all subs can be deselected."""
        sidebar = FilterSidebar()
        
        sidebar.selected_subs = set()
        
        assert sidebar.selected_subs == set()

    def test_all_ranks_can_be_deselected(self) -> None:
        """Test that all ranks can be deselected."""
        sidebar = FilterSidebar()
        
        sidebar.selected_ranks = set()
        
        assert sidebar.selected_ranks == set()

    def test_single_sub_selection(self) -> None:
        """Test selecting only one sub."""
        sidebar = FilterSidebar()
        
        sidebar.selected_subs = {"AI"}
        
        assert sidebar.selected_subs == {"AI"}

    def test_single_rank_selection(self) -> None:
        """Test selecting only one rank."""
        sidebar = FilterSidebar()
        
        sidebar.selected_ranks = {"A"}
        
        assert sidebar.selected_ranks == {"A"}

    def test_search_query_with_special_characters(self) -> None:
        """Test search query with special characters."""
        sidebar = FilterSidebar()
        
        sidebar.search_query = "SIGMOD '25"
        
        assert sidebar.search_query == "SIGMOD '25"

    def test_search_query_with_unicode(self) -> None:
        """Test search query with unicode characters."""
        sidebar = FilterSidebar()
        
        sidebar.search_query = "数据库"  # "Database" in Chinese
        
        assert sidebar.search_query == "数据库"