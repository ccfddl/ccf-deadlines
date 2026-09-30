"""Date precision must survive filtering, sorting and CLI formatting."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest
import yaml

from ccfddl.fetch import process_conference_deadlines
from ccfddl.models import Conference
from ccfddl.output import output_json, output_table
from ccfddl.utils import (
    deadline_has_passed,
    deadline_sort_key,
    format_duration,
    get_timezone,
    parse_deadline,
)


def conference(deadlines, zone="Unknown", conf_id="test28"):
    return Conference.from_dict({
        "title": "TEST", "description": "Test conference", "sub": "AI",
        "rank": {"ccf": "A"}, "dblp": "test",
        "confs": [{
            "year": 2028, "id": conf_id, "link": "https://example.org/",
            "timeline": [{"deadline": value} for value in deadlines],
            "timezone": zone, "date": "March 2028", "place": "Online",
        }],
    })


def test_date_parser_preserves_leap_day_and_yaml_native_dates():
    for value in ("2028-02-29", yaml.safe_load("2028-02-29")):
        parsed = parse_deadline(value, "Unknown")
        assert type(parsed) is date
        assert parsed == date(2028, 2, 29)
    assert type(parse_deadline("2028-02-29", "AoE")) is date


@pytest.mark.parametrize("value", [
    "2027-02-29", "2028-04-31", "2028-13-01", "2028-00-01",
    "2028-2-29", "20280229", "2028-W09-2", "2028-02-29 ", "TBD", "", None,
])
def test_invalid_dates_do_not_gain_a_time(value):
    with pytest.raises(ValueError):
        parse_deadline(value, "Unknown")


def test_unknown_precise_timezone_is_not_utc():
    with pytest.raises(ValueError):
        get_timezone("Unknown")
    with pytest.raises(ValueError):
        parse_deadline("2028-02-29 12:00:00", "Unknown")


def test_precise_datetime_and_pt_behavior_remain_unchanged():
    deadline = parse_deadline("2028-07-01 12:30:45", "PT")
    assert deadline.utcoffset() == timedelta(hours=-7)
    assert deadline.astimezone(timezone.utc) == datetime(2028, 7, 1, 19, 30, 45, tzinfo=timezone.utc)
    assert not deadline_has_passed(deadline, deadline, "PT")
    assert deadline_has_passed(deadline, deadline + timedelta(seconds=1), "PT")


def test_unknown_date_stays_pending_until_day_has_passed_everywhere():
    deadline = date(2028, 2, 29)
    for now in (
        datetime(2028, 2, 29, 0, tzinfo=timezone.utc),
        datetime(2028, 2, 29, 23, 59, 59, tzinfo=timezone.utc),
        datetime(2028, 3, 1, 11, 59, 59, tzinfo=timezone.utc),
    ):
        assert not deadline_has_passed(deadline, now, "Unknown")
    assert deadline_has_passed(deadline, datetime(2028, 3, 1, 12, tzinfo=timezone.utc), "Unknown")


def test_known_date_uses_source_calendar_day():
    deadline = date(2028, 2, 29)
    assert not deadline_has_passed(deadline, datetime(2028, 2, 29, 15, 59, 59, tzinfo=timezone.utc), "UTC+8")
    assert deadline_has_passed(deadline, datetime(2028, 2, 29, 16, tzinfo=timezone.utc), "UTC+8")
    with pytest.raises(ValueError):
        deadline_has_passed(deadline, datetime(2028, 2, 29), "Unknown")


def test_mixed_rounds_keep_later_real_candidates_without_estimates():
    now = datetime(2028, 3, 1, 12, tzinfo=timezone.utc)
    inputs = [
        conference(["2028-02-29", "TBD", "2028-03-02 11:00:00"], "UTC", "precise"),
        conference(["2028-02-29 11:00:00", "2028-03-02", "TBD"], "UTC", "date"),
        conference(["2028-02-29", "TBD"], "Unknown", "expired"),
        conference(["TBD", "2028-02-30"], "Unknown", "invalid"),
        conference(["2028-03-04 12:00:00"], "Unknown", "unknown-clock"),
    ]
    results = process_conference_deadlines(inputs, now)
    assert [item["id"] for item in results] == ["date", "precise"]
    assert type(results[0]["deadline"]) is date
    assert results[0]["deadline_str"] == "2028-03-02"
    assert results[0]["precision"] == "date"
    assert isinstance(results[1]["deadline"], datetime)
    assert results[1]["precision"] == "datetime"


def test_same_day_round_is_not_dropped_and_earliest_upcoming_is_selected():
    now = datetime(2028, 3, 1, 11, 59, 59, tzinfo=timezone.utc)
    results = process_conference_deadlines([
        conference(["2028-03-05", "2028-02-29"], "Unknown"),
    ], now)
    assert results[0]["deadline"] == date(2028, 2, 29)
    assert results[0]["timezone"] == "Unknown"


def test_calendar_sort_key_does_not_assign_date_a_clock():
    day = date(2028, 2, 29)
    instant = datetime(2028, 2, 29, 1, tzinfo=timezone.utc)
    assert type(day) is date
    assert sorted([instant, day], key=lambda value: deadline_sort_key(value, "UTC")) == [day, instant]


def test_mixed_zone_lower_bound_ordering_is_internal_only():
    now = datetime(2028, 2, 28, tzinfo=timezone.utc)
    results = process_conference_deadlines([
        conference(["2028-03-01"], "UTC+8", "known-date"),
        conference(["2028-02-29 18:00:00"], "UTC", "precise"),
        conference(["2028-03-01"], "Unknown", "unknown-date"),
    ], now)
    assert [item["id"] for item in results] == ["unknown-date", "known-date", "precise"]
    assert all(type(item["deadline"]) is date for item in results[:2])
    assert results[0]["deadline_str"] == results[1]["deadline_str"] == "2028-03-01"


def test_mixed_round_selection_uses_source_zone_bounds():
    now = datetime(2028, 2, 28, tzinfo=timezone.utc)
    results = process_conference_deadlines([
        conference(["2028-03-01 01:00:00", "2028-03-01"], "UTC+8"),
    ], now)
    assert type(results[0]["deadline"]) is date
    assert results[0]["deadline"] == date(2028, 3, 1)


@pytest.mark.parametrize("day,before,after", [
    (date(2028, 3, 11), datetime(2028, 3, 12, 7, 59, 59, tzinfo=timezone.utc),
     datetime(2028, 3, 12, 8, tzinfo=timezone.utc)),
    (date(2028, 3, 12), datetime(2028, 3, 13, 6, 59, 59, tzinfo=timezone.utc),
     datetime(2028, 3, 13, 7, tzinfo=timezone.utc)),
    (date(2028, 11, 4), datetime(2028, 11, 5, 6, 59, 59, tzinfo=timezone.utc),
     datetime(2028, 11, 5, 7, tzinfo=timezone.utc)),
    (date(2028, 11, 5), datetime(2028, 11, 6, 7, 59, 59, tzinfo=timezone.utc),
     datetime(2028, 11, 6, 8, tzinfo=timezone.utc)),
])
def test_pt_date_expiry_across_dst_transitions(day, before, after):
    assert not deadline_has_passed(day, before, "PT")
    assert deadline_has_passed(day, after, "PT")


def test_pt_lower_bound_uses_midnight_offset_before_dst_switch():
    spring_day = date(2028, 3, 12)
    spring_start = datetime(2028, 3, 12, 8, tzinfo=timezone.utc)
    fall_day = date(2028, 11, 5)
    fall_start = datetime(2028, 11, 5, 7, tzinfo=timezone.utc)
    assert deadline_sort_key(spring_day, "PT") == deadline_sort_key(spring_start, "UTC")
    assert deadline_sort_key(fall_day, "PT") == deadline_sort_key(fall_start, "UTC")


def test_cli_date_outputs_have_no_countdown_or_fabricated_instant(capsys):
    now = datetime(2028, 2, 28, tzinfo=timezone.utc)
    results = process_conference_deadlines([conference(["2028-02-29"])], now)
    output_table(results, now)
    rendered = capsys.readouterr().out
    assert "2028-02-29 (time unknown)" in rendered
    assert "00:00" not in rendered
    assert format_duration(date(2028, 2, 29), now) == "2028-02-29 (time unknown)"
    output_json(results)
    payload = json.loads(capsys.readouterr().out)[0]
    assert payload["deadline"] == "2028-02-29"
    assert payload["deadline_at"] is None
    assert payload["deadline_date"] == "2028-02-29"
    assert payload["precision"] == "date"
    assert payload["timezone"] == "Unknown"


def test_cli_precise_json_retains_exact_instant(capsys):
    now = datetime(2028, 2, 28, tzinfo=timezone.utc)
    results = process_conference_deadlines([
        conference(["2028-02-29 12:00:00", "TBD"], "UTC+8"),
    ], now)
    output_json(results)
    payload = json.loads(capsys.readouterr().out)[0]
    assert payload["deadline_at"] == "2028-02-29T04:00:00Z"
    assert payload["deadline_date"] is None
    assert payload["precision"] == "datetime"
