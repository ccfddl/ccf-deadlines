import tempfile
import unittest
import importlib.util
from pathlib import Path

import yaml
from icalendar import Calendar

CONVERTER = Path(__file__).resolve().parents[1] / "extensions/cli/ccfddl/convert_to_ical.py"
SPEC = importlib.util.spec_from_file_location("convert_to_ical", CONVERTER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
convert_to_ical = MODULE.convert_to_ical


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
                "timeline": [{"abstract_deadline": "2026-09-19 23:59:00", "deadline": "2026-09-26 23:59:00"}],
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


if __name__ == "__main__":
    unittest.main()
