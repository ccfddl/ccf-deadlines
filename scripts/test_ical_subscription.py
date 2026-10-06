import tempfile
import unittest
import importlib.util
import json
from pathlib import Path

import yaml
from icalendar import Calendar

CONVERTER = Path(__file__).resolve().parents[1] / "extensions/cli/ccfddl/convert_to_ical.py"
SPEC = importlib.util.spec_from_file_location("convert_to_ical", CONVERTER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
convert_to_ical = MODULE.convert_to_ical
write_deadline_events_index = MODULE.write_deadline_events_index


class FavoriteCalendarTests(unittest.TestCase):
    def test_calendar_events_have_stable_edition_ids(self):
        conference = [{
            "title": "ICLR",
            "description": "International Conference on Learning Representations",
            "sub": "AI",
            "rank": {"ccf": "A", "core": "A*", "thcpl": "A"},
            "dblp": "iclr",
            "confs": [{
                "year": 2027,
                "id": "iclr27",
                "link": "https://iclr.cc/",
                "timeline": [{"abstract_deadline": "2026-09-19 23:59:59", "deadline": "2026-09-26 23:59:59"}],
                "timezone": "UTC+0",
                "date": "April 2027",
                "place": "USA",
            }],
        }]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "conference.yml"
            source.write_text(yaml.safe_dump(conference), encoding="utf-8")
            output = Path(directory) / "conference.ics"
            snapshots = []
            for _ in range(2):
                convert_to_ical([str(source)], str(output), "en")
                calendar = Calendar.from_ical(output.read_bytes())
                events = [item for item in calendar.walk() if item.name == "VEVENT"]
                self.assertEqual(len(events), 2)
                self.assertTrue(all(str(item["X-CCFDDL-ID"]) == "iclr27" for item in events))
                snapshots.append(sorted(str(item["UID"]) for item in events))
            self.assertEqual(snapshots[0], snapshots[1])

    def test_chinese_feed_keeps_event_titles_in_english(self):
        conference = [{
            "title": "ICLR",
            "description": "International Conference on Learning Representations",
            "sub": "AI",
            "rank": {"ccf": "A", "core": "A*", "thcpl": "A"},
            "dblp": "iclr",
            "confs": [{
                "year": 2027,
                "id": "iclr27",
                "link": "https://iclr.cc/",
                "timeline": [{
                    "abstract_deadline": "2026-09-19 23:59:59",
                    "deadline": "2026-09-26 23:59:59",
                    "rebuttal_deadline": "2026-10-01 23:59:59",
                    "decision_deadline": "2026-10-10 23:59:59",
                }],
                "timezone": "UTC+0",
                "date": "April 2027",
                "place": "USA",
            }],
        }]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "conference.yml"
            source.write_text(yaml.safe_dump(conference), encoding="utf-8")
            output = Path(directory) / "conference.ics"
            convert_to_ical([str(source)], str(output), "zh")
            calendar = Calendar.from_ical(output.read_bytes())
            summaries = {
                str(item["SUMMARY"])
                for item in calendar.walk()
                if item.name == "VEVENT"
            }
            self.assertEqual(summaries, {
                "ICLR 2027 Abstract Deadline",
                "ICLR 2027 Deadline",
                "ICLR 2027 Rebuttal Submission",
                "ICLR 2027 Final Decisions",
            })

    def test_email_index_reuses_calendar_instants_and_edition_ids(self):
        conference = [{
            "title": "ICLR", "description": "Conference", "sub": "AI",
            "rank": {"ccf": "A"}, "dblp": "iclr",
            "confs": [{
                "year": 2027, "id": "iclr27", "link": "https://iclr.cc/",
                "timeline": [{"deadline": "2026-10-05 09:00:00"}],
                "timezone": "UTC+8", "date": "2027", "place": "Singapore",
            }],
        }]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "conference.yml"
            source.write_text(yaml.safe_dump(conference), encoding="utf-8")
            calendar = Path(directory) / "deadlines_en.ics"
            index = Path(directory) / "deadline_events.json"
            convert_to_ical([str(source)], str(calendar), "en")
            write_deadline_events_index(str(calendar), str(index))
            events = json.loads(index.read_text(encoding="utf-8"))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["id"], "iclr27")
            self.assertEqual(events[0]["conference"], "ICLR 2027")
            self.assertEqual(events[0]["deadline_at"], "2026-10-05T01:00:00Z")
            self.assertEqual(events[0]["title"], "ICLR 2027 Deadline")


if __name__ == "__main__":
    unittest.main()
