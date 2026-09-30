import unittest
from datetime import date

from build_data import acceptance_bucket, split_conferences


def edition(year, deadline="TBD"):
    return {"year": year, "id": f"conf{year}", "timeline": [{"deadline": deadline}]}


class LoadingDataTests(unittest.TestCase):
    def test_preserves_all_editions_and_source_structure(self):
        conference = {"title": "Example", "sub": "AI", "confs": [
            edition(2024, "2023-10-01 23:59:59"),
            edition(2025, "2024-10-01 23:59:59"),
            edition(2026, "2025-10-01 23:59:59"), edition(2027),
        ]}
        initial, archive = split_conferences([conference], date(2026, 9, 27))
        self.assertEqual([item["year"] for item in initial[0]["confs"]], [2026, 2027])
        self.assertEqual([item["year"] for item in archive[0]["confs"]], [2024, 2025])
        self.assertEqual(sorted(initial[0]["confs"] + archive[0]["confs"], key=lambda item: item["year"]), conference["confs"])
        self.assertEqual(len(conference["confs"]), 4)

    def test_keeps_upcoming_decisions_from_an_older_edition(self):
        older = edition(2024, "2023-10-01 23:59:59")
        older["timeline"][0]["decision_deadline"] = "2026-12-01 23:59:59"
        initial, archive = split_conferences([
            {"title": "Example", "confs": [older, edition(2027)]},
        ], date(2026, 9, 27))
        self.assertEqual(len(initial[0]["confs"]), 2)
        self.assertEqual(archive, [])

    def test_keeps_previous_edition_across_year_gaps_for_estimates(self):
        initial, archive = split_conferences([
            {"title": "Example", "confs": [edition(2021), edition(2024), edition(2027)]},
        ], date(2026, 9, 27))
        self.assertEqual([item["year"] for item in initial[0]["confs"]], [2024, 2027])
        self.assertEqual(archive[0]["confs"][0]["year"], 2021)

    def test_keeps_only_latest_finished_edition_when_no_dates_are_upcoming(self):
        initial, archive = split_conferences([
            {"title": "Example", "confs": [edition(2020), edition(2021), edition(2022)]},
        ], date(2026, 9, 27))
        self.assertEqual([item["year"] for item in initial[0]["confs"]], [2022])
        self.assertEqual(len(archive[0]["confs"]), 2)

    def test_keeps_tbd_current_edition_even_if_next_year_is_already_announced(self):
        initial, _ = split_conferences([
            {"title": "Example", "confs": [edition(2026), edition(2027, "2026-12-01 23:59:59")]},
        ], date(2026, 9, 27))
        self.assertEqual([item["year"] for item in initial[0]["confs"]], [2026, 2027])

    def test_date_only_rounds_are_preserved_without_tbd_estimation(self):
        older = edition(2024, "2023-10-01")
        older["timeline"].append({"deadline": "2026-09-26", "decision_deadline": "2026-10-01"})
        current = edition(2027, "2026-10-15")
        initial, archive = split_conferences([
            {"title": "Example", "confs": [older, edition(2026, "2025-01-01"), current]},
        ], date(2026, 9, 27))
        self.assertEqual([item["year"] for item in initial[0]["confs"]], [2024, 2027])
        self.assertEqual(initial[0]["confs"][0]["timeline"][1]["deadline"], "2026-09-26")
        self.assertEqual(archive[0]["confs"][0]["year"], 2026)

    def test_bucket_is_stable_for_ascii_and_unicode(self):
        self.assertEqual(acceptance_bucket("ICLR"), 11)
        self.assertEqual(acceptance_bucket("VLDB"), 9)
        self.assertEqual(acceptance_bucket("中文"), 5)


if __name__ == "__main__":
    unittest.main()
