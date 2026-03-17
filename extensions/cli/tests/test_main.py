import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from ccfddl.__main__ import (
    parse_args,
    extract_alpha_id,
    main,
)
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
    @patch("ccfddl.__main__.requests.get")
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