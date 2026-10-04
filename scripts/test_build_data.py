import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from build_data import (
    acceptance_bucket,
    resolve_acceptance_keys,
    split_conferences,
    write_loading_data,
)


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

    def test_keeps_upcoming_opening_after_submission_dates_have_passed(self):
        older = edition(2026, "2025-10-01 23:59:59")
        older["opening"] = "2026-12-01 08:00:00"
        initial, archive = split_conferences([
            {"title": "Example", "confs": [older, edition(2027)]},
        ], date(2026, 10, 4))
        self.assertEqual([entry["year"] for entry in initial[0]["confs"]], [2026, 2027])
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

    def test_bucket_is_stable_for_ascii_and_unicode(self):
        self.assertEqual(acceptance_bucket("ICLR"), 11)
        self.assertEqual(acceptance_bucket("VLDB"), 9)
        self.assertEqual(acceptance_bucket("中文"), 5)


class AcceptanceIdentityTests(unittest.TestCase):
    def test_same_title_conferences_retain_distinct_source_keys_and_years(self):
        conferences = [{"conference_key": key, "title": title} for key, title in [
            ("DS/sec", "SEC"), ("SC/sec", "SEC"),
            ("SC/fse", "FSE"), ("SE/fse", "FSE"),
        ]]
        acceptances = [{**conference, "accept_rates": [{"year": 2026, "accepted": count}]}
                       for conference, count in zip(conferences, [18, 39, 55, 211])]
        resolved = resolve_acceptance_keys(conferences, acceptances)
        self.assertEqual([item["conference_key"] for item in resolved],
                         ["DS/sec", "SC/sec", "SC/fse", "SE/fse"])
        self.assertEqual([item["accept_rates"][0]["accepted"] for item in resolved], [18, 39, 55, 211])

    def test_unambiguous_eusipco_legacy_path_preserves_every_historical_row(self):
        original = {"conference_key": "DB/eusipco", "title": "EUSIPCO", "accept_rates": [
            {"year": 2017, "accepted": 461, "submitted": 730},
            {"year": 2018, "accepted": 409, "submitted": 709},
            {"year": 2020, "accepted": 499, "submitted": 829},
        ]}
        resolved = resolve_acceptance_keys(
            [{"conference_key": "CG/eusipco", "title": "EUSIPCO"}], [original],
        )[0]
        self.assertEqual(resolved["conference_key"], "CG/eusipco")
        self.assertEqual(resolved["accept_rates"], original["accept_rates"])
        self.assertEqual(original["conference_key"], "DB/eusipco")

    def test_exact_key_survives_title_rename_and_uses_current_title_bucket(self):
        resolved = resolve_acceptance_keys(
            [{"conference_key": "AI/nips", "title": "NeurIPS"}],
            [{"conference_key": "AI/nips", "title": "NIPS", "accept_rates": []}],
        )
        self.assertEqual(resolved[0]["conference_key"], "AI/nips")
        self.assertEqual(resolved[0]["title"], "NeurIPS")
        with TemporaryDirectory() as directory:
            output = Path(directory)
            write_loading_data([], resolved, output)
            bucket = output / "parts" / f"acceptance-{acceptance_bucket('NeurIPS'):02}.json"
            self.assertEqual(json.loads(bucket.read_text()), resolved)

    def test_ambiguous_or_unknown_legacy_paths_fail_closed(self):
        conferences = [{"conference_key": "SC/fse", "title": "FSE"},
                       {"conference_key": "SE/fse", "title": "FSE"}]
        for title in ["FSE", "Unknown"]:
            with self.assertRaisesRegex(ValueError, "Unknown or ambiguous"):
                resolve_acceptance_keys(conferences, [{"conference_key": "old/fse", "title": title}])

    def test_duplicate_identities_are_rejected_before_rendering(self):
        conference = {"conference_key": "AI/iclr", "title": "ICLR"}
        with self.assertRaisesRegex(ValueError, "Duplicate conference"):
            resolve_acceptance_keys([conference, conference], [])
        with self.assertRaisesRegex(ValueError, "Duplicate acceptance"):
            resolve_acceptance_keys([conference], [conference, conference])

    def test_merge_derives_distinct_keys_without_changing_source_files(self):
        script = Path(__file__).with_name("merge.py")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            contents = "- title: SEC\n  accept_rates: []\n"
            for category in ["DS", "SC"]:
                (root / category).mkdir()
                (root / category / "sec.yml").write_text(contents)
            result = subprocess.run(
                [sys.executable, str(script), str(root), "--include-conference-key"],
                capture_output=True, text=True, check=True,
            )
            data = yaml.safe_load(result.stdout)
            self.assertEqual([item["conference_key"] for item in data], ["DS/sec", "SC/sec"])
            for category in ["DS", "SC"]:
                self.assertEqual((root / category / "sec.yml").read_text(), contents)

    def test_identity_survives_initial_and_history_split(self):
        conference = {"conference_key": "SC/sec", "title": "SEC", "confs": [
            edition(2021, "2020-01-01 23:59:00"), edition(2026, "2025-01-01 23:59:00"),
            edition(2027, "2026-12-01 23:59:00"),
        ]}
        initial, history = split_conferences([conference], date(2026, 9, 30))
        self.assertEqual(initial[0]["conference_key"], "SC/sec")
        self.assertEqual(history[0]["conference_key"], "SC/sec")


if __name__ == "__main__":
    unittest.main()
