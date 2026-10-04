import unittest

from conference_dates import conference_opening, with_conference_openings


class ConferenceOpeningTests(unittest.TestCase):
    def test_first_day_of_ranges_abbreviations_and_day_first_dates(self):
        for raw, expected in [
            ("August 17-22, 2027", "2027-08-17"),
            ("February 25 - March 4, 2025", "2025-02-25"),
            ("Nov. 25-27, 2021", "2021-11-25"),
            ("29 June - 2 July, 2026", "2026-06-29"),
            ("2027-04-26 to 2027-04-30", "2027-04-26"),
            ("December 29, 2026 - January 2, 2027", "2026-12-29"),
            ("August 7-13 and August 15-17, 2027", "2027-08-07"),
            ("December 2-7 (San Diego), November 30-December 5 (Mexico City), 2025", "2025-11-30"),
            ("June 14", "2027-06-14"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(conference_opening({"year": 2027, "date": raw}), expected + " 08:00:00")

    def test_missing_days_and_invalid_dates_are_not_invented(self):
        for raw in [None, "", "TBD", "Extended", "July 2027", "May 2027 (exact dates TBD)", "March-April, 2025", "February 30, 2027"]:
            with self.subTest(raw=raw):
                self.assertIsNone(conference_opening({"year": 2027, "date": raw}))

    def test_generated_data_preserves_the_edition_timezone_and_submission_dates(self):
        original = [{"title": "Example", "confs": [
            {"year": 2027, "date": "April 26-30, 2027", "timezone": "AoE", "timeline": [{"deadline": "TBD"}]},
            {"year": 2028, "date": "TBD", "timezone": "PT", "timeline": []},
        ]}]
        result = with_conference_openings(original)
        self.assertEqual(result[0]["confs"][0]["opening"], "2027-04-26 08:00:00")
        self.assertEqual(result[0]["confs"][0]["timezone"], "AoE")
        self.assertEqual(result[0]["confs"][0]["timeline"], [{"deadline": "TBD"}])
        self.assertIsNone(result[0]["confs"][1]["opening"])
        self.assertNotIn("opening", original[0]["confs"][0])


if __name__ == "__main__":
    unittest.main()
