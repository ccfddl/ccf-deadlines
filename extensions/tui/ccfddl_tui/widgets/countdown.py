"""Countdown widget for displaying remaining time until conference deadlines.

This module provides a real-time countdown widget that displays remaining time
with color-coded urgency indicators.
"""

from datetime import datetime, timezone
from typing import Optional

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

from ..utils.formatters import format_countdown_from_timedelta


class CountdownWidget(Static):
    """A widget that displays a real-time countdown to a deadline.

    The countdown updates every second and uses color-coded display based
    on remaining time:
        - Red (danger): < 1 day remaining
        - Yellow (warning): < 7 days remaining
        - Blue (info): < 30 days remaining
        - Green (success): >= 30 days remaining

    Attributes:
        deadline: Reactive attribute holding the deadline datetime (timezone-aware)
                 or None for TBD deadlines.

    Example:
        ```python
        from datetime import datetime, timezone, timedelta

        widget = CountdownWidget()
        widget.deadline = datetime.now(timezone.utc) + timedelta(days=5)
        ```
    """

    DEFAULT_CSS = """
    CountdownWidget {
        width: auto;
        height: auto;
    }
    """

    # Reactive deadline attribute - can be set externally to update display
    deadline: Optional[datetime] = reactive(None)

    def __init__(
        self,
        deadline: Optional[datetime] = None,
        *,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
        disabled: bool = False,
    ) -> None:
        """Initialize the countdown widget.

        Args:
            deadline: Optional initial deadline datetime (should be timezone-aware).
            name: The name of the widget.
            id: The ID of the widget in the DOM.
            classes: Space-separated list of class names.
            disabled: Whether the widget is disabled.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.deadline = deadline
        self._interval_id: Optional[str] = None

    def on_mount(self) -> None:
        """Set up the countdown update interval when widget is mounted."""
        # Update every second
        self.set_interval(1, self._update_countdown)
        # Initial update
        self._update_countdown()

    def _update_countdown(self) -> None:
        """Calculate remaining time and update the widget display."""
        text = self._format_countdown()
        self.update(text)

    def _format_countdown(self) -> Text:
        """Format the countdown display with appropriate color.

        Returns:
            Rich Text object with color-coded countdown string.
        """
        # Handle TBD (deadline is None)
        if self.deadline is None:
            return Text("TBD", style="dim")

        # Get current time (timezone-aware)
        now = datetime.now(timezone.utc)

        # Ensure deadline is timezone-aware
        deadline = self.deadline
        if deadline.tzinfo is None:
            # Assume UTC if no timezone specified
            deadline = deadline.replace(tzinfo=timezone.utc)

        # Calculate remaining time
        remaining = deadline - now

        # Handle expired deadline
        if remaining.total_seconds() <= 0:
            return Text("Expired", style="red")

        # Use shared formatter
        time_str, color = format_countdown_from_timedelta(remaining)

        return Text(time_str, style=color)

    def set_deadline(self, deadline: Optional[datetime]) -> None:
        """Set a new deadline for the countdown.

        This is a convenience method that sets the reactive deadline attribute.

        Args:
            deadline: The new deadline datetime (should be timezone-aware) or None for TBD.
        """
        self.deadline = deadline

    def watch_deadline(self, old_deadline: Optional[datetime], new_deadline: Optional[datetime]) -> None:
        """React to deadline changes.

        Args:
            old_deadline: Previous deadline value.
            new_deadline: New deadline value.
        """
        # Immediately update display when deadline changes
        self._update_countdown()