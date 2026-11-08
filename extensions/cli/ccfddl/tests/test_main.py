import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from ccfddl.__main__ import parse_args, main
from ccfddl.fetch import extract_alpha_id, process_conference_deadlines
from ccfddl.models import Conference
from ccfddl.output import output_json, output_table
from ccfddl.utils import format_duration, get_timezone


class TestGetTimezone:
    def test_aoe(self):
        tz = get_timezone("AoE")
        assert tz == timezone(timedelta(hours=-12))

    def test_utc(self):
        tz = get_timezone("UTC")
        assert tz == timezone.utc

    def test_utc_negative(self):
        tz = get_timezone("UTC-8")
        assert tz == timezone(timedelta(hours=-8))

    def test_utc_positive(self):
        tz = get_timezone("UTC+8")
        assert tz == timezone(timedelta(hours=8))

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            get_timezone("GMT+8")


class TestParseArgs:
    def test_no_args(self):
        with patch("sys.argv", ["ccfddl"]):
            args = parse_args()
            assert args.conf is None
            assert args.sub is None
            assert args.rank is None

    def test_conf_args(self):
        with patch("sys.argv", ["ccfddl", "--conf", "CVPR", "ICML"]):
            args = parse_args()
            assert args.conf == ["CVPR", "ICML"]

    def test_sub_args(self):
        with patch("sys.argv", ["ccfddl", "--sub", "AI", "CG"]):
            args = parse_args()
            assert args.sub == ["AI", "CG"]

    def test_rank_args(self):
        with patch("sys.argv", ["ccfddl", "--rank", "A", "B"]):
            args = parse_args()
            assert args.rank == ["A", "B"]

    def test_json_flag(self):
        with patch("sys.argv", ["ccfddl", "--json"]):
            args = parse_args()
            assert args.json is True

    def test_list_categories_flag(self):
        with patch("sys.argv", ["ccfddl", "--list-categories"]):
            args = parse_args()
            assert args.list_categories is True


class TestFormatDuration:
    @pytest.fixture
    def now(self):
        return datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_less_than_one_day(self, now):
        ddl = now + timedelta(hours=5, minutes=30, seconds=45)
        result = format_duration(ddl, now)
        assert "05:30:45" in result

    def test_less_than_30_days(self, now):
        ddl = now + timedelta(days=15, hours=10, minutes=20)
        result = format_duration(ddl, now)
        assert "15 days" in result

    def test_less_than_100_days(self, now):
        ddl = now + timedelta(days=50)
        result = format_duration(ddl, now)
        assert "50 day" in result

    def test_more_than_100_days(self, now):
        ddl = now + timedelta(days=150)
        result = format_duration(ddl, now)
        assert "05 months" in result

    def test_single_day(self, now):
        ddl = now + timedelta(days=1)
        result = format_duration(ddl, now)
        assert "01 day" in result


class TestExtractAlphaId:
    def test_with_digits(self):
        assert extract_alpha_id("CVPR2025") == "cvpr"

    def test_lowercase(self):
        assert extract_alpha_id("cvpr2025") == "cvpr"

    def test_mixed_case(self):
        assert extract_alpha_id("IcMl2025") == "icml"

    def test_no_digits(self):
        assert extract_alpha_id("NEURIPS") == "neurips"

    def test_with_special_chars(self):
        assert extract_alpha_id("CVPR-2025") == "cvpr"

    def test_empty_string(self):
        assert extract_alpha_id("") == ""


class TestMain:
    @patch("ccfddl.fetch.requests.get")
    def test_main_basic(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = """
- title: CVPR
  description: Test Conference
  sub: AI
  rank:
    ccf: A
  dblp: cvpr
  confs:
    - year: 2030
      id: cvpr30
      link: https://example.com
      timeline:
        - deadline: '2030-01-01 12:00:00'
      timezone: UTC+0
      date: June 2030
      place: Test City
""".encode("utf-8")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch("sys.argv", ["ccfddl"]):
            main()

        mock_get.assert_called_once()

    @patch("builtins.print")
    def test_list_categories(self, mock_print):
        with patch("sys.argv", ["ccfddl", "--list-categories"]):
            main()

        printed = [str(call) for call in mock_print.call_args_list]
        assert any("Available Categories" in str(p) for p in printed)


class TestProcessConferenceDeadlines:
    @pytest.fixture
    def siggraph_conf(self):
        return Conference.from_dict({
            "title": "ACM SIGGRAPH",
            "description": "ACM SIGGRAPH Annual Conference",
            "sub": "CG",
            "rank": {"ccf": "A", "core": "A*", "thcpl": "A"},
            "dblp": "siggraph",
            "confs": [
                {
                    "year": 2027,
                    "id": "siggraph27",
                    "link": "https://s2027.siggraph.org/",
                    "timeline": [
                        {
                            "abstract_deadline": "2027-01-21 22:00:00",
                            "deadline": "2027-01-28 22:00:00",
                            "comment": "Submissions form & conflicts / paper deadline",
                        }
                    ],
                    "timezone": "UTC+0",
                    "date": "August 8 - 12, 2027",
                    "place": "Anaheim, California",
                }
            ],
        })

    def test_both_abstract_and_paper_upcoming(self, siggraph_conf):
        ref_date = datetime(2026, 11, 8, 0, 0, 0, tzinfo=timezone.utc)
        results = process_conference_deadlines([siggraph_conf], ref_date)

        assert len(results) == 1
        res = results[0]
        assert res["abstract_deadline_str"] == "2027-01-21 22:00:00 UTC"
        assert res["deadline_str"] == "2027-01-28 22:00:00 UTC"
        assert res["comment"] == "Submissions form & conflicts / paper deadline"
        assert res["next_deadline"] == res["abstract_deadline"]

    def test_abstract_expired_paper_upcoming(self, siggraph_conf):
        ref_date = datetime(2027, 1, 23, 0, 0, 0, tzinfo=timezone.utc)
        results = process_conference_deadlines([siggraph_conf], ref_date)

        assert len(results) == 1
        res = results[0]
        assert res["abstract_deadline"] is None
        assert res["abstract_deadline_str"] is None
        assert res["deadline_str"] == "2027-01-28 22:00:00 UTC"
        assert res["next_deadline"] == res["deadline"]

    def test_sorting_uses_earliest_upcoming_deadline(self):
        ref_date = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        conf_a = Conference.from_dict({
            "title": "Conf A",
            "sub": "AI",
            "rank": {"ccf": "A"},
            "dblp": "a",
            "confs": [
                {
                    "year": 2026,
                    "id": "a26",
                    "link": "https://a.org",
                    "timeline": [
                        {
                            "abstract_deadline": "2026-01-10 12:00:00",
                            "deadline": "2026-01-30 12:00:00",
                        }
                    ],
                    "timezone": "UTC+0",
                    "date": "2026",
                    "place": "City A",
                }
            ],
        })
        conf_b = Conference.from_dict({
            "title": "Conf B",
            "sub": "AI",
            "rank": {"ccf": "A"},
            "dblp": "b",
            "confs": [
                {
                    "year": 2026,
                    "id": "b26",
                    "link": "https://b.org",
                    "timeline": [{"deadline": "2026-01-20 12:00:00"}],
                    "timezone": "UTC+0",
                    "date": "2026",
                    "place": "City B",
                }
            ],
        })
        results = process_conference_deadlines([conf_b, conf_a], ref_date)
        assert [r["title"] for r in results] == ["Conf A", "Conf B"]

    @patch("builtins.print")
    def test_output_table_and_json(self, mock_print, siggraph_conf):
        ref_date = datetime(2026, 11, 8, 0, 0, 0, tzinfo=timezone.utc)
        results = process_conference_deadlines([siggraph_conf], ref_date)

        output_table(results, ref_date)
        table_output = "".join(str(call) for call in mock_print.call_args_list)
        assert "Abs DDL" in table_output
        assert "DDL" in table_output
        assert "74 days" in table_output
        assert "81 days" in table_output

        mock_print.reset_mock()
        output_json(results)
        json_output = "".join(str(call) for call in mock_print.call_args_list)
        assert '"abstract_deadline": "2027-01-21 22:00:00 UTC"' in json_output
        assert '"deadline": "2027-01-28 22:00:00 UTC"' in json_output
        assert '"comment": "Submissions form & conflicts / paper deadline"' in json_output

    @patch("builtins.print")
    def test_abstract_upcoming_paper_tbd(self, mock_print):
        ref_date = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        conf = Conference.from_dict({
            "title": "Conf TBD",
            "sub": "AI",
            "rank": {"ccf": "A"},
            "dblp": "tbd",
            "confs": [
                {
                    "year": 2026,
                    "id": "tbd26",
                    "link": "https://tbd.org",
                    "timeline": [
                        {
                            "abstract_deadline": "2026-02-01 12:00:00",
                            "deadline": "TBD",
                            "comment": "Abstract first, full paper TBD",
                        }
                    ],
                    "timezone": "UTC+0",
                    "date": "2026",
                    "place": "City",
                }
            ],
        })
        results = process_conference_deadlines([conf], ref_date)
        assert len(results) == 1
        res = results[0]
        assert res["abstract_deadline_str"] == "2026-02-01 12:00:00 UTC"
        assert res["deadline"] is None
        assert res["deadline_str"] is None
        assert res["comment"] == "Abstract first, full paper TBD"
        assert res["next_deadline"] == res["abstract_deadline"]

        output_table(results, ref_date)
        table_output = "".join(str(call) for call in mock_print.call_args_list)
        assert "31 days" in table_output
        assert "TBD" in table_output

        mock_print.reset_mock()
        output_json(results)
        json_output = "".join(str(call) for call in mock_print.call_args_list)
        assert '"abstract_deadline": "2026-02-01 12:00:00 UTC"' in json_output
        assert '"deadline": null' in json_output
        assert '"comment": "Abstract first, full paper TBD"' in json_output

    @patch("builtins.print")
    def test_multiple_rounds_selected_round_consistency(self, mock_print):
        conf = Conference.from_dict({
            "title": "Conf Multi",
            "sub": "AI",
            "rank": {"ccf": "B"},
            "dblp": "multi",
            "confs": [
                {
                    "year": 2026,
                    "id": "multi26",
                    "link": "https://multi.org",
                    "timeline": [
                        {
                            "abstract_deadline": "2026-01-10 12:00:00",
                            "deadline": "2026-02-15 12:00:00",
                            "comment": "Round 1",
                        },
                        {
                            "abstract_deadline": "2026-04-01 12:00:00",
                            "deadline": "2026-04-15 12:00:00",
                            "comment": "Round 2",
                        },
                    ],
                    "timezone": "UTC+0",
                    "date": "2026",
                    "place": "City",
                }
            ],
        })

        # Phase 1: In Round 1, abstract has passed but paper deadline is upcoming.
        # Round 2 is further in the future.
        ref_date_1 = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
        results_1 = process_conference_deadlines([conf], ref_date_1)
        assert len(results_1) == 1
        res_1 = results_1[0]
        # Must select Round 1: abstract_deadline is None (expired), paper deadline is Feb 15
        assert res_1["abstract_deadline"] is None
        assert res_1["abstract_deadline_str"] is None
        assert res_1["deadline_str"] == "2026-02-15 12:00:00 UTC"
        assert res_1["comment"] == "Round 1"
        assert res_1["next_deadline"] == res_1["deadline"]

        output_table(results_1, ref_date_1)
        table_output = "".join(str(call) for call in mock_print.call_args_list)
        assert "14 days" in table_output

        mock_print.reset_mock()
        output_json(results_1)
        json_output = "".join(str(call) for call in mock_print.call_args_list)
        assert '"abstract_deadline": null' in json_output
        assert '"deadline": "2026-02-15 12:00:00 UTC"' in json_output
        assert '"comment": "Round 1"' in json_output

        # Phase 2: Round 1 fully passed, now active round is Round 2.
        ref_date_2 = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
        results_2 = process_conference_deadlines([conf], ref_date_2)
        assert len(results_2) == 1
        res_2 = results_2[0]
        assert res_2["abstract_deadline_str"] == "2026-04-01 12:00:00 UTC"
        assert res_2["deadline_str"] == "2026-04-15 12:00:00 UTC"
        assert res_2["comment"] == "Round 2"
        assert res_2["next_deadline"] == res_2["abstract_deadline"]
