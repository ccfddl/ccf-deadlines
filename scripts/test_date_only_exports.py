"""Regression tests for date-only calendar, RSS and reminder exports."""

import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

import yaml
from icalendar import Calendar, Event

CLI_ROOT = Path(__file__).resolve().parents[1] / "extensions/cli"
sys.path.insert(0, str(CLI_ROOT))
from ccfddl.convert_to_ical import convert_to_ical, write_deadline_events_index
from ccfddl.convert_to_rss import convert_to_rss


def fixture(timeline, zone="Unknown"):
    return [{
        "title": "TEST", "description": "Test conference", "sub": "AI",
        "rank": {"ccf": "A"}, "dblp": "test",
        "confs": [{
            "year": 2028, "id": "test28", "link": "https://example.org/",
            "timeline": timeline, "timezone": zone,
            "date": "March 2028", "place": "Online",
        }],
    }]


class DateOnlyExportTests(unittest.TestCase):
    def export(self, data, lang="en"):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        source, ical, rss, index = (root / name for name in ("input.yml", "out.ics", "out.xml", "index.json"))
        source.write_text(yaml.safe_dump(data), encoding="utf-8")
        convert_to_ical([str(source)], str(ical), lang)
        convert_to_rss([str(source)], str(rss), lang)
        write_deadline_events_index(str(ical), str(index))
        return Calendar.from_ical(ical.read_bytes()), ET.parse(rss), json.loads(index.read_text()), ical.read_text()

    def test_all_deadline_fields_keep_calendar_precision(self):
        calendar, rss, index, raw = self.export(fixture([{
            key: "2028-02-29" for key in (
                "abstract_deadline", "deadline", "rebuttal_deadline", "decision_deadline"
            )
        }]))
        events = calendar.walk("VEVENT")
        self.assertEqual(len(events), 4)
        self.assertEqual(len(calendar.walk("VTIMEZONE")), 0)
        for event in events:
            self.assertIs(type(event.decoded("DTSTART")), date)
            self.assertEqual(event.decoded("DTSTART"), date(2028, 2, 29))
            self.assertEqual(event.decoded("DTEND"), date(2028, 3, 1))
            self.assertEqual(event["DTSTART"].params["VALUE"], "DATE")
            self.assertNotIn("TZID", event["DTSTART"].params)
        self.assertIn("DTSTART;VALUE=DATE:20280229", raw)
        for row in index:
            self.assertIsNone(row["deadline_at"])
            self.assertEqual(row["deadline_date"], "2028-02-29")
            self.assertEqual(row["precision"], "date")
            self.assertEqual(row["timezone"], "Unknown")
            self.assertTrue(row["all_day"])
        for item in rss.findall("./channel/item"):
            self.assertIsNone(item.find("pubDate"))
            self.assertIn("Deadline (Unknown): 2028-02-29", item.findtext("description"))
            self.assertIn("Time of day is unknown", item.findtext("description"))

    def test_known_zone_and_native_yaml_date_are_preserved(self):
        calendar, rss, index, _ = self.export(fixture([{"deadline": date(2028, 2, 29)}], "AoE"))
        self.assertIs(type(calendar.walk("VEVENT")[0].decoded("DTSTART")), date)
        self.assertEqual(index[0]["timezone"], "AoE")
        self.assertIsNone(index[0]["deadline_at"])
        self.assertIsNone(rss.find("./channel/item/pubDate"))

    def test_precise_timestamp_and_tbd_regression(self):
        calendar, rss, index, _ = self.export(fixture([
            {"deadline": "2028-02-29 12:00:00", "abstract_deadline": "TBD"},
            {"deadline": "TBD"},
        ], "UTC+8"))
        events = calendar.walk("VEVENT")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].decoded("DTSTART").astimezone(timezone.utc), datetime(2028, 2, 29, 4, tzinfo=timezone.utc))
        self.assertEqual(index[0]["deadline_at"], "2028-02-29T04:00:00Z")
        self.assertIsNone(index[0]["deadline_date"])
        self.assertEqual(index[0]["precision"], "datetime")
        self.assertEqual(index[0]["timezone"], "UTC+8")
        self.assertFalse(index[0]["all_day"])
        self.assertEqual(rss.findtext("./channel/item/pubDate"), "Tue, 29 Feb 2028 12:00:00 +0800")

    def test_invalid_dates_and_unknown_precise_values_are_not_exported(self):
        for value in ("2027-02-29", "2028-02-30", "2028-2-29", "2028-02-29 12:00:00", "TBD", None):
            with self.subTest(value=value):
                calendar, rss, index, _ = self.export(fixture([{"deadline": value}]))
                self.assertEqual(calendar.walk("VEVENT"), [])
                self.assertEqual(rss.findall("./channel/item"), [])
                self.assertEqual(index, [])

    def test_mixed_rounds_export_both_without_a_synthetic_midnight(self):
        calendar, rss, index, raw = self.export(fixture([
            {"deadline": "2028-02-29"},
            {"deadline": "TBD"},
            {"deadline": "2028-03-01 12:00:00"},
        ], "UTC"))
        self.assertEqual(len(calendar.walk("VEVENT")), 2)
        self.assertEqual([row["precision"] for row in index], ["date", "datetime"])
        self.assertIsNone(index[0]["deadline_at"])
        self.assertEqual(index[1]["deadline_at"], "2028-03-01T12:00:00Z")
        self.assertNotIn("20280229T000000", raw)
        self.assertEqual(len(rss.findall("./channel/item/pubDate")), 1)

    def test_chinese_feed_explains_unknown_clock(self):
        _, rss, index, _ = self.export(fixture([{"deadline": "2028-02-29"}]), "zh")
        self.assertIn("具体时刻未知", rss.findtext("./channel/item/description"))
        self.assertEqual(index[0]["title"], "TEST 2028 Deadline")

    def test_index_mixed_source_zones_use_internal_bounds_only(self):
        conferences = []
        for value, zone, conf_id in (
            ("2028-03-01", "UTC+8", "known-date"),
            ("2028-02-29 18:00:00", "UTC", "precise"),
            ("2028-03-01", "Unknown", "unknown-date"),
        ):
            conf = fixture([{"deadline": value}], zone)[0]
            conf["confs"][0]["id"] = conf_id
            conferences.append(conf)
        _, _, index, _ = self.export(conferences)
        self.assertEqual([row["id"] for row in index], ["unknown-date", "known-date", "precise"])
        self.assertTrue(all(row["deadline_at"] is None for row in index[:2]))
        self.assertTrue(all(row["deadline_date"] == "2028-03-01" for row in index[:2]))

    def test_last_iso_date_does_not_overflow_all_day_export(self):
        calendar, _, index, _ = self.export(fixture([{"deadline": "9999-12-31"}]))
        self.assertEqual(calendar.walk("VEVENT")[0].decoded("DTSTART"), date.max)
        self.assertEqual(index[0]["deadline_date"], "9999-12-31")

    def test_reminder_index_rejects_floating_or_unknown_zone_instants(self):
        for start, zone in (
            (datetime(2028, 2, 29, 12), "UTC"),
            (datetime(2028, 2, 29, 12, tzinfo=timezone.utc), "Unknown"),
        ):
            with self.subTest(start=start, zone=zone), tempfile.TemporaryDirectory() as directory:
                calendar = Calendar()
                event = Event()
                event.add("DTSTART", start)
                event.add("X-CCFDDL-TIMEZONE", zone)
                calendar.add_component(event)
                source = Path(directory) / "floating.ics"
                source.write_bytes(calendar.to_ical())
                with self.assertRaisesRegex(ValueError, "known timezone"):
                    write_deadline_events_index(str(source), str(Path(directory) / "index.json"))


if __name__ == "__main__":
    unittest.main()
