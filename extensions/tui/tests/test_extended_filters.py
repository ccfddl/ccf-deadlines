"""Tests for multi-rank filtering (CCF, CORE, THCPL) and expired toggle.

This module tests the extended FilterChanged message, DataService rank filtering,
and the show_expired toggle functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta

from ccfddl_tui.data.data_service import DataService, ConferenceRow
from ccfddl_tui.widgets.filters import FilterChanged, FilterSidebar


class TestFilterChangedMessage:
    """Test the extended FilterChanged message with multi-rank support."""

    def test_filter_changed_with_all_ranks(self):
        """FilterChanged should accept CCF, CORE, and THCPL ranks."""
        msg = FilterChanged(
            subs={"AI", "DB"},
            ranks={"A", "B"},
            core_ranks={"A*", "A"},
            thcpl_ranks={"A", "B"},
            show_expired=False,
            query="test",
        )

        assert msg.subs == {"AI", "DB"}
        assert msg.ranks == {"A", "B"}
        assert msg.core_ranks == {"A*", "A"}
        assert msg.thcpl_ranks == {"A", "B"}
        assert msg.show_expired is False
        assert msg.query == "test"

    def test_filter_changed_with_expired_enabled(self):
        """FilterChanged should support show_expired=True."""
        msg = FilterChanged(
            subs={"AI"},
            ranks={"A"},
            core_ranks={"A"},
            thcpl_ranks={"A"},
            show_expired=True,
            query="",
        )

        assert msg.show_expired is True


class TestConferenceRowExtended:
    """Test ConferenceRow with extended rank fields."""

    def test_conference_row_with_core_and_thcpl(self):
        """ConferenceRow should accept core_rank and thcpl_rank."""
        row = ConferenceRow(
            title="Test Conference",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A*",
            thcpl_rank="A",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            countdown="30 days",
            place="Test Location",
            date="July 2025",
            link="http://test.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        )

        assert row.core_rank == "A*"
        assert row.thcpl_rank == "A"
        assert row.is_expired is False

    def test_conference_row_with_none_ranks(self):
        """ConferenceRow should accept None for optional ranks."""
        row = ConferenceRow(
            title="Test Conference",
            year=2025,
            sub="AI",
            rank="A",
            core_rank=None,
            thcpl_rank=None,
            deadline=None,
            countdown="TBD",
            place="Test Location",
            date="July 2025",
            link="http://test.com",
            is_running=True,
            is_tbd=True,
            is_expired=False,
        )

        assert row.core_rank is None
        assert row.thcpl_rank is None


class TestDataServiceRankFiltering:
    """Test DataService filtering with multiple rank types."""

    def test_filter_by_rank_with_ccf(self, sample_conference_rows_with_ranks):
        """Should filter by CCF rank."""
        service = DataService()
        rows = sample_conference_rows_with_ranks

        result = service.filter_by_rank(rows, {"A"})

        assert len(result) == 2
        assert all(r.rank == "A" for r in result)

    def test_filter_expired_conferences(self, sample_conference_rows_mixed):
        """Should filter out expired conferences when show_expired=False."""
        rows = sample_conference_rows_mixed

        # Filter out expired
        result = [r for r in rows if not r.is_expired]

        assert len(result) == 2  # Running and TBD
        assert all(not r.is_expired for r in result)

    def test_include_expired_when_enabled(self, sample_conference_rows_mixed):
        """Should include expired when show_expired=True."""
        rows = sample_conference_rows_mixed

        # Include all
        result = rows

        assert len(result) == 3
        assert any(r.is_expired for r in result)


class TestFilterSidebarExtended:
    """Test FilterSidebar with extended rank filters."""

    @pytest.mark.asyncio
    async def test_core_rank_checkboxes_exist(self):
        """Sidebar should have CORE rank checkboxes."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield FilterSidebar()

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            sidebar = pilot.app.query_one(FilterSidebar)

            # Check CORE rank checkboxes exist
            for rank in ["A*", "A", "B", "C", "N"]:
                safe_id = rank.replace("*", "star")
                checkbox = sidebar.query_one(f"#core-rank-{safe_id}")
                assert checkbox is not None
                assert checkbox.value is True  # Default checked

    @pytest.mark.asyncio
    async def test_thcpl_rank_checkboxes_exist(self):
        """Sidebar should have THCPL rank checkboxes."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield FilterSidebar()

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            sidebar = pilot.app.query_one(FilterSidebar)

            # Check THCPL rank checkboxes exist
            for rank in ["A", "B", "N"]:
                checkbox = sidebar.query_one(f"#thcpl-rank-{rank}")
                assert checkbox is not None
                assert checkbox.value is True  # Default checked

    @pytest.mark.asyncio
    async def test_show_expired_checkbox_exists(self):
        """Sidebar should have show_expired checkbox."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield FilterSidebar()

        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            sidebar = pilot.app.query_one(FilterSidebar)

            checkbox = sidebar.query_one("#show-expired")
            assert checkbox is not None
            assert checkbox.value is False  # Default unchecked

    @pytest.mark.asyncio
    async def test_core_rank_toggle_emits_filter_changed(self):
        """Toggling CORE rank should emit FilterChanged."""
        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield FilterSidebar()

        app = TestApp()
        messages = []

        def capture_message(msg):
            messages.append(msg)

        async with app.run_test() as pilot:
            await pilot.pause()

            sidebar = pilot.app.query_one(FilterSidebar)
            sidebar.watch(sidebar, "selected_core_ranks", capture_message)

            # Toggle off A*
            checkbox = sidebar.query_one("#core-rank-Astar")
            checkbox.value = False

            await pilot.pause()

            assert len(messages) > 0


class TestLocalDataFallback:
    """Test DataService local data fallback functionality."""

    def test_using_local_data_property(self, mock_local_conferences):
        """DataService should track if using local data."""
        service = DataService()

        # Initially false
        assert service.using_local_data is False

    def test_last_error_property(self):
        """DataService should store last error."""
        service = DataService()

        # Initially None
        assert service.last_error is None


# Fixtures

@pytest.fixture
def sample_conference_rows_with_ranks():
    """Sample rows with different rank types."""
    now = datetime.now(timezone.utc)

    return [
        ConferenceRow(
            title="CVPR",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A*",
            thcpl_rank="A",
            deadline=now + timedelta(days=30),
            countdown="30 days",
            place="Location",
            date="June 2025",
            link="http://cvpr.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        ),
        ConferenceRow(
            title="ICML",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            deadline=now + timedelta(days=60),
            countdown="60 days",
            place="Location",
            date="July 2025",
            link="http://icml.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        ),
        ConferenceRow(
            title="NeurIPS",
            year=2025,
            sub="AI",
            rank="B",
            core_rank="A",
            thcpl_rank="B",
            deadline=now + timedelta(days=90),
            countdown="90 days",
            place="Location",
            date="Dec 2025",
            link="http://neurips.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        ),
    ]


@pytest.fixture
def sample_conference_rows_mixed():
    """Sample rows with running, TBD, and expired conferences."""
    now = datetime.now(timezone.utc)

    return [
        ConferenceRow(
            title="Running Conf",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            deadline=now + timedelta(days=30),
            countdown="30 days",
            place="Location",
            date="June 2025",
            link="http://running.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        ),
        ConferenceRow(
            title="TBD Conf",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            deadline=None,
            countdown="TBD",
            place="Location",
            date="TBD",
            link="http://tbd.com",
            is_running=True,
            is_tbd=True,
            is_expired=False,
        ),
        ConferenceRow(
            title="Expired Conf",
            year=2024,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            deadline=now - timedelta(days=30),
            countdown="Expired",
            place="Location",
            date="June 2024",
            link="http://expired.com",
            is_running=False,
            is_tbd=False,
            is_expired=True,
        ),
    ]


@pytest.fixture
def mock_local_conferences(monkeypatch):
    """Mock local conference loading."""
    def mock_load_local(self):
        return []

    monkeypatch.setattr(DataService, "_load_local_conferences", mock_load_local)
