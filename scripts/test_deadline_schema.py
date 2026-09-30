import unittest
from pathlib import Path

import jsonschema
import yaml
from validate import DEADLINE_FORMAT_CHECKER


class DeadlineSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = yaml.safe_load(Path(__file__).with_name("conference-yaml-schema.yml").read_text())

    def validate(self, deadline, timezone="Unknown", **extra):
        data = [{"title": "TEST", "description": "Test", "sub": "AI", "rank": {"ccf": "A"}, "dblp": "test",
                 "confs": [{"year": 2028, "id": "test28", "link": "https://example.org", "timezone": timezone,
                            "date": "TBD", "place": "TBD", "timeline": [{"deadline": deadline, **extra}]}]}]
        jsonschema.validate(data, self.schema, format_checker=DEADLINE_FORMAT_CHECKER)

    def test_precisions_and_source_known_zones(self):
        for timezone in ("Unknown", "AoE", "UTC+8", "PT"):
            self.validate("2028-02-29", timezone)
            self.validate("TBD", timezone)
        self.validate("2028-02-29 23:59:59", "AoE")

    def test_rejects_invalid_calendar_dates_and_unknown_precise_clocks(self):
        for value in ("2027-02-29", "2028-02-30", "2028-2-29", "2028-13-01", "2028-02-29 12:00:00"):
            with self.subTest(value=value), self.assertRaises(jsonschema.ValidationError):
                self.validate(value)
        for field in ("abstract_deadline", "rebuttal_deadline", "decision_deadline"):
            with self.subTest(field=field), self.assertRaises(jsonschema.ValidationError):
                self.validate("2028-02-29", **{field: "2028-02-29 12:00:00"})


if __name__ == "__main__":
    unittest.main()
