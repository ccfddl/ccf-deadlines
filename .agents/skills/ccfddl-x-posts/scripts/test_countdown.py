#!/usr/bin/env python3
"""Offline regression checks for date interpretation, selection, output, and state."""
import json
from pathlib import Path
import tempfile
import unittest
from datetime import timedelta
import yaml
import countdown as c

NOW = c.as_utc("2026-10-03T12:00:00Z")


def row(title="Example", sub="AI", rank="A", timeline=None, zone="AoE", identity="example27"):
    return {"title": title, "sub": sub, "rank": {"ccf": rank}, "confs": [{"year": 2027, "id": identity,
            "timezone": zone, "link": "https://example.org", "date": "July 2027", "timeline": timeline or [{"deadline": "2026-10-10 23:59:00"}]}]}


class DeadlineTests(unittest.TestCase):
    def test_aoe(self):
        self.assertEqual(c.iso(c.parse_deadline("2026-10-10 23:59:00", "AoE")), "2026-10-11T11:59:00Z")

    def test_offsets(self):
        self.assertEqual(c.iso(c.parse_deadline("2026-10-10 12:00:00", "UTC+05:30")), "2026-10-10T06:30:00Z")
        self.assertEqual(c.iso(c.parse_deadline("2026-10-10 12:00:00", "UTC-12")), "2026-10-11T00:00:00Z")
        self.assertEqual(c.iso(c.parse_deadline("2026-10-10 12:00:00Z", "TBD")), "2026-10-10T12:00:00Z")

    def test_dst(self):
        self.assertEqual(c.iso(c.parse_deadline("2026-07-10 12:00:00", "PT")), "2026-07-10T19:00:00Z")
        self.assertEqual(c.iso(c.parse_deadline("2026-12-10 12:00:00", "America/Los_Angeles")), "2026-12-10T20:00:00Z")
        for stamp in ("2026-11-01 01:30:00", "2026-03-08 02:30:00"):
            with self.assertRaises(ValueError):
                c.parse_deadline(stamp, "America/Los_Angeles")

    def test_reject_unknown_and_incomplete(self):
        for zone in (None, "PST?", "UTC+15", "UTC+14:30"):
            with self.assertRaises((ValueError, KeyError)):
                c.parse_deadline("2026-10-10 12:00:00", zone)
        with self.assertRaises(ValueError):
            c.parse_deadline("2026-10-10", "AoE")
        self.assertIsNone(c.parse_deadline("TBD", "AoE"))

    def test_countdown_boundaries(self):
        self.assertEqual(c.countdown(90000), "1 day left")
        self.assertEqual(c.countdown(3600), "1 hour left")
        self.assertEqual(c.countdown(7200), "2 hours left")
        self.assertEqual(c.countdown(172800), "2 days left")
        self.assertEqual(c.countdown(86400, True), "24h")
        self.assertEqual(c.countdown(86399, True), "23h")
        self.assertEqual(c.countdown(3599, True), "59m")
        self.assertEqual(c.countdown(1, True), "<1m")
        self.assertEqual(c.countdown(172800, True), "2d")
        with self.assertRaises(ValueError):
            c.countdown(0)

    def test_weighted_length(self):
        self.assertEqual(c.weighted_length("abc"), 3)
        self.assertEqual(c.weighted_length("会议"), 4)
        self.assertEqual(c.weighted_length(c.LINK), 23)
        self.assertEqual(c.weighted_length("e\u0301"), 1)
        with self.assertRaises(ValueError):
            c.weighted_length("https://evil.example")


class SelectionTests(unittest.TestCase):
    def test_category_and_explicit_include(self):
        rows = [(row(), "conference/AI/example.yml"), (row("MLSys", "MX", "N"), "conference/MX/mlsys.yml"), (row("B", "DB", "B"), "conference/DB/b.yml")]
        cats, issues = c.select(rows, {"include_paths": ["conference/MX/mlsys.yml"]}, NOW)
        self.assertEqual(len(cats["AI"]), 1)
        self.assertEqual([e["conference"] for e in cats["Data Systems"]], ["MLSys"])

    def test_submission_only(self):
        r = row(timeline=[{"deadline": "TBD", "rebuttal_deadline": "2026-10-05 12:00:00", "decision_deadline": "2026-10-06 12:00:00"}])
        r["confs"][0]["date"] = "2026-10-07 12:00:00"
        cats, _ = c.select([(r, "conference/AI/x.yml")], {}, NOW)
        self.assertEqual(cats["AI"], [])

    def test_multi_round(self):
        r = row(timeline=[{"deadline": "2026-10-01 12:00:00"}, {"abstract_deadline": "2026-10-10 12:00:00", "deadline": "2026-10-17 12:00:00"}, {"deadline": "2026-12-03 12:00:00"}])
        cats, _ = c.select([(r, "conference/AI/x.yml")], {}, NOW)
        self.assertEqual([e["round_label"] for e in cats["AI"]], ["R2", "R3"])
        self.assertEqual(cats["AI"][0]["stage"], "abstract")

    def test_abstract_closed(self):
        r = row(timeline=[{"abstract_deadline": "2026-10-01 12:00:00", "deadline": "2026-10-10 12:00:00"}])
        cats, _ = c.select([(r, "conference/AI/x.yml")], {}, NOW)
        self.assertTrue(cats["AI"][0]["abstract_closed"])
        text, _ = c.tweet("AI", cats["AI"], NOW, 3)
        self.assertIn("abstract closed", text)

    def test_title_collisions_not_merged(self):
        rows = [(row("SEC"), "conference/SC/sec.yml"), (row("SEC"), "conference/SE/sec.yml")]
        cats, _ = c.select(rows, {}, NOW)
        self.assertEqual(len(cats["AI"]), 2)

    def test_quarantine(self):
        cats, issues = c.select([(row(), "conference/AI/x.yml")], {"quarantine_events": [{"source_path": "conference/AI/x.yml", "id": "example27", "reason": "clock conflict"}]}, NOW)
        self.assertEqual(cats["AI"], [])
        self.assertEqual(issues[0]["reason"], "clock conflict")

    def test_skip_expired_far_tbd_and_unclear(self):
        r = row(timeline=[{"deadline": "TBD"}, {"deadline": "2025-01-01 12:00:00"}, {"deadline": "2030-01-01 12:00:00"}, {"deadline": "2026-10-12 12:00:00", "comment": "Rebuttal deadline"}])
        cats, issues = c.select([(r, "conference/AI/x.yml")], {}, NOW)
        self.assertEqual(cats["AI"], [])
        self.assertEqual(len(issues), 1)

    def test_default_tweet_has_at_most_three_rows(self):
        rows = [(row("ConferenceVeryLong" + str(i)), f"conference/AI/x{i}.yml") for i in range(10)]
        cats, _ = c.select(rows, {}, NOW)
        text, chosen = c.tweet("AI", cats["AI"], NOW, 3)
        self.assertLessEqual(len(chosen), 3)
        self.assertTrue(text.endswith(c.LINK))

    def test_exact_user_plain_text_format(self):
        timelines = [{"deadline": "TBD"} for _ in range(3)] + [{"abstract_deadline": "2026-10-10 23:59:00", "deadline": "2026-10-17 23:59:00"}]
        cats, _ = c.select([(row("SIGMOD", sub="DB", timeline=timelines), "conference/DB/sigmod.yml")], {}, NOW)
        text, _ = c.tweet("Data Systems", cats["Data Systems"], NOW, 3)
        self.assertEqual(text, "CCFDDL deadline reminders:\nSIGMOD'27 (abstract, round 4) · 7 days left · 2026/10/10 23:59 (AoE)\nsee details: https://ccfddl.com")
        self.assertNotIn("**", text)
        self.assertNotIn("Data Systems", text)

    def test_explicit_multiple_stages(self):
        timeline = [{"abstract_deadline": "2026-10-10 23:59:00", "deadline": "2026-10-17 23:59:00"}]
        rows = [(row("CVPR", timeline=timeline), "conference/AI/cvpr.yml")]
        nearest, _ = c.select(rows, {}, NOW)
        self.assertEqual(len(nearest["AI"]), 1)
        all_stages, _ = c.select(rows, {"stage_selection": "all_future"}, NOW)
        self.assertEqual([e["stage"] for e in all_stages["AI"]], ["abstract", "paper"])
        text, chosen = c.tweet("AI", all_stages["AI"], NOW, 3)
        self.assertEqual(len(chosen), 2)
        self.assertIn("CVPR'27 (abstract)", text)
        self.assertIn("CVPR'27 (paper)", text)

    def test_unknown_selection_mode_rejected(self):
        with self.assertRaises(ValueError):
            c.select([], {"stage_selection": "guess"}, NOW)

    def test_long_text_is_advisory_not_a_hard_cap(self):
        rows = [(row("LongConference" * 10), "conference/AI/long.yml")]
        cats, _ = c.select(rows, {}, NOW)
        text, chosen = c.tweet("Data Systems", cats["AI"] * 3, NOW, 3)
        self.assertGreater(c.weighted_length(text), 280)
        self.assertEqual(len(chosen), 3)


class BuildAndLedgerTests(unittest.TestCase):
    def make_snapshot(self, base, complete=True, age=0):
        raw = yaml.safe_dump([row()])
        obj = {"repository": "https://github.com/ccfddl/ccf-deadlines", "commit": "a" * 40,
               "fetched_at_utc": c.iso(NOW - timedelta(minutes=age)), "complete_catalog": complete,
               "files": [{"path": "conference/AI/x.yml", "content": raw, "sha256": c.sha(raw)}]}
        path = Path(base) / "snapshot.json"
        path.write_text(json.dumps(obj))
        return path

    def test_build(self):
        with tempfile.TemporaryDirectory() as temp:
            snapshot = self.make_snapshot(temp)
            cfg = Path(temp) / "config.json"
            cfg.write_text('{"editorial_confirmed":true}')
            manifest = c.build(snapshot, cfg, NOW, Path(temp) / "output", False)
            self.assertEqual(len(manifest["digests"]), 1)
            from PIL import Image
            with Image.open(manifest["digests"][0]["image"]) as image:
                self.assertEqual(image.size, (1600, 652))
                self.assertEqual(image.getpixel((0, 0)), (242, 242, 242))

    def test_stale_and_partial_fail_closed(self):
        for complete, age in ((False, 0), (True, 16)):
            with tempfile.TemporaryDirectory() as temp:
                snapshot = self.make_snapshot(temp, complete, age)
                cfg = Path(temp) / "config.json"
                cfg.write_text('{"editorial_confirmed":true}')
                with self.assertRaises(ValueError):
                    c.build(snapshot, cfg, NOW, Path(temp) / "output", False)

    def test_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            snapshot = self.make_snapshot(temp)
            obj = json.loads(snapshot.read_text())
            obj["files"][0]["content"] += "\n# altered"
            snapshot.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                c.load_snapshot(snapshot)

    def test_ledger_uncertain_and_confirmed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ledger.json"
            args = (path, "reserve", "2026-10-03", "AI", "a" * 64)
            self.assertEqual(c.ledger(*args)["state"], "pending")
            with self.assertRaises(ValueError):
                c.ledger(*args)
            with self.assertRaises(ValueError):
                c.ledger(path, "confirm", "2026-10-03", "AI", post_id="1", post_url="https://x.com/wrong/status/1")
            self.assertEqual(c.ledger(path, "confirm", "2026-10-03", "AI", post_id="1", post_url="https://x.com/ccfddl/status/1")["state"], "published")
            with self.assertRaises(ValueError):
                c.ledger(*args)
            self.assertIsNone(c.ledger(path, "check", "2026-10-03", "Data Systems"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
