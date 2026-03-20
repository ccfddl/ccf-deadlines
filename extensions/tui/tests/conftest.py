"""Shared fixtures for CCF Deadlines TUI tests."""

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from ccfddl.models import Conference, ConferenceYear, Rank, Timeline

from ccfddl_tui.data.data_service import ConferenceRow


# =============================================================================
# ConferenceRow fixtures
# =============================================================================

@pytest.fixture
def sample_conference_row_running() -> ConferenceRow:
    """Create a sample ConferenceRow with a running deadline (not expired, not TBD)."""
    deadline = datetime.now(timezone.utc) + timedelta(days=5)
    return ConferenceRow(
        title="CVPR",
        year=2025,
        sub="AI",
        rank="A",
        core_rank="A",
        thcpl_rank="A",
        is_expired=False,
        is_favorite=False,
        deadline=deadline,
        countdown="5 days, 12:30",
        place="Seattle, USA",
        date="June 15-20, 2025",
        link="https://cvpr2025.thecvf.com/",
        is_running=True,
        is_tbd=False,
    )


@pytest.fixture
def sample_conference_row_tbd() -> ConferenceRow:
    """Create a sample ConferenceRow with TBD deadline."""
    return ConferenceRow(
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
        date="December 8-14, 2025",
        link="https://neurips.cc/",
        is_running=True,
        is_tbd=True,
    )


@pytest.fixture
def sample_conference_row_finished() -> ConferenceRow:
    """Create a sample ConferenceRow with finished deadline (already passed)."""
    deadline = datetime.now(timezone.utc) - timedelta(days=10)
    return ConferenceRow(
        title="ICML",
        year=2024,
        sub="AI",
        rank="A",
        core_rank="A",
        thcpl_rank="A",
        is_expired=False,
        is_favorite=False,
        deadline=deadline,
        countdown="Finished",
        place="Vienna, Austria",
        date="July 21-27, 2024",
        link="https://icml.cc/",
        is_running=False,
        is_tbd=False,
    )


@pytest.fixture
def sample_conference_rows_mixed() -> list[ConferenceRow]:
    """Create a list of ConferenceRows with mixed statuses (running, TBD, finished)."""
    now = datetime.now(timezone.utc)
    
    # Running conferences (different deadlines to test sorting)
    running1 = ConferenceRow(
        title="CVPR",
        year=2025,
        sub="AI",
        rank="A",
        core_rank="A",
        thcpl_rank="A",
        is_expired=False,
        is_favorite=False,
        deadline=now + timedelta(days=5),
        countdown="5 days, 12:30",
        place="Seattle, USA",
        date="June 15-20, 2025",
        link="https://cvpr2025.thecvf.com/",
        is_running=True,
        is_tbd=False,
    )
    
    running2 = ConferenceRow(
        title="ICLR",
        year=2025,
        sub="AI",
        rank="A",
        core_rank="A",
        thcpl_rank="A",
        is_expired=False,
        is_favorite=False,
        deadline=now + timedelta(days=2),  # More urgent
        countdown="2 days, 05:00",
        place="Singapore",
        date="April 24-28, 2025",
        link="https://iclr.cc/",
        is_running=True,
        is_tbd=False,
    )
    
    running3 = ConferenceRow(
        title="SIGMOD",
        year=2025,
        sub="DB",
        rank="A",
        core_rank="A",
        thcpl_rank="A",
        is_expired=False,
        is_favorite=False,
        deadline=now + timedelta(days=30),
        countdown="30 days",
        place="Berlin, Germany",
        date="June 14-19, 2025",
        link="https://sigmod2025.org/",
        is_running=True,
        is_tbd=False,
    )
    
    # TBD conference
    tbd = ConferenceRow(
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
        date="December 8-14, 2025",
        link="https://neurips.cc/",
        is_running=True,
        is_tbd=True,
    )
    
    # Finished conferences
    finished1 = ConferenceRow(
        title="ICML",
        year=2024,
        sub="AI",
        rank="A",
        core_rank="A",
        thcpl_rank="A",
        is_expired=False,
        is_favorite=False,
        deadline=now - timedelta(days=30),
        countdown="Finished",
        place="Vienna, Austria",
        date="July 21-27, 2024",
        link="https://icml.cc/",
        is_running=False,
        is_tbd=False,
    )
    
    finished2 = ConferenceRow(
        title="VLDB",
        year=2024,
        sub="DB",
        rank="A",
        core_rank="A",
        thcpl_rank="A",
        is_expired=False,
        is_favorite=False,
        deadline=now - timedelta(days=60),
        countdown="Finished",
        place="Guangzhou, China",
        date="August 26-30, 2024",
        link="https://vldb.org/",
        is_running=False,
        is_tbd=False,
    )
    
    return [running1, running2, running3, tbd, finished1, finished2]


@pytest.fixture
def sample_conference_rows_various_categories() -> list[ConferenceRow]:
    """Create ConferenceRows with different categories (sub) for filter testing."""
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=10)
    
    return [
        ConferenceRow(
            title="CVPR",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Seattle, USA",
            date="June 15-20, 2025",
            link="https://cvpr2025.thecvf.com/",
            is_running=True,
            is_tbd=False,
        ),
        ConferenceRow(
            title="SIGMOD",
            year=2025,
            sub="DB",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Berlin, Germany",
            date="June 14-19, 2025",
            link="https://sigmod2025.org/",
            is_running=True,
            is_tbd=False,
        ),
        ConferenceRow(
            title="SIGGRAPH",
            year=2025,
            sub="CG",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Denver, USA",
            date="August 10-14, 2025",
            link="https://siggraph.org/",
            is_running=True,
            is_tbd=False,
        ),
        ConferenceRow(
            title="ICSE",
            year=2025,
            sub="SE",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Milan, Italy",
            date="June 28-July 3, 2025",
            link="https://icse2025.org/",
            is_running=True,
            is_tbd=False,
        ),
    ]


@pytest.fixture
def sample_conference_rows_various_ranks() -> list[ConferenceRow]:
    """Create ConferenceRows with different CCF ranks for filter testing."""
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=10)
    
    return [
        ConferenceRow(
            title="CVPR",
            year=2025,
            sub="AI",
            rank="A",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Seattle, USA",
            date="June 15-20, 2025",
            link="https://cvpr2025.thecvf.com/",
            is_running=True,
            is_tbd=False,
        ),
        ConferenceRow(
            title="ECCV",
            year=2025,
            sub="AI",
            rank="B",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Milan, Italy",
            date="September 2025",
            link="https://eccv2025.eu/",
            is_running=True,
            is_tbd=False,
        ),
        ConferenceRow(
            title="ACCV",
            year=2025,
            sub="AI",
            rank="C",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Singapore",
            date="December 2025",
            link="https://accv2025.org/",
            is_running=True,
            is_tbd=False,
        ),
        ConferenceRow(
            title="LocalConf",
            year=2025,
            sub="AI",
            rank="N",
            core_rank="A",
            thcpl_rank="A",
            is_expired=False,
        is_favorite=False,
            deadline=deadline,
            countdown="10 days",
            place="Beijing, China",
            date="October 2025",
            link="https://localconf.org/",
            is_running=True,
            is_tbd=False,
        ),
    ]


# =============================================================================
# Conference (from ccfddl.models) fixtures
# =============================================================================

@pytest.fixture
def sample_conference_dict() -> dict[str, Any]:
    """Create a sample conference dictionary matching YAML structure."""
    return {
        "title": "CVPR",
        "description": "IEEE Conference on Computer Vision and Pattern Recognition",
        "sub": "AI",
        "rank": {"ccf": "A", "core": "A*", "thcpl": "A"},
        "dblp": "cvpr",
        "confs": [
            {
                "year": 2025,
                "id": "cvpr25",
                "link": "https://cvpr2025.thecvf.com/",
                "timeline": [
                    {
                        "deadline": "2024-11-15 23:59:59",
                        "comment": "Main deadline",
                    }
                ],
                "timezone": "UTC-8",
                "date": "June 15-20, 2025",
                "place": "Seattle, USA",
            }
        ],
    }


@pytest.fixture
def sample_conference() -> Conference:
    """Create a sample Conference object."""
    return Conference(
        title="CVPR",
        description="IEEE Conference on Computer Vision and Pattern Recognition",
        sub="AI",
        rank=Rank(ccf="A", core="A*", thcpl="A"),
        dblp="cvpr",
        confs=[
            ConferenceYear(
                year=2025,
                id="cvpr25",
                link="https://cvpr2025.thecvf.com/",
                timeline=[
                    Timeline(
                        deadline="2024-11-15 23:59:59",
                        comment="Main deadline",
                    )
                ],
                timezone="UTC-8",
                date="June 15-20, 2025",
                place="Seattle, USA",
            )
        ],
    )


@pytest.fixture
def sample_conference_tbd() -> Conference:
    """Create a sample Conference with TBD deadline."""
    return Conference(
        title="NeurIPS",
        description="Conference on Neural Information Processing Systems",
        sub="AI",
        rank=Rank(ccf="A"),
        dblp="neurips",
        confs=[
            ConferenceYear(
                year=2025,
                id="neurips25",
                link="https://neurips.cc/",
                timeline=[
                    Timeline(deadline="TBD")
                ],
                timezone="UTC-12",
                date="December 8-14, 2025",
                place="Vancouver, Canada",
            )
        ],
    )


@pytest.fixture
def sample_conference_multiple_years() -> Conference:
    """Create a sample Conference with multiple years."""
    return Conference(
        title="ICML",
        description="International Conference on Machine Learning",
        sub="AI",
        rank=Rank(ccf="A"),
        dblp="icml",
        confs=[
            ConferenceYear(
                year=2024,
                id="icml24",
                link="https://icml.cc/2024/",
                timeline=[
                    Timeline(deadline="2024-02-01 23:59:59")
                ],
                timezone="UTC-8",
                date="July 21-27, 2024",
                place="Vienna, Austria",
            ),
            ConferenceYear(
                year=2025,
                id="icml25",
                link="https://icml.cc/2025/",
                timeline=[
                    Timeline(
                        deadline="2025-02-01 23:59:59",
                        comment="Main deadline",
                    )
                ],
                timezone="UTC-8",
                date="July 2025",
                place="TBD",
            ),
        ],
    )


@pytest.fixture
def sample_conference_multiple_timelines() -> Conference:
    """Create a sample Conference with multiple timeline entries (multiple deadlines)."""
    return Conference(
        title="SIGMOD",
        description="ACM Conference on Management of Data",
        sub="DB",
        rank=Rank(ccf="A"),
        dblp="sigmod",
        confs=[
            ConferenceYear(
                year=2025,
                id="sigmod25",
                link="https://sigmod2025.org/",
                timeline=[
                    Timeline(
                        deadline="2024-07-15 17:00:00",
                        comment="First round",
                    ),
                    Timeline(
                        deadline="2024-10-15 17:00:00",
                        comment="Second round",
                    ),
                ],
                timezone="UTC-8",
                date="June 14-19, 2025",
                place="Berlin, Germany",
            )
        ],
    )


# =============================================================================
# Mock datetime fixtures
# =============================================================================

@pytest.fixture
def fixed_now() -> datetime:
    """Return a fixed datetime for testing (2025-01-15 12:00:00 UTC)."""
    return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def future_deadline() -> datetime:
    """Return a future deadline datetime (30 days from fixed_now)."""
    return datetime(2025, 2, 14, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def past_deadline() -> datetime:
    """Return a past deadline datetime (30 days before fixed_now)."""
    return datetime(2024, 12, 16, 12, 0, 0, tzinfo=timezone.utc)