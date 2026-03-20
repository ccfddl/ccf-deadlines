"""Data layer for CCF-Deadlines TUI.

This module provides data models and services for loading, processing,
and filtering conference data for the TUI display.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import requests
import yaml

from ccfddl.models import Conference, CATEGORIES
from ccfddl.utils import parse_datetime_with_tz, format_duration


@dataclass
class ConferenceRow:
    """Display row for a conference in the TUI table.

    Represents a single row in the conference list, containing all
    the information needed for display and filtering.
    """
    title: str
    year: int
    sub: str  # Category code (e.g., "AI", "DB")
    rank: str  # CCF rank ("A", "B", "C", "N")
    core_rank: Optional[str]  # CORE rank ("A*", "A", "B", "C", "N") or None
    thcpl_rank: Optional[str]  # THCPL rank ("A", "B", "N") or None
    deadline: Optional[datetime]  # Next upcoming deadline (UTC), None if TBD
    countdown: str  # Formatted remaining time or "TBD" or "Finished"
    place: str
    date: str
    link: str
    is_running: bool  # True if deadline hasn't passed
    is_tbd: bool  # True if deadline is TBD
    is_expired: bool  # True if deadline has passed
    is_favorite: bool = False  # True if conference is favorited


class DataService:
    """Service for loading and processing conference data.

    Handles fetching conference data from remote YAML, converting to
    display rows, and providing filtering/search capabilities.
    """

    DEFAULT_URL = "https://ccfddl.github.io/conference/allconf.yml"

    def __init__(self, url: str | None = None):
        """Initialize the data service.

        Args:
            url: URL to fetch conference data from. Defaults to the
                 official CCFDDL allconf.yml URL.
        """
        self.url = url or self.DEFAULT_URL
        self._conferences: list[Conference] = []
        self._using_local_data: bool = False
        self._last_error: Optional[str] = None
        self._favorites: set[str] = self._load_favorites()

    def _get_favorites_path(self) -> Path:
        """Get the path to the favorites file.

        Returns:
            Path to the favorites JSON file in user's home directory.
        """
        return Path.home() / ".ccfddl" / "favorites.json"

    def _load_favorites(self) -> set[str]:
        """Load favorited conference IDs from file.

        Returns:
            Set of conference IDs (title_year) that are favorited.
        """
        favorites_path = self._get_favorites_path()
        if not favorites_path.exists():
            return set()

        try:
            with open(favorites_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("favorites", []))
        except Exception:
            return set()

    def save_favorites(self, favorites: set[str]) -> None:
        """Save favorited conference IDs to file.

        Args:
            favorites: Set of conference IDs to save.
        """
        favorites_path = self._get_favorites_path()
        favorites_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(favorites_path, "w", encoding="utf-8") as f:
                json.dump({"favorites": list(favorites)}, f)
            self._favorites = favorites
        except Exception:
            pass

    def toggle_favorite(self, row: ConferenceRow) -> bool:
        """Toggle favorite status for a conference.

        Args:
            row: ConferenceRow to toggle favorite status for.

        Returns:
            New favorite status (True if now favorited, False if removed).
        """
        conf_id = f"{row.title}_{row.year}"

        if conf_id in self._favorites:
            self._favorites.discard(conf_id)
            is_favorite = False
        else:
            self._favorites.add(conf_id)
            is_favorite = True

        self.save_favorites(self._favorites)
        return is_favorite

    def is_favorite(self, row: ConferenceRow) -> bool:
        """Check if a conference is favorited.

        Args:
            row: ConferenceRow to check.

        Returns:
            True if conference is favorited.
        """
        conf_id = f"{row.title}_{row.year}"
        return conf_id in self._favorites

    def load_conferences(self, url: str | None = None) -> list[Conference]:
        """Load conferences from a YAML URL with local fallback.

        First tries to load from the remote URL. If that fails,
        falls back to loading from local conference files.

        Args:
            url: Optional URL override. If not provided, uses the
                 URL from constructor.

        Returns:
            List of Conference objects.

        Raises:
            Exception: If both remote and local loading fail.
        """
        fetch_url = url or self.url
        self._using_local_data = False
        self._last_error = None

        try:
            response = requests.get(fetch_url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            content = response.content.decode("utf-8")
            data = yaml.safe_load(content)
            self._conferences = [Conference.from_dict(c) for c in data]
            return self._conferences

        except Exception as e:
            self._last_error = f"Remote: {str(e)}"
            try:
                self._conferences = self._load_local_conferences()
                self._using_local_data = True
                return self._conferences
            except Exception as local_e:
                raise Exception(
                    f"Failed to load data from both remote and local sources. "
                    f"Remote error: {self._last_error}, "
                    f"Local error: {str(local_e)}"
                )

    def _load_local_conferences(self) -> list[Conference]:
        """Load conferences from local YAML files.

        Scans the conference/ directory and loads all YAML files,
        merging them into a single list (same as the remote data).

        Returns:
            List of Conference objects.

        Raises:
            Exception: If local data cannot be loaded.
        """
        possible_paths = [
            Path("conference"),
            Path("../../conference"),
            Path(__file__).parent.parent.parent.parent.parent / "conference",
        ]

        conference_dir: Optional[Path] = None
        for path in possible_paths:
            if path.exists() and path.is_dir():
                conference_dir = path
                break

        if conference_dir is None:
            raise Exception("Could not find local conference/ directory")

        yml_files = sorted([
            f for f in conference_dir.rglob("*.yml")
            if f.name != "types.yml"
        ])

        if not yml_files:
            raise Exception(f"No YAML files found in {conference_dir}")

        all_data: list[dict] = []
        for yml_file in yml_files:
            try:
                with open(yml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, list):
                    all_data.extend(data)
            except Exception:
                continue

        if not all_data:
            raise Exception("No valid conference data found in local files")

        return [Conference.from_dict(c) for c in all_data]

    @property
    def using_local_data(self) -> bool:
        """Whether local data is being used (fallback from remote)."""
        return self._using_local_data

    @property
    def last_error(self) -> Optional[str]:
        """Last error message from remote loading attempt."""
        return self._last_error

    def process_rows(self, now: datetime) -> list[ConferenceRow]:
        """Convert conferences to display rows.

        For each conference, finds the earliest upcoming deadline across
        all years and timeline entries. Expired deadlines are skipped.

        Args:
            now: Current datetime (should be timezone-aware, UTC).

        Returns:
            List of ConferenceRow objects, unsorted.
        """
        rows: list[ConferenceRow] = []

        for conf in self._conferences:
            # Find the best conference year to display
            best_row = self._find_best_conf_year(conf, now)
            if best_row:
                rows.append(best_row)

        return rows

    def _find_best_conf_year(self, conf: Conference, now: datetime) -> Optional[ConferenceRow]:
        """Find the best year/timeline entry to display for a conference.

        Priority:
        1. Earliest upcoming deadline (not yet passed)
        2. If no upcoming deadlines, the most recent year (finished)

        Args:
            conf: Conference to process.
            now: Current datetime (UTC).

        Returns:
            ConferenceRow or None if conference has no confs.
        """
        if not conf.confs:
            return None

        best_conf_year = None
        best_deadline: Optional[datetime] = None
        best_timeline_idx = 0
        is_tbd = False

        # First, look for upcoming deadlines
        for conf_year in conf.confs:
            for idx, timeline in enumerate(conf_year.timeline):
                deadline_str = timeline.deadline

                # Check for TBD
                if deadline_str.upper() == "TBD":
                    if best_deadline is None and not is_tbd:
                        # Use TBD only if no running deadline found
                        best_conf_year = conf_year
                        best_timeline_idx = idx
                        is_tbd = True
                    continue

                try:
                    deadline = parse_datetime_with_tz(
                        deadline_str,
                        conf_year.timezone
                    )
                    # Convert to UTC for comparison
                    deadline_utc = deadline.astimezone(timezone.utc)

                    # Skip past deadlines when looking for upcoming
                    if deadline_utc <= now:
                        continue

                    # Keep the earliest upcoming deadline
                    if best_deadline is None or deadline_utc < best_deadline:
                        best_deadline = deadline_utc
                        best_conf_year = conf_year
                        best_timeline_idx = idx
                        is_tbd = False

                except (ValueError, AttributeError):
                    continue

        # If no upcoming deadline, use the most recent year
        if best_conf_year is None:
            # Sort by year descending and take the first
            sorted_confs = sorted(conf.confs, key=lambda c: c.year, reverse=True)
            if sorted_confs:
                best_conf_year = sorted_confs[0]
                best_timeline_idx = 0
                # Try to get the deadline for countdown display
                if best_conf_year.timeline:
                    first_timeline = best_conf_year.timeline[0]
                    if first_timeline.deadline.upper() == "TBD":
                        is_tbd = True
                    else:
                        try:
                            deadline = parse_datetime_with_tz(
                                first_timeline.deadline,
                                best_conf_year.timezone
                            )
                            best_deadline = deadline.astimezone(timezone.utc)
                        except (ValueError, AttributeError):
                            pass

        if best_conf_year is None:
            return None

        # Build the row
        return self._create_row(
            conf, best_conf_year, best_deadline,
            best_timeline_idx, is_tbd, now
        )

    def _create_row(
        self,
        conf: Conference,
        conf_year,
        deadline: Optional[datetime],
        timeline_idx: int,
        is_tbd: bool,
        now: datetime
    ) -> ConferenceRow:
        """Create a ConferenceRow from conference data.

        Args:
            conf: Conference object.
            conf_year: ConferenceYear object.
            deadline: Parsed deadline datetime (UTC) or None.
            timeline_idx: Index of the timeline entry used.
            is_tbd: Whether the deadline is TBD.
            now: Current datetime (UTC).

        Returns:
            ConferenceRow object.
        """
        # Determine status
        is_running = False
        if is_tbd:
            countdown = "TBD"
            is_running = True  # TBD conferences are considered "running"
        elif deadline is None:
            countdown = "N/A"
            is_running = False
        elif deadline > now:
            countdown = format_duration(deadline, now)
            is_running = True
        else:
            countdown = "Finished"
            is_running = False

        return ConferenceRow(
            title=conf.title,
            year=conf_year.year,
            sub=conf.sub,
            rank=conf.rank.ccf,
            core_rank=conf.rank.core,
            thcpl_rank=conf.rank.thcpl,
            deadline=deadline,
            countdown=countdown,
            place=conf_year.place,
            date=conf_year.date,
            link=conf_year.link,
            is_running=is_running,
            is_tbd=is_tbd,
            is_expired=not is_running and not is_tbd,
            is_favorite=self.is_favorite(ConferenceRow(
                title=conf.title,
                year=conf_year.year,
                sub="",
                rank="",
                core_rank=None,
                thcpl_rank=None,
                deadline=None,
                countdown="",
                place="",
                date="",
                link="",
                is_running=False,
                is_tbd=False,
                is_expired=False,
            )),
        )

    def filter_by_sub(
        self,
        rows: list[ConferenceRow],
        subs: set[str]
    ) -> list[ConferenceRow]:
        """Filter rows by category codes.

        Args:
            rows: List of conference rows.
            subs: Set of category codes to include (e.g., {"AI", "DB"}).

        Returns:
            Filtered list of rows.
        """
        if not subs:
            return rows
        return [row for row in rows if row.sub in subs]

    def filter_by_rank(
        self,
        rows: list[ConferenceRow],
        ranks: set[str]
    ) -> list[ConferenceRow]:
        """Filter rows by CCF rank.

        Args:
            rows: List of conference rows.
            ranks: Set of ranks to include (e.g., {"A", "B"}).

        Returns:
            Filtered list of rows.
        """
        if not ranks:
            return rows
        return [row for row in rows if row.rank in ranks]

    def fuzzy_search(
        self,
        rows: list[ConferenceRow],
        query: str
    ) -> list[ConferenceRow]:
        """Search rows by title using fuzzy matching.

        Args:
            rows: List of conference rows.
            query: Search query string.

        Returns:
            List of rows matching the query, sorted by relevance.
        """
        if not query:
            return rows

        query_lower = query.lower()
        matches: list[tuple[ConferenceRow, float]] = []

        for row in rows:
            title_lower = row.title.lower()

            # Exact substring match gets highest score
            if query_lower in title_lower:
                score = 1.0 + (1.0 / (len(title_lower) + 1))
            else:
                # Fuzzy match using SequenceMatcher
                score = SequenceMatcher(
                    None,
                    query_lower,
                    title_lower
                ).ratio()

            # Only include results above threshold
            if score > 0.3:
                matches.append((row, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return [row for row, _ in matches]

    def sort_rows(self, rows: list[ConferenceRow]) -> list[ConferenceRow]:
        """Sort rows for display.

        Sort order:
        1. Favorites (is_favorite=True) - pinned to top
        2. Running conferences (is_running=True, is_tbd=False)
           sorted by remaining time ascending (most urgent first)
        3. TBD conferences (is_tbd=True)
           sorted by year descending
        4. Finished conferences (is_running=False, is_tbd=False)
           sorted by year descending

        Args:
            rows: List of conference rows.

        Returns:
            Sorted list of rows.
        """
        favorites: list[ConferenceRow] = []
        running: list[ConferenceRow] = []
        tbd: list[ConferenceRow] = []
        finished: list[ConferenceRow] = []

        for row in rows:
            if row.is_favorite:
                favorites.append(row)
            elif row.is_tbd:
                tbd.append(row)
            elif row.is_running:
                running.append(row)
            else:
                finished.append(row)

        # Sort favorites by deadline (most urgent first)
        favorites.sort(key=lambda r: r.deadline or datetime.max.replace(tzinfo=timezone.utc))

        # Sort running by deadline (ascending = most urgent first)
        running.sort(key=lambda r: r.deadline or datetime.max.replace(tzinfo=timezone.utc))

        # Sort TBD by year descending
        tbd.sort(key=lambda r: r.year, reverse=True)

        # Sort finished by year descending
        finished.sort(key=lambda r: r.year, reverse=True)

        return favorites + running + tbd + finished
        tbd.sort(key=lambda r: r.year, reverse=True)

        # Sort finished by year descending
        finished.sort(key=lambda r: r.year, reverse=True)

        return running + tbd + finished

    def get_category_name(self, sub: str) -> str:
        """Get the English name for a category code.

        Args:
            sub: Category code (e.g., "AI", "DB").

        Returns:
            English name of the category, or the code if not found.
        """
        for cat in CATEGORIES:
            if cat.sub == sub:
                return cat.name_en
        return sub

    @property
    def conferences(self) -> list[Conference]:
        """Get the loaded conferences."""
        return self._conferences
