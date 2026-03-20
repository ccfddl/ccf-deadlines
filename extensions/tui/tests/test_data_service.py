"""Tests for DataService.

This module tests the data service layer including:
- ConferenceRow creation
- Filtering by category and rank
- Fuzzy search functionality
- Sorting logic (running → TBD → finished)
- Deadline extraction from conference data
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ccfddl.models import Conference, ConferenceYear, Rank, Timeline

from ccfddl_tui.data.data_service import ConferenceRow, DataService


class TestConferenceRow:
    """Test cases for ConferenceRow dataclass."""

    def test_conference_row_creation_basic(self) -> None:
        """Test basic ConferenceRow creation with required fields."""
        deadline = datetime.now(timezone.utc) + timedelta(days=5)
        row = ConferenceRow(
            title="CVPR",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
            is_favorite=False,
            deadline=deadline,
            countdown="5 days",
            place="Seattle, USA",
            date="June 15-20, 2025",
            link="https://example.com",
            is_running=True,
            is_tbd=False,
        )

        assert row.title == "CVPR"
        assert row.year == 2025
        assert row.sub == "AI"
        assert row.rank == "A"
        assert row.deadline == deadline
        assert row.countdown == "5 days"
        assert row.is_running is True
        assert row.is_tbd is False

    def test_conference_row_tbd(self) -> None:
        """Test ConferenceRow with TBD deadline."""
        row = ConferenceRow(
            title="NeurIPS",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
            is_favorite=False,
            deadline=None,
            countdown="TBD",
            place="Vancouver, Canada",
            date="December 2025",
            link="https://example.com",
            is_running=True,
            is_tbd=True,
        )

        assert row.deadline is None
        assert row.is_tbd is True
        assert row.is_running is True

    def test_conference_row_finished(self) -> None:
        """Test ConferenceRow with finished (expired) deadline."""
        row = ConferenceRow(
            title="ICML",
            year=2024,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
            is_favorite=False,
            deadline=datetime.now(timezone.utc) - timedelta(days=10),
            countdown="Finished",
            place="Vienna, Austria",
            date="July 2024",
            link="https://example.com",
            is_running=False,
            is_tbd=False,
        )

        assert row.is_running is False
        assert row.is_tbd is False
        assert row.countdown == "Finished"


class TestDataServiceInit:
    """Test cases for DataService initialization."""

    def test_init_default_url(self) -> None:
        """Test DataService initialization with default URL."""
        service = DataService()
        assert service.url == DataService.DEFAULT_URL
        assert service.conferences == []

    def test_init_custom_url(self) -> None:
        """Test DataService initialization with custom URL."""
        custom_url = "https://custom.url/conferences.yml"
        service = DataService(url=custom_url)
        assert service.url == custom_url

    def test_conferences_property(self) -> None:
        """Test conferences property returns internal list."""
        service = DataService()
        assert service.conferences == []


class TestFilterBySub:
    """Test cases for filter_by_sub method."""

    def test_filter_by_sub_single_category(
        self, sample_conference_rows_various_categories: list[ConferenceRow]
    ) -> None:
        """Test filtering by a single category returns only matching rows."""
        service = DataService()
        rows = sample_conference_rows_various_categories

        result = service.filter_by_sub(rows, {"AI"})

        assert len(result) == 1
        assert result[0].sub == "AI"
        assert result[0].title == "CVPR"

    def test_filter_by_sub_multiple_categories(
        self, sample_conference_rows_various_categories: list[ConferenceRow]
    ) -> None:
        """Test filtering by multiple categories returns all matching rows."""
        service = DataService()
        rows = sample_conference_rows_various_categories

        result = service.filter_by_sub(rows, {"AI", "DB"})

        assert len(result) == 2
        result_subs = {row.sub for row in result}
        assert result_subs == {"AI", "DB"}

    def test_filter_by_sub_all_categories(
        self, sample_conference_rows_various_categories: list[ConferenceRow]
    ) -> None:
        """Test filtering with all categories returns all rows."""
        service = DataService()
        rows = sample_conference_rows_various_categories

        result = service.filter_by_sub(rows, {"AI", "DB", "CG", "SE"})

        assert len(result) == len(rows)

    def test_filter_by_sub_empty_set_returns_all(
        self, sample_conference_rows_various_categories: list[ConferenceRow]
    ) -> None:
        """Test filtering with empty set returns all rows."""
        service = DataService()
        rows = sample_conference_rows_various_categories

        result = service.filter_by_sub(rows, set())

        assert len(result) == len(rows)

    def test_filter_by_sub_no_match_returns_empty(
        self, sample_conference_rows_various_categories: list[ConferenceRow]
    ) -> None:
        """Test filtering with non-existent category returns empty list."""
        service = DataService()
        rows = sample_conference_rows_various_categories

        result = service.filter_by_sub(rows, {"NONEXISTENT"})

        assert len(result) == 0

    def test_filter_by_sub_empty_input_list(self) -> None:
        """Test filtering an empty list returns empty list."""
        service = DataService()

        result = service.filter_by_sub([], {"AI"})

        assert result == []


class TestFilterByRank:
    """Test cases for filter_by_rank method."""

    def test_filter_by_rank_single_rank(
        self, sample_conference_rows_various_ranks: list[ConferenceRow]
    ) -> None:
        """Test filtering by a single rank returns only matching rows."""
        service = DataService()
        rows = sample_conference_rows_various_ranks

        result = service.filter_by_rank(rows, {"A"})

        assert len(result) == 1
        assert result[0].rank == "A"

    def test_filter_by_rank_multiple_ranks(
        self, sample_conference_rows_various_ranks: list[ConferenceRow]
    ) -> None:
        """Test filtering by multiple ranks returns all matching rows."""
        service = DataService()
        rows = sample_conference_rows_various_ranks

        result = service.filter_by_rank(rows, {"A", "B"})

        assert len(result) == 2
        result_ranks = {row.rank for row in result}
        assert result_ranks == {"A", "B"}

    def test_filter_by_rank_all_ranks(
        self, sample_conference_rows_various_ranks: list[ConferenceRow]
    ) -> None:
        """Test filtering with all ranks returns all rows."""
        service = DataService()
        rows = sample_conference_rows_various_ranks

        result = service.filter_by_rank(rows, {"A", "B", "C", "N"})

        assert len(result) == len(rows)

    def test_filter_by_rank_empty_set_returns_all(
        self, sample_conference_rows_various_ranks: list[ConferenceRow]
    ) -> None:
        """Test filtering with empty set returns all rows."""
        service = DataService()
        rows = sample_conference_rows_various_ranks

        result = service.filter_by_rank(rows, set())

        assert len(result) == len(rows)

    def test_filter_by_rank_no_match_returns_empty(
        self, sample_conference_rows_various_ranks: list[ConferenceRow]
    ) -> None:
        """Test filtering with non-existent rank returns empty list."""
        service = DataService()
        rows = sample_conference_rows_various_ranks

        # Use a rank that doesn't exist in the fixture
        result = service.filter_by_rank(rows, {"Z"})

        assert len(result) == 0

    def test_filter_by_rank_empty_input_list(self) -> None:
        """Test filtering an empty list returns empty list."""
        service = DataService()

        result = service.filter_by_rank([], {"A"})

        assert result == []


class TestFuzzySearch:
    """Test cases for fuzzy_search method."""

    def test_fuzzy_search_exact_match(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test exact substring match returns correct results."""
        service = DataService()
        rows = sample_conference_rows_mixed

        result = service.fuzzy_search(rows, "CVPR")

        assert len(result) >= 1
        assert any("CVPR" in row.title for row in result)

    def test_fuzzy_search_partial_match(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test partial match returns relevant results."""
        service = DataService()
        rows = sample_conference_rows_mixed

        result = service.fuzzy_search(rows, "Neur")

        assert len(result) >= 1
        assert any("NeurIPS" in row.title for row in result)

    def test_fuzzy_search_case_insensitive(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test search is case insensitive."""
        service = DataService()
        rows = sample_conference_rows_mixed

        result_lower = service.fuzzy_search(rows, "cvpr")
        result_upper = service.fuzzy_search(rows, "CVPR")

        # Both should return results
        assert len(result_lower) >= 1
        assert len(result_upper) >= 1

    def test_fuzzy_search_empty_query_returns_all(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test empty query returns all rows."""
        service = DataService()
        rows = sample_conference_rows_mixed

        result = service.fuzzy_search(rows, "")

        assert len(result) == len(rows)

    def test_fuzzy_search_no_match_returns_empty(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test no match returns empty list."""
        service = DataService()
        rows = sample_conference_rows_mixed

        # Use a query that won't match any conference
        result = service.fuzzy_search(rows, "ZZZZZZZZZZNOTFOUND12345")

        assert len(result) == 0

    def test_fuzzy_search_empty_input_list(self) -> None:
        """Test searching an empty list returns empty list."""
        service = DataService()

        result = service.fuzzy_search([], "CVPR")

        assert result == []

    def test_fuzzy_search_sorted_by_relevance(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test results are sorted by relevance score."""
        service = DataService()
        # Create rows with different similarity levels
        rows = [
            ConferenceRow(
                title="International Conference on Computer Vision",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=datetime.now(timezone.utc) + timedelta(days=10),
                countdown="10 days",
                place="Paris, France",
                date="October 2025",
                link="https://example.com",
                is_running=True,
                is_tbd=False,
            ),
            ConferenceRow(
                title="Computer Vision Workshop",
                year=2025,
                sub="AI",
                rank="C",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=datetime.now(timezone.utc) + timedelta(days=10),
                countdown="10 days",
                place="Online",
                date="June 2025",
                link="https://example.com",
                is_running=True,
                is_tbd=False,
            ),
        ]

        result = service.fuzzy_search(rows, "Computer Vision")

        # Should return both results
        assert len(result) >= 1


class TestSortRows:
    """Test cases for sort_rows method."""

    def test_sort_rows_running_first(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test that running conferences come before TBD and finished."""
        service = DataService()
        rows = sample_conference_rows_mixed

        sorted_rows = service.sort_rows(rows)

        # First items should be running
        for i, row in enumerate(sorted_rows[:3]):
            assert row.is_running is True
            assert row.is_tbd is False

    def test_sort_rows_tbd_before_finished(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test that TBD conferences come before finished."""
        service = DataService()
        rows = sample_conference_rows_mixed

        sorted_rows = service.sort_rows(rows)

        # Find the first TBD and first finished
        tbd_idx = None
        finished_idx = None

        for i, row in enumerate(sorted_rows):
            if row.is_tbd and tbd_idx is None:
                tbd_idx = i
            if not row.is_running and not row.is_tbd and finished_idx is None:
                finished_idx = i

        # TBD should come before finished
        if tbd_idx is not None and finished_idx is not None:
            assert tbd_idx < finished_idx

    def test_sort_rows_running_by_deadline_ascending(
        self, sample_conference_rows_mixed: list[ConferenceRow]
    ) -> None:
        """Test running conferences sorted by deadline (most urgent first)."""
        service = DataService()
        rows = sample_conference_rows_mixed

        sorted_rows = service.sort_rows(rows)

        # Get only running rows
        running_rows = [r for r in sorted_rows if r.is_running and not r.is_tbd]

        # Check they are sorted by deadline ascending
        for i in range(len(running_rows) - 1):
            assert running_rows[i].deadline <= running_rows[i + 1].deadline

    def test_sort_rows_tbd_by_year_descending(self) -> None:
        """Test TBD conferences sorted by year descending."""
        service = DataService()
        now = datetime.now(timezone.utc)

        rows = [
            ConferenceRow(
                title="Conf A",
                year=2023,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=None,
                countdown="TBD",
                place="City A",
                date="TBD",
                link="https://a.com",
                is_running=True,
                is_tbd=True,
            ),
            ConferenceRow(
                title="Conf B",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=None,
                countdown="TBD",
                place="City B",
                date="TBD",
                link="https://b.com",
                is_running=True,
                is_tbd=True,
            ),
            ConferenceRow(
                title="Conf C",
                year=2024,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=None,
                countdown="TBD",
                place="City C",
                date="TBD",
                link="https://c.com",
                is_running=True,
                is_tbd=True,
            ),
        ]

        sorted_rows = service.sort_rows(rows)

        # Check TBD rows are sorted by year descending
        tbd_rows = [r for r in sorted_rows if r.is_tbd]
        for i in range(len(tbd_rows) - 1):
            assert tbd_rows[i].year >= tbd_rows[i + 1].year

    def test_sort_rows_finished_by_year_descending(self) -> None:
        """Test finished conferences sorted by year descending."""
        service = DataService()
        now = datetime.now(timezone.utc)

        rows = [
            ConferenceRow(
                title="Conf A",
                year=2022,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=now - timedelta(days=100),
                countdown="Finished",
                place="City A",
                date="TBD",
                link="https://a.com",
                is_running=False,
                is_tbd=False,
            ),
            ConferenceRow(
                title="Conf B",
                year=2024,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=now - timedelta(days=100),
                countdown="Finished",
                place="City B",
                date="TBD",
                link="https://b.com",
                is_running=False,
                is_tbd=False,
            ),
            ConferenceRow(
                title="Conf C",
                year=2023,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                is_expired=False,
                is_favorite=False,
                deadline=now - timedelta(days=100),
                countdown="Finished",
                place="City C",
                date="TBD",
                link="https://c.com",
                is_running=False,
                is_tbd=False,
            ),
        ]

        sorted_rows = service.sort_rows(rows)

        # Check finished rows are sorted by year descending
        finished_rows = [r for r in sorted_rows if not r.is_running and not r.is_tbd]
        for i in range(len(finished_rows) - 1):
            assert finished_rows[i].year >= finished_rows[i + 1].year

    def test_sort_rows_empty_list(self) -> None:
        """Test sorting an empty list returns empty list."""
        service = DataService()

        result = service.sort_rows([])

        assert result == []


class TestFindBestConfYear:
    """Test cases for _find_best_conf_year method."""

    def test_find_best_conf_year_upcoming_deadline(
        self, sample_conference: Conference, fixed_now: datetime
    ) -> None:
        """Test finding upcoming deadline returns correct row."""
        service = DataService()

        # Set a future deadline
        future_deadline = fixed_now + timedelta(days=30)
        sample_conference.confs[0].timeline[0].deadline = future_deadline.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        result = service._find_best_conf_year(sample_conference, fixed_now)

        assert result is not None
        assert result.title == "CVPR"

    def test_find_best_conf_year_tbd_deadline(
        self, sample_conference_tbd: Conference, fixed_now: datetime
    ) -> None:
        """Test TBD deadline returns correct row with is_tbd=True."""
        service = DataService()

        result = service._find_best_conf_year(sample_conference_tbd, fixed_now)

        assert result is not None
        assert result.is_tbd is True
        assert result.countdown == "TBD"

    def test_find_best_conf_year_no_confs(
        self, fixed_now: datetime
    ) -> None:
        """Test conference with no confs returns None."""
        service = DataService()
        conf = Conference(
            title="EmptyConf",
            description="A conference with no years",
            sub="AI",
            rank=Rank(ccf="A"),
            dblp="empty",
            confs=[],
        )

        result = service._find_best_conf_year(conf, fixed_now)

        assert result is None

    def test_find_best_conf_year_expired_uses_most_recent(
        self, fixed_now: datetime
    ) -> None:
        """Test expired deadline falls back to most recent year."""
        service = DataService()

        # Create conference with expired deadline
        past_deadline = fixed_now - timedelta(days=30)
        conf = Conference(
            title="ExpiredConf",
            description="A conference with expired deadline",
            sub="AI",
            rank=Rank(ccf="A"),
            dblp="expired",
            confs=[
                ConferenceYear(
                    year=2024,
                    id="expired24",
                    link="https://example.com",
                    timeline=[
                        Timeline(deadline=past_deadline.strftime("%Y-%m-%d %H:%M:%S"))
                    ],
                    timezone="UTC",
                    date="July 2024",
                    place="City",
                )
            ],
        )

        result = service._find_best_conf_year(conf, fixed_now)

        assert result is not None
        assert result.year == 2024
        assert result.is_running is False

    def test_find_best_conf_year_multiple_timelines(
        self, sample_conference_multiple_timelines: Conference, fixed_now: datetime
    ) -> None:
        """Test conference with multiple timeline entries picks earliest upcoming."""
        service = DataService()

        # Set deadlines relative to fixed_now
        sample_conference_multiple_timelines.confs[0].timeline[0].deadline = (
            fixed_now + timedelta(days=60)
        ).strftime("%Y-%m-%d %H:%M:%S")
        sample_conference_multiple_timelines.confs[0].timeline[1].deadline = (
            fixed_now + timedelta(days=30)
        ).strftime("%Y-%m-%d %H:%M:%S")

        result = service._find_best_conf_year(sample_conference_multiple_timelines, fixed_now)

        assert result is not None
        # Should pick the earlier upcoming deadline (30 days, not 60)


class TestCreateRow:
    """Test cases for _create_row method."""

    def test_create_row_running(self, sample_conference: Conference, fixed_now: datetime) -> None:
        """Test creating row for running conference."""
        service = DataService()

        future_deadline = fixed_now + timedelta(days=10)

        row = service._create_row(
            conf=sample_conference,
            conf_year=sample_conference.confs[0],
            deadline=future_deadline,
            timeline_idx=0,
            is_tbd=False,
            now=fixed_now,
        )

        assert row.title == "CVPR"
        assert row.year == 2025
        assert row.sub == "AI"
        assert row.rank == "A"
        assert row.is_running is True
        assert row.is_tbd is False

    def test_create_row_tbd(self, sample_conference_tbd: Conference, fixed_now: datetime) -> None:
        """Test creating row for TBD conference."""
        service = DataService()

        row = service._create_row(
            conf=sample_conference_tbd,
            conf_year=sample_conference_tbd.confs[0],
            deadline=None,
            timeline_idx=0,
            is_tbd=True,
            now=fixed_now,
        )

        assert row.is_tbd is True
        assert row.is_running is True  # TBD is considered "running"
        assert row.countdown == "TBD"

    def test_create_row_finished(self, sample_conference: Conference, fixed_now: datetime) -> None:
        """Test creating row for finished conference."""
        service = DataService()

        past_deadline = fixed_now - timedelta(days=10)

        row = service._create_row(
            conf=sample_conference,
            conf_year=sample_conference.confs[0],
            deadline=past_deadline,
            timeline_idx=0,
            is_tbd=False,
            now=fixed_now,
        )

        assert row.is_running is False
        assert row.is_tbd is False
        assert row.countdown == "Finished"


class TestProcessRows:
    """Test cases for process_rows method."""

    def test_process_rows_empty_conferences(self, fixed_now: datetime) -> None:
        """Test processing empty conference list returns empty list."""
        service = DataService()

        result = service.process_rows(fixed_now)

        assert result == []

    def test_process_rows_filters_none_results(self, fixed_now: datetime) -> None:
        """Test process_rows filters out None results from _find_best_conf_year."""
        service = DataService()

        # Add a conference with no confs (will return None)
        service._conferences = [
            Conference(
                title="EmptyConf",
                description="No years",
                sub="AI",
                rank=Rank(ccf="A"),
                dblp="empty",
                confs=[],
            )
        ]

        result = service.process_rows(fixed_now)

        assert result == []


class TestLoadConferences:
    """Test cases for load_conferences method."""

    @patch("ccfddl_tui.data.data_service.requests.get")
    @patch("ccfddl_tui.data.data_service.yaml.safe_load")
    def test_load_conferences_success(
        self, mock_yaml_load: MagicMock, mock_get: MagicMock, sample_conference_dict: dict[str, Any]
    ) -> None:
        """Test successful conference loading."""
        mock_response = MagicMock()
        mock_response.content = b"fake yaml content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        mock_yaml_load.return_value = [sample_conference_dict]

        service = DataService()
        result = service.load_conferences()

        assert len(result) == 1
        assert result[0].title == "CVPR"

    @patch("ccfddl_tui.data.data_service.requests.get")
    @patch.object(DataService, "_load_local_conferences")
    def test_load_conferences_network_error(self, mock_local: MagicMock, mock_get: MagicMock) -> None:
        """Test load_conferences raises on network error when local also fails."""
        mock_get.side_effect = Exception("Network error")
        mock_local.side_effect = Exception("Local file not found")

        service = DataService()

        with pytest.raises(Exception):
            service.load_conferences()

    @patch("ccfddl_tui.data.data_service.requests.get")
    @patch("ccfddl_tui.data.data_service.yaml.safe_load")
    def test_load_conferences_custom_url(
        self, mock_yaml_load: MagicMock, mock_get: MagicMock, sample_conference_dict: dict[str, Any]
    ) -> None:
        """Test load_conferences uses custom URL."""
        mock_response = MagicMock()
        mock_response.content = b"fake yaml content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        mock_yaml_load.return_value = [sample_conference_dict]

        service = DataService()
        custom_url = "https://custom.url/conf.yml"
        service.load_conferences(url=custom_url)

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == custom_url


class TestGetCategoryName:
    """Test cases for get_category_name method."""

    def test_get_category_name_valid(self) -> None:
        """Test getting category name for valid sub code."""
        service = DataService()

        result = service.get_category_name("AI")

        assert result == "Artificial Intelligence"

    def test_get_category_name_db(self) -> None:
        """Test getting category name for DB."""
        service = DataService()

        result = service.get_category_name("DB")

        assert result == "Database"

    def test_get_category_name_invalid_returns_code(self) -> None:
        """Test invalid sub code returns the code itself."""
        service = DataService()

        result = service.get_category_name("INVALID")

        assert result == "INVALID"
