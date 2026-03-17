import pytest

from ccfddl.models import (
    Rank,
    Timeline,
    ConferenceYear,
    Conference,
    Category,
    CATEGORIES,
    VALID_SUBS,
    get_category_by_sub,
    get_all_subs,
    is_valid_sub,
)


class TestRank:
    def test_from_dict_full(self):
        data = {"ccf": "A", "core": "A*", "thcpl": "A"}
        rank = Rank.from_dict(data)
        assert rank.ccf == "A"
        assert rank.core == "A*"
        assert rank.thcpl == "A"

    def test_from_dict_minimal(self):
        data = {"ccf": "B"}
        rank = Rank.from_dict(data)
        assert rank.ccf == "B"
        assert rank.core is None
        assert rank.thcpl is None

    def test_to_dict_full(self):
        rank = Rank(ccf="A", core="A*", thcpl="A")
        result = rank.to_dict()
        assert result == {"ccf": "A", "core": "A*", "thcpl": "A"}

    def test_to_dict_minimal(self):
        rank = Rank(ccf="B")
        result = rank.to_dict()
        assert result == {"ccf": "B"}


class TestTimeline:
    def test_from_dict_full(self):
        data = {"deadline": "2025-01-15 23:59:59", "abstract_deadline": "2025-01-08 23:59:59", "comment": "Main"}
        timeline = Timeline.from_dict(data)
        assert timeline.deadline == "2025-01-15 23:59:59"
        assert timeline.abstract_deadline == "2025-01-08 23:59:59"
        assert timeline.comment == "Main"

    def test_from_dict_minimal(self):
        data = {"deadline": "2025-01-15 23:59:59"}
        timeline = Timeline.from_dict(data)
        assert timeline.deadline == "2025-01-15 23:59:59"
        assert timeline.abstract_deadline is None
        assert timeline.comment is None

    def test_to_dict(self):
        timeline = Timeline(deadline="2025-01-15 23:59:59", comment="Test")
        result = timeline.to_dict()
        assert result["deadline"] == "2025-01-15 23:59:59"
        assert result["comment"] == "Test"


class TestConferenceYear:
    def test_from_dict(self):
        data = {
            "year": 2025,
            "id": "cvpr25",
            "link": "https://example.com",
            "timeline": [{"deadline": "2025-01-15 23:59:59"}],
            "timezone": "UTC-8",
            "date": "June 2025",
            "place": "Seattle",
        }
        conf_year = ConferenceYear.from_dict(data)
        assert conf_year.year == 2025
        assert conf_year.id == "cvpr25"
        assert len(conf_year.timeline) == 1

    def test_to_dict(self):
        conf_year = ConferenceYear(
            year=2025,
            id="cvpr25",
            link="https://example.com",
            timeline=[Timeline(deadline="2025-01-15 23:59:59")],
            timezone="UTC-8",
            date="June 2025",
            place="Seattle",
        )
        result = conf_year.to_dict()
        assert result["year"] == 2025
        assert result["id"] == "cvpr25"


class TestConference:
    def test_from_dict(self):
        data = {
            "title": "CVPR",
            "description": "Test Conference",
            "sub": "AI",
            "rank": {"ccf": "A"},
            "dblp": "cvpr",
            "confs": [
                {
                    "year": 2025,
                    "id": "cvpr25",
                    "link": "https://example.com",
                    "timeline": [{"deadline": "2025-01-15 23:59:59"}],
                    "timezone": "UTC-8",
                    "date": "June 2025",
                    "place": "Seattle",
                }
            ],
        }
        conf = Conference.from_dict(data)
        assert conf.title == "CVPR"
        assert conf.sub == "AI"
        assert conf.rank.ccf == "A"
        assert len(conf.confs) == 1

    def test_to_dict(self):
        conf = Conference(
            title="CVPR",
            description="Test",
            sub="AI",
            rank=Rank(ccf="A"),
            dblp="cvpr",
            confs=[],
        )
        result = conf.to_dict()
        assert result["title"] == "CVPR"
        assert result["rank"]["ccf"] == "A"


class TestCategory:
    def test_from_dict(self):
        data = {"name": "人工智能", "name_en": "Artificial Intelligence", "sub": "AI"}
        cat = Category.from_dict(data)
        assert cat.name == "人工智能"
        assert cat.name_en == "Artificial Intelligence"
        assert cat.sub == "AI"

    def test_to_dict(self):
        cat = Category(name="人工智能", name_en="Artificial Intelligence", sub="AI")
        result = cat.to_dict()
        assert result == {"name": "人工智能", "name_en": "Artificial Intelligence", "sub": "AI"}


class TestCategoriesConstants:
    def test_categories_count(self):
        assert len(CATEGORIES) == 10

    def test_valid_subs(self):
        assert "AI" in VALID_SUBS
        assert "DB" in VALID_SUBS
        assert "INVALID" not in VALID_SUBS

    def test_get_category_by_sub(self):
        cat = get_category_by_sub("AI")
        assert cat is not None
        assert cat.name_en == "Artificial Intelligence"

    def test_get_category_by_sub_invalid(self):
        cat = get_category_by_sub("INVALID")
        assert cat is None

    def test_get_all_subs(self):
        subs = get_all_subs()
        assert len(subs) == 10
        assert "AI" in subs

    def test_is_valid_sub(self):
        assert is_valid_sub("AI") is True
        assert is_valid_sub("INVALID") is False
