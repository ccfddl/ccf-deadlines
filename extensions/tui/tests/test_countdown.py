"""Tests for countdown formatters.

This module tests the shared countdown formatting utilities.
"""

from datetime import datetime, timedelta, timezone

import pytest

from ccfddl_tui.utils.formatters import (
    get_countdown_color,
    format_time_remaining,
    format_deadline_countdown,
    format_countdown_from_timedelta,
)


class TestGetCountdownColor:
    """Test cases for get_countdown_color function."""

    def test_get_color_red(self) -> None:
        """Test color is red for less than 1 day."""
        assert get_countdown_color(0) == "red"
        assert get_countdown_color(-1) == "red"

    def test_get_color_yellow(self) -> None:
        """Test color is yellow for 1-6 days."""
        assert get_countdown_color(1) == "yellow"
        assert get_countdown_color(3) == "yellow"
        assert get_countdown_color(6) == "yellow"

    def test_get_color_blue(self) -> None:
        """Test color is blue for 7-29 days."""
        assert get_countdown_color(7) == "blue"
        assert get_countdown_color(15) == "blue"
        assert get_countdown_color(29) == "blue"

    def test_get_color_green(self) -> None:
        """Test color is green for 30+ days."""
        assert get_countdown_color(30) == "green"
        assert get_countdown_color(100) == "green"


class TestFormatTimeRemaining:
    """Test cases for format_time_remaining function."""

    def test_format_time_less_than_day(self) -> None:
        """Test time formatting for less than 1 day."""
        total_seconds = int(timedelta(hours=5, minutes=30, seconds=45).total_seconds())
        result = format_time_remaining(0, total_seconds)
        assert "05:30:45" in result
        assert "day" not in result

    def test_format_time_more_than_day(self) -> None:
        """Test time formatting for more than 1 day."""
        remaining = timedelta(days=5, hours=12, minutes=30, seconds=45)
        result = format_time_remaining(5, int(remaining.total_seconds()))
        assert "5 days" in result
        assert "12:30:45" in result

    def test_format_time_single_day(self) -> None:
        """Test time formatting for exactly 1 day."""
        remaining = timedelta(days=1, hours=2, minutes=30)
        result = format_time_remaining(1, int(remaining.total_seconds()))
        assert "1 day" in result


class TestFormatDeadlineCountdown:
    """Test cases for format_deadline_countdown function."""

    def test_format_countdown_tbd(self) -> None:
        """Test countdown formatting for TBD (None deadline)."""
        result = format_deadline_countdown(None, is_tbd=True)
        assert result.plain == "TBD"

    def test_format_countdown_expired(self) -> None:
        """Test countdown formatting for expired deadline."""
        deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        result = format_deadline_countdown(deadline)
        assert result.plain == "Expired"

    def test_format_countdown_running(self) -> None:
        """Test countdown formatting for running conference."""
        deadline = datetime.now(timezone.utc) + timedelta(days=5)
        result = format_deadline_countdown(deadline)
        assert "days" in result.plain or ":" in result.plain


class TestFormatCountdownFromTimedelta:
    """Test cases for format_countdown_from_timedelta function."""

    def test_format_from_timedelta(self) -> None:
        """Test formatting from timedelta."""
        remaining = timedelta(days=5, hours=12)
        time_str, color = format_countdown_from_timedelta(remaining)
        assert "5 days" in time_str
        assert color == "yellow"  # 5 days is yellow (< 7 days)
