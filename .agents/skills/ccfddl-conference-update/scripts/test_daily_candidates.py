"""Behavior checks for local triage; no web access or real check-ledger writes."""

import argparse
from contextlib import redirect_stdout
from datetime import date, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest

import yaml

import daily_candidates as helper


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / "conference/AI").mkdir(parents=True)
        self.today = date(2026, 10, 24)
        self.state = {"version": 1, "checks": {}, "remote": {"issues_until": "example-watermark"}}
        self.path = self.repo / "local/state.json"

    def write(self, editions):
        path = self.repo / "conference/AI/example.yml"
        path.write_text(yaml.safe_dump([{"title": "EXAMPLE", "confs": editions}]))

    def edition(self, year, **timeline):
        return {"id": f"example{year}", "year": year, "link": f"https://example.org/{year}",
                "date": f"December 10-12, {year}", "timeline": [timeline]}

    def rows(self, **kwargs):
        return helper.candidates(self.repo, self.today, kwargs.get("lead_days", 180), kwargs.get("filters", []))

    def scan(self, rows, force=False, limit=0, today=None):
        output = io.StringIO()
        args = argparse.Namespace(force=force, limit=limit, today=today or self.today)
        with redirect_stdout(output):
            helper.scan(args, rows, [], self.state)
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def record(self, row, outcome="unchanged", partial=False, today=None, round_name="all", source=None):
        args = argparse.Namespace(key=row["key"], outcome=outcome, today=today or self.today,
                                  next_check=None, source=source or row["url"], round=round_name,
                                  revision="fixture-v1", partial=partial)
        with redirect_stdout(io.StringIO()):
            helper.record(args, [row], self.state, self.path)
        return self.state["checks"][row["key"]]

    def test_overlapping_editions_and_new_deadline_fields(self):
        self.write([self.edition(2026, deadline="2026-04-01 23:59:59", decision_deadline="2026-11-01 12:00:00"),
                    self.edition(2027, deadline="2027-02-01 23:59:59", rebuttal_deadline="TBD")])
        rows, _ = self.rows()
        editions = [row for row in rows if row["scope"] == "edition"]
        self.assertEqual({row["year"] for row in editions}, {2026, 2027})
        self.assertEqual(editions[0]["reason"], "near milestone")
        self.assertEqual(editions[1]["reason"], "TBD / active edition")

    def test_quiet_cache_force_and_local_invalidation(self):
        self.write([self.edition(2027, deadline="2027-05-01 23:59:59")])
        rows, _ = self.rows()
        row = rows[0]
        self.record(row)
        self.assertEqual(self.scan([row])[0]["cached"], 1)
        self.assertEqual(self.scan([row], force=True)[0]["shown"], 1)
        self.write([self.edition(2027, deadline="2027-05-02 23:59:59")])
        changed, _ = self.rows()
        self.assertTrue(self.scan(changed)[1]["local_changed"])
        new_record = self.record(changed[0], source="https://example.org/revised-dates")
        self.assertEqual(len(new_record["sources"]), 1)
        self.assertEqual(new_record["sources"][0]["url"], "https://example.org/revised-dates")
        self.assertEqual(helper.load_state(self.path)["remote"], self.state["remote"])

    def test_near_milestone_overrides_old_backoff(self):
        self.write([self.edition(2027, deadline="2026-11-07 23:59:59")])
        row = self.rows()[0][0]
        self.record(row)
        self.state["checks"][row["key"]]["next_check"] = "2026-11-15"
        self.assertEqual(self.scan([row])[0]["cached"], 1)
        self.assertEqual(self.scan([row], today=self.today + timedelta(days=1))[0]["shown"], 1)

    def test_source_error_backoff_and_partial_round_records(self):
        self.write([self.edition(2027, deadline="2027-05-01 23:59:59")])
        row = self.rows()[0][0]
        first = self.record(row, outcome="source-error", partial=True, round_name="round 1")
        self.assertEqual(first["next_check"], str(self.today))
        second = self.record(row, outcome="source-error", round_name="round 2")
        self.assertEqual(len(second["sources"]), 2)
        self.assertEqual(second["next_check"], "2026-10-25")
        third = self.record(row, outcome="source-error", today=date(2026, 10, 25), round_name="round 2")
        self.assertEqual(third["sources"][-1]["next_check"], "2026-10-27")
        self.assertEqual(third["next_check"], "2026-10-25")  # Round 1 still needs its retry.
        self.assertEqual(third["outcome"], "source-error")

    def test_other_page_cannot_hide_earlier_retry(self):
        self.write([self.edition(2027, deadline="2027-05-01 23:59:59")])
        row = self.rows()[0][0]
        self.record(row, outcome="tbd", partial=True, source="https://example.org/cfp")
        result = self.record(row, outcome="unchanged", source="https://example.org/dates")
        self.assertEqual(result["next_check"], "2026-10-27")
        self.assertEqual(self.scan([row], today=date(2026, 10, 27))[0]["shown"], 1)
        self.record(row, outcome="source-error", source="https://example.org/cfp", round_name="round 1")
        result = self.record(row, outcome="unchanged", source="https://example.org/dates")
        self.assertEqual(result["next_check"], "2026-10-25")

    def test_gates_unknown_leads_and_explicit_force(self):
        self.write([self.edition(2027, deadline="2027-12-01 23:59:59"),
                    self.edition(2028, deadline="2028-12-01 23:59:59")])
        rows, _ = self.rows()
        next_row = [row for row in rows if row["scope"] == "next-edition"]
        self.assertEqual(self.scan(next_row)[0]["too_early"], 1)
        self.assertEqual(self.scan(next_row, force=True)[0]["shown"], 1)
        self.assertEqual(self.rows(filters=["NEWCONF"])[1], ["NEWCONF"])

    def test_local_revision_reopens_a_previously_checked_early_candidate(self):
        editions = [self.edition(2027, deadline="2027-12-01 23:59:59"),
                    self.edition(2028, deadline="2028-12-01 23:59:59")]
        self.write(editions)
        row = next(row for row in self.rows()[0] if row["scope"] == "next-edition")
        self.record(row, outcome="not-announced")
        self.assertEqual(self.scan([row])[0]["too_early"], 1)
        editions[-1]["link"] = "https://example.org/2028/new-official-home"
        self.write(editions)
        new_row = next(row for row in self.rows()[0] if row["scope"] == "next-edition")
        result = self.scan([new_row])
        self.assertEqual(result[0]["shown"], 1)
        self.assertTrue(result[1]["local_changed"])

    def test_bounded_batch_keeps_old_work_in_rotation(self):
        self.write([self.edition(2027, deadline="2026-11-01 23:59:59")])
        template = self.rows()[0][0]
        rows = [{**template, "key": f"urgent-{number}", "_priority": 0} for number in range(8)]
        rows.append({**template, "key": "old-unvisited", "_priority": 3})
        result = self.scan(rows, limit=4)
        self.assertEqual(result[0]["remaining"], 5)
        self.assertIn("old-unvisited", [row["key"] for row in result[1:]])


if __name__ == "__main__":
    unittest.main()
