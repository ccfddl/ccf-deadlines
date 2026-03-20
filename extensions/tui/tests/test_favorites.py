"""Tests for favorite functionality and rank display.

This module tests the favorite feature, including persistence,
sorting, and rank display in the conference table.
"""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from ccfddl_tui.data.data_service import DataService, ConferenceRow


class TestFavoriteFunctionality:
    """Test favorite functionality in DataService."""

    def test_conference_row_has_favorite_field(self):
        """ConferenceRow should have is_favorite field."""
        row = ConferenceRow(
            title="Test Conf",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A*",
            thcpl_rank="A",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            countdown="30 days",
            place="Test",
            date="2025",
            link="http://test.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
            is_favorite=True,
        )

        assert row.is_favorite is True

    def test_conference_row_default_favorite_false(self):
        """ConferenceRow should default is_favorite to False."""
        row = ConferenceRow(
            title="Test Conf",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            countdown="30 days",
            place="Test",
            date="2025",
            link="http://test.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        )

        assert row.is_favorite is False

    def test_data_service_has_favorites_set(self):
        """DataService should have _favorites set."""
        service = DataService()
        assert hasattr(service, "_favorites")
        assert isinstance(service._favorites, set)

    def test_toggle_favorite_adds_conference(self):
        """toggle_favorite should add conference to favorites."""
        with tempfile.TemporaryDirectory() as tmpdir:
            favorites_path = Path(tmpdir) / "favorites.json"

            service = DataService()
            service._get_favorites_path = lambda: favorites_path
            service._favorites = service._load_favorites()

            row = ConferenceRow(
                title="CVPR",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A*",
                thcpl_rank="A",
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                countdown="30 days",
                place="Test",
                date="2025",
                link="http://test.com",
                is_running=True,
                is_tbd=False,
                is_expired=False,
                is_favorite=False,
            )

            result = service.toggle_favorite(row)

            assert result is True
            assert service.is_favorite(row) is True

    def test_toggle_favorite_removes_conference(self):
        """toggle_favorite should remove conference from favorites."""
        with tempfile.TemporaryDirectory() as tmpdir:
            favorites_path = Path(tmpdir) / "favorites.json"

            service = DataService()
            service._get_favorites_path = lambda: favorites_path
            service._favorites = service._load_favorites()

            row = ConferenceRow(
                title="CVPR",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A*",
                thcpl_rank="A",
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                countdown="30 days",
                place="Test",
                date="2025",
                link="http://test.com",
                is_running=True,
                is_tbd=False,
                is_expired=False,
                is_favorite=True,
            )

            # Add first
            service.toggle_favorite(row)
            assert service.is_favorite(row) is True

            # Remove
            result = service.toggle_favorite(row)

            assert result is False
            assert service.is_favorite(row) is False

    def test_favorites_persistence(self):
        """Favorites should be persisted to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            favorites_path = Path(tmpdir) / "favorites.json"

            service = DataService()
            service._get_favorites_path = lambda: favorites_path

            row = ConferenceRow(
                title="ICML",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                countdown="30 days",
                place="Test",
                date="2025",
                link="http://test.com",
                is_running=True,
                is_tbd=False,
                is_expired=False,
            )

            service.toggle_favorite(row)

            # Check file was created
            assert favorites_path.exists()

            # Check file contents
            with open(favorites_path, "r") as f:
                data = json.load(f)
                assert "ICML_2025" in data["favorites"]

    def test_load_favorites_from_file(self):
        """Favorites should be loaded from file on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            favorites_path = Path(tmpdir) / "favorites.json"
            favorites_path.parent.mkdir(parents=True, exist_ok=True)

            # Create favorites file
            with open(favorites_path, "w") as f:
                json.dump({"favorites": ["NeurIPS_2025", "ICML_2025"]}, f)

            service = DataService()
            service._get_favorites_path = lambda: favorites_path
            service._favorites = service._load_favorites()

            row1 = ConferenceRow(
                title="NeurIPS", year=2025, sub="AI", rank="A",
                core_rank="A", thcpl_rank="A", deadline=None, countdown="TBD",
                place="Test", date="2025", link="http://test.com",
                is_running=True, is_tbd=True, is_expired=False,
            )
            row2 = ConferenceRow(
                title="ICML", year=2025, sub="AI", rank="A",
                core_rank="A", thcpl_rank="A", deadline=None, countdown="TBD",
                place="Test", date="2025", link="http://test.com",
                is_running=True, is_tbd=True, is_expired=False,
            )

            assert service.is_favorite(row1) is True
            assert service.is_favorite(row2) is True


class TestFavoriteSorting:
    """Test that favorites are sorted to the top."""

    def test_favorites_pinned_to_top(self):
        """Favorites should appear first in sorted results."""
        service = DataService()
        now = datetime.now(timezone.utc)

        rows = [
            ConferenceRow(
                title="Regular Conf",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                deadline=now + timedelta(days=10),
                countdown="10 days",
                place="Test",
                date="2025",
                link="http://test.com",
                is_running=True,
                is_tbd=False,
                is_expired=False,
                is_favorite=False,
            ),
            ConferenceRow(
                title="Favorite Conf",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                deadline=now + timedelta(days=30),
                countdown="30 days",
                place="Test",
                date="2025",
                link="http://test.com",
                is_running=True,
                is_tbd=False,
                is_expired=False,
                is_favorite=True,
            ),
        ]

        sorted_rows = service.sort_rows(rows)

        assert sorted_rows[0].title == "Favorite Conf"
        assert sorted_rows[1].title == "Regular Conf"

    def test_favorites_sorted_by_deadline(self):
        """Multiple favorites should be sorted by deadline."""
        service = DataService()
        now = datetime.now(timezone.utc)

        rows = [
            ConferenceRow(
                title="Favorite Later",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                deadline=now + timedelta(days=30),
                countdown="30 days",
                place="Test",
                date="2025",
                link="http://test.com",
                is_running=True,
                is_tbd=False,
                is_expired=False,
                is_favorite=True,
            ),
            ConferenceRow(
                title="Favorite Soon",
                year=2025,
                sub="AI",
                rank="A",
                core_rank="A",
                thcpl_rank="A",
                deadline=now + timedelta(days=5),
                countdown="5 days",
                place="Test",
                date="2025",
                link="http://test.com",
                is_running=True,
                is_tbd=False,
                is_expired=False,
                is_favorite=True,
            ),
        ]

        sorted_rows = service.sort_rows(rows)

        assert sorted_rows[0].title == "Favorite Soon"
        assert sorted_rows[1].title == "Favorite Later"


class TestRankDisplay:
    """Test rank display in ConferenceRow."""

    def test_ccf_rank_display(self):
        """ConferenceRow should store CCF rank."""
        row = ConferenceRow(
            title="Test",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A*",
            thcpl_rank="A",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            countdown="30 days",
            place="Test",
            date="2025",
            link="http://test.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        )

        assert row.rank == "A"

    def test_core_rank_display(self):
        """ConferenceRow should store CORE rank."""
        row = ConferenceRow(
            title="Test",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A*",
            thcpl_rank="A",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            countdown="30 days",
            place="Test",
            date="2025",
            link="http://test.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        )

        assert row.core_rank == "A*"

    def test_thcpl_rank_display(self):
        """ConferenceRow should store THCPL rank."""
        row = ConferenceRow(
            title="Test",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="B",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            countdown="30 days",
            place="Test",
            date="2025",
            link="http://test.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        )

        assert row.thcpl_rank == "B"

    def test_optional_ranks_none(self):
        """CORE and THCPL ranks should be optional (None)."""
        row = ConferenceRow(
            title="Test",
            year=2025,
            sub="AI",
            rank="A",
            core_rank=None,
            thcpl_rank=None,
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            countdown="30 days",
            place="Test",
            date="2025",
            link="http://test.com",
            is_running=True,
            is_tbd=False,
            is_expired=False,
        )

        assert row.core_rank is None
        assert row.thcpl_rank is None
