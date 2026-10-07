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
            "timezone": zone, "link": "https://example.org", "date": "July 2027", "timeline": timeline or [{"deadline": "2026-10-10 23:59:59"}]}]}


class DeadlineTests(unittest.TestCase):
    def test_aoe(self):
        self.assertEqual(c.iso(c.parse_deadline("2026-10-10 23:59:59", "AoE")), "2026-10-11T11:59:59Z")

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

    def test_detail_url_and_whole_path_weight(self):
        event = {"source_subject": "DB", "conference": "IEEE ICDE", "year": 2027, "id": "icde27"}
        url = c.detail_url(event)
        self.assertEqual(url, "https://ccfddl.com/venues/db/ieee-icde-2027/")
        self.assertEqual(c.weighted_length(url), 23)
        event.update(source_subject="MX", conference="!!!", id="MLSys27")
        self.assertEqual(c.detail_url(event), "https://ccfddl.com/venues/mx/mlsys27-2027/")
        for bad in ("https://ccfddl.com.evil.org/venues/ai/aaai-2027/",
                    "https://ccfddl.com/venues/ai/aaai-2027/?private=1",
                    "https://evil.org/venues/ai/aaai-2027/"):
            with self.assertRaises(ValueError):
                c.weighted_length(bad)

    def test_weighted_length(self):
        self.assertEqual(c.weighted_length("abc"), 3)
        self.assertEqual(c.weighted_length("会议"), 4)
        self.assertEqual(c.weighted_length(c.LINK), 23)
        self.assertEqual(c.weighted_length(c.DISPLAY_LINK), 23)
        self.assertEqual(c.weighted_length("see details: ccfddl.com"), len("see details: ") + 23)
        self.assertEqual(c.weighted_length(c.LINK + " " + c.DISPLAY_LINK), 47)
        self.assertEqual(c.weighted_length("ccfddl.com\nhttps://ccfddl.com/venues/ai/aaai-2027/"), 47)
        self.assertEqual(c.weighted_length(c.HASHTAGS), 27)
        self.assertEqual(c.weighted_length("e\u0301"), 1)
        with self.assertRaises(ValueError):
            c.weighted_length("https://evil.example")


class SelectionTests(unittest.TestCase):
    def test_category_and_explicit_include(self):
        rows = [(row(), "conference/AI/example.yml"), (row("MLSys", "MX", "N"), "conference/MX/mlsys.yml"), (row("B", "DB", "B"), "conference/DB/b.yml")]
        cats, issues = c.select(rows, {"ccf_ranks": ["A"], "include_paths": ["conference/MX/mlsys.yml"]}, NOW)
        self.assertEqual(len(cats["AI"]), 1)
        self.assertEqual([e["conference"] for e in cats["Data Systems"]], ["MLSys"])

    def test_default_scope_includes_ccf_a_and_b_not_c(self):
        rows = [(row("A", rank="A"), "conference/AI/a.yml"), (row("B", rank="B"), "conference/AI/b.yml"), (row("C", rank="C"), "conference/AI/c.yml")]
        cats, _ = c.select(rows, {}, NOW)
        self.assertEqual({e["conference"] for e in cats["AI"]}, {"A", "B"})

    def test_commitment_is_not_a_submission_or_extra_round(self):
        timelines = [{"deadline": "2026-10-12 23:59:59", "comment": "ARR Submission"}, {"deadline": "2026-12-23 23:59:59", "comment": "Conference commitment after ARR meta-reviews; reviewed papers only"}]
        rows = [(row("COLING", timeline=timelines), "conference/AI/coling.yml")]
        cats, issues = c.select(rows, {}, NOW)
        self.assertEqual(len(cats["AI"]), 1)
        self.assertEqual(cats["AI"][0]["round_label"], "")
        self.assertEqual(len(issues), 1)
        later, _ = c.select(rows, {}, c.as_utc("2026-12-01T12:00:00Z"))
        self.assertEqual(later["AI"], [])

    def test_card_event_labels(self):
        cats, _ = c.select([(row("VLDB", timeline=[{"abstract_deadline": "2026-10-10 23:59:59", "deadline": "2026-10-17 23:59:59"}]), "conference/DB/vldb.yml")], {"stage_selection": "all_future"}, NOW)
        self.assertEqual(c.card_event_title(cats["AI"][0]), "VLDB 2027 Abstract Deadline")
        self.assertEqual(c.card_event_title(cats["AI"][1]), "VLDB 2027 Deadline")
        cats["AI"][1]["abstract_closed"] = True
        self.assertEqual(c.card_event_title(cats["AI"][1]), "VLDB 2027 Deadline")

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
        self.assertNotIn("abstract closed", text)
        self.assertNotIn("abstract closed", c.card_event_title(cats["AI"][0]))

    def test_title_collisions_not_merged(self):
        rows = [(row("SEC"), "conference/SC/sec.yml"), (row("SEC"), "conference/SE/sec.yml")]
        cats, _ = c.select(rows, {}, NOW)
        self.assertEqual(len(cats["AI"]), 2)

    def test_repository_deadline_ignores_legacy_official_override(self):
        r = row("EDBT", sub="DB", timeline=[{"deadline": "2026-10-07 23:59:59"}], identity="edbt27")
        cfg = {"official_deadline_overrides": [{"source_path": "conference/DB/edbt.yml",
               "id": "edbt27", "timeline_index": 1, "field": "deadline",
               "replacement_value": "2026-10-07 17:00:00", "replacement_timezone": "PT"}]}
        cats, issues = c.select([(r, "conference/DB/edbt.yml")], cfg, NOW)
        event = cats["Data Systems"][0]
        self.assertEqual(event["deadline_utc"], "2026-10-08T11:59:59Z")
        self.assertEqual(event["timezone_source"], "AoE")
        self.assertEqual(event["deadline_source"], "2026-10-07 23:59:59")
        self.assertNotIn("official_deadline_override", event)
        self.assertEqual(issues, [])
        r["confs"][0]["timeline"][0]["deadline"] = "2026-10-09 23:59:59"
        changed, issues = c.select([(r, "conference/DB/edbt.yml")], cfg, NOW)
        self.assertEqual(changed["Data Systems"][0]["deadline_utc"], "2026-10-10T11:59:59Z")
        self.assertEqual(issues, [])

    def test_repository_mlsys_ignores_legacy_external_quarantine(self):
        r = row("MLSys", sub="MX", rank="N", identity="mlsys27",
                timeline=[{"deadline": "2026-10-30 12:00:00"}], zone="PT")
        cfg = {"include_paths": ["conference/MX/mlsys.yml"],
               "quarantine_events": [{"source_path": "conference/MX/mlsys.yml",
                                     "id": "mlsys27", "reason": "external clock conflict"}]}
        cats, issues = c.select([(r, "conference/MX/mlsys.yml")], cfg, NOW)
        self.assertEqual(len(cats["Data Systems"]), 1)
        self.assertEqual(cats["Data Systems"][0]["deadline_source"], "2026-10-30 12:00:00")
        self.assertEqual(cats["Data Systems"][0]["deadline_utc"], "2026-10-30T19:00:00Z")
        self.assertEqual(issues, [])

    def test_skip_expired_far_tbd_and_unclear(self):
        r = row(timeline=[{"deadline": "TBD"}, {"deadline": "2025-01-01 12:00:00"}, {"deadline": "2030-01-01 12:00:00"}, {"deadline": "2026-10-12 12:00:00", "comment": "Rebuttal deadline"}])
        cats, issues = c.select([(r, "conference/AI/x.yml")], {}, NOW)
        self.assertEqual(cats["AI"], [])
        self.assertEqual(len(issues), 1)

    def test_overflow_preserves_a_and_b_representatives(self):
        items = [{"conference": f"B{i}", "rank_ccf": "B"} for i in range(8)] + [{"conference": "A", "rank_ccf": "A"}]
        selected = c.choose_digest_events(items, 6)
        self.assertEqual(len(selected), 6)
        self.assertEqual({e["rank_ccf"] for e in selected}, {"A", "B"})
        with self.assertRaises(ValueError):
            c.choose_digest_events(items, 1)

    def test_all_six_fit_without_rank_displacement(self):
        items = [{"conference": str(i), "rank_ccf": "A" if i in (3, 5) else "B"} for i in range(6)]
        self.assertEqual(c.choose_digest_events(items, 6), items)

    def test_default_tweet_has_at_most_three_rows(self):
        rows = [(row("ConferenceVeryLong" + str(i)), f"conference/AI/x{i}.yml") for i in range(10)]
        cats, _ = c.select(rows, {}, NOW)
        text, chosen = c.tweet("AI", cats["AI"], NOW, 3)
        self.assertLessEqual(len(chosen), 3)
        self.assertTrue(text.endswith("see details: " + c.detail_url(chosen[0]) + "\n#ccfddl #conf_deadline #蓝v"))

    def test_exact_user_plain_text_format(self):
        timelines = [{"deadline": "TBD"} for _ in range(3)] + [{"abstract_deadline": "2026-10-10 23:59:59", "deadline": "2026-10-17 23:59:59"}]
        cats, _ = c.select([(row("SIGMOD", sub="DB", timeline=timelines), "conference/DB/sigmod.yml")], {}, NOW)
        text, _ = c.tweet("Data Systems", cats["Data Systems"], NOW, 3)
        self.assertEqual(text, "CCFDDL daily reminders (Data Systems) · 2026/10/03\n\nSIGMOD'27 (abstract, round 4) · 7 days\n\nsee details: https://ccfddl.com/venues/db/sigmod-2027/\n#ccfddl #conf_deadline #蓝v")
        self.assertNotIn("**", text)
        self.assertFalse(text.splitlines()[0].endswith(":"))

    def test_tweet_day_countdown_omits_left_only_in_text(self):
        cats, _ = c.select([(row(), "conference/AI/x.yml")], {}, NOW)
        event = cats["AI"][0]
        for seconds, expected in [(38 * 86400, "38 days"), (90000, "1 day"),
                                  (86400, "24 hours left"), (3600, "1 hour left"),
                                  (60, "1 min left"), (1, "<1 min left")]:
            with self.subTest(seconds=seconds):
                event["seconds_left"] = seconds
                text, _ = c.tweet("AI", [event], NOW, 3)
                self.assertEqual(text.splitlines()[2], f"Example'27 (paper) · {expected}")
                self.assertTrue(c.countdown(seconds).endswith(" left"))

    def test_tweet_header_uses_los_angeles_publication_date(self):
        cats, _ = c.select([(row(), "conference/AI/x.yml")], {}, NOW)
        cases = [("2026-10-07T06:59:59Z", "2026/10/06"),
                 ("2026-10-07T07:00:00Z", "2026/10/07"),
                 ("2026-12-07T07:59:59Z", "2026/12/06"),
                 ("2026-12-07T08:00:00Z", "2026/12/07")]
        for category in ("AI", "Data Systems"):
            for stamp, date in cases:
                with self.subTest(category=category, stamp=stamp):
                    text, _ = c.tweet(category, cats["AI"], c.as_utc(stamp), 3)
                    self.assertEqual(text.splitlines()[0],
                                     f"CCFDDL daily reminders ({category}) · {date}")
                    # The Chinese character in the hashtag has weight two; other non-URL characters weigh one.
                    self.assertEqual(c.weighted_length(text), len(text) - len(c.detail_url(cats["AI"][0])) + 23 + 1)

    def test_explicit_multiple_stages(self):
        timeline = [{"abstract_deadline": "2026-10-10 23:59:59", "deadline": "2026-10-17 23:59:59"}]
        rows = [(row("CVPR", timeline=timeline), "conference/AI/cvpr.yml")]
        nearest, _ = c.select(rows, {}, NOW)
        self.assertEqual(len(nearest["AI"]), 1)
        all_stages, _ = c.select(rows, {"stage_selection": "all_future"}, NOW)
        self.assertEqual([e["stage"] for e in all_stages["AI"]], ["abstract", "paper"])
        text, chosen = c.tweet("AI", all_stages["AI"], NOW, 3)
        self.assertEqual(len(chosen), 2)
        self.assertIn("CVPR'27 (abstract)", text)
        self.assertIn("CVPR'27 (paper)", text)

    def test_ai_category_header_without_colon(self):
        cats, _ = c.select([(row(), "conference/AI/x.yml")], {}, NOW)
        text, _ = c.tweet("AI", cats["AI"], NOW, 3)
        self.assertEqual(text.splitlines()[0], "CCFDDL daily reminders (AI) · 2026/10/03")

    def test_abstract_display_ignores_registration_alias(self):
        cats, _ = c.select([(row("CVPR", timeline=[{"abstract_deadline": "2026-10-10 23:59:59", "deadline": "2026-10-17 23:59:59"}]), "conference/AI/cvpr.yml")], {}, NOW)
        event = cats["AI"][0]
        event["stage_label"] = "reg"
        self.assertEqual(c.display_stage(event), "abstract")
        text, _ = c.tweet("AI", [event], NOW, 3)
        self.assertIn("CVPR'27 (abstract)", text)
        self.assertNotIn("(reg)", text)
        event["stage_label"] = "registration"
        self.assertEqual(c.display_stage(event), "abstract")

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

    def test_category_limits(self):
        self.assertEqual(c.digest_limit({}, "AI"), 6)
        self.assertEqual(c.digest_limit({}, "Data Systems"), 6)
        for cfg, category in [({"max_items_by_category": {"AI": 7}}, "AI"),
                              ({"max_items_by_category": {"Data Systems": 7}}, "Data Systems"),
                              ({"max_items_by_category": {"Data Systems": 0}}, "Data Systems"),
                              ({"max_items_by_category": {"Unknown": 6}}, "AI")]:
            with self.subTest(cfg=cfg):
                with self.assertRaises(ValueError):
                    c.digest_limit(cfg, category)

    def test_both_categories_six_without_inventing_rows(self):
        for data_count in (3, 9):
            with self.subTest(data_count=data_count), tempfile.TemporaryDirectory() as temp:
                snapshot = self.make_snapshot(temp)
                obj = json.loads(snapshot.read_text())
                rows = [row(f"AI{i:02d}", identity=f"ai{i}27") for i in range(8)]
                rows += [row(f"DB{i:02d}", sub="DB", rank="A" if i == data_count - 1 else "B",
                             identity=f"db{i}27") for i in range(data_count)]
                raw = yaml.safe_dump(rows)
                obj["files"][0].update({"content": raw, "sha256": c.sha(raw)})
                snapshot.write_text(json.dumps(obj))
                cfg = Path(temp) / "config.json"
                cfg.write_text('{"editorial_confirmed":true,"max_items_by_category":{"AI":6,"Data Systems":6}}')
                manifest = c.build(snapshot, cfg, NOW, Path(temp) / "output", False)
                digests = {d["category"]: d for d in manifest["digests"]}
                self.assertEqual(len(digests["AI"]["events"]), 6)
                data = digests["Data Systems"]
                self.assertEqual(len(data["events"]), min(data_count, 6))
                self.assertEqual(data["max_text_events"], 6)
                self.assertEqual(data["omitted_event_count"], max(0, data_count - 6))
                self.assertEqual({e["rank_ccf"] for e in data["events"]}, {"A", "B"})
                self.assertEqual([e["conference"] for e in data["events"]],
                                 sorted(e["conference"] for e in data["events"]))
                self.assertEqual(data["needs_publication_capability_validation"], c.weighted_length(data["text"]) > 280)
                self.assertIsNone(data["image"])

    def test_build(self):
        with tempfile.TemporaryDirectory() as temp:
            snapshot = self.make_snapshot(temp)
            cfg = Path(temp) / "config.json"
            cfg.write_text('{"editorial_confirmed":true,"media_mode":"generated_card"}')
            manifest = c.build(snapshot, cfg, NOW, Path(temp) / "output", False)
            self.assertEqual(len(manifest["digests"]), 1)
            self.assertFalse(manifest["digests"][0]["card_has_more"])
            self.assertNotIn("abstract closed", manifest["digests"][0]["alt_text"])
            from PIL import Image
            with Image.open(manifest["digests"][0]["image"]) as image:
                self.assertEqual(image.size, (1600, 610))
                self.assertEqual(image.getpixel((0, 0)), (242, 242, 242))

    def test_default_link_preview_preserves_long_digest_without_image(self):
        with tempfile.TemporaryDirectory() as temp:
            snapshot = self.make_snapshot(temp)
            obj = json.loads(snapshot.read_text())
            raw = yaml.safe_dump([row(f"ConferenceVeryLongName{i}", sub="DB", identity=f"conf{i}27") for i in range(6)])
            obj["files"][0].update({"content": raw, "sha256": c.sha(raw)})
            snapshot.write_text(json.dumps(obj))
            cfg = Path(temp) / "config.json"
            cfg.write_text('{"editorial_confirmed":true,"max_items_per_category":6}')
            manifest = c.build(snapshot, cfg, NOW, Path(temp) / "output", False)
            digest = manifest["digests"][0]
            self.assertEqual(digest["category"], "Data Systems")
            self.assertEqual(len(digest["events"]), 6)
            self.assertEqual(digest["media_mode"], "link_preview")
            self.assertEqual(digest["link_url"], c.detail_url(digest["events"][0]))
            self.assertNotIn("display_link", digest)
            self.assertNotIn("detail_url", digest)
            self.assertEqual(digest["card_target_url"], c.detail_url(digest["events"][0]))
            self.assertNotIn("requires_separate_card_target_validation", digest)
            self.assertNotIn("publication_blocker", digest)
            self.assertFalse(digest["preview_selection_guaranteed"])
            self.assertEqual(digest["visible_detail_url"], digest["card_target_url"])
            self.assertEqual(digest["text"].count("https://"), 1)
            self.assertEqual(digest["text"].count("ccfddl.com"), 1)
            self.assertTrue(digest["text"].endswith("see details: " + digest["visible_detail_url"] + "\n#ccfddl #conf_deadline #蓝v"))
            self.assertEqual(digest["text"].count("see details: "), 1)
            self.assertNotIn("see details: ccfddl.com", digest["text"])
            self.assertIsNone(digest["image"])
            self.assertFalse(list((Path(temp) / "output").glob("*.png")))
            self.assertTrue(digest["needs_publication_capability_validation"])
            self.assertTrue(digest["requires_live_url_verification"])
            self.assertFalse(digest["link_preview_guaranteed"])
            self.assertEqual(digest["content_sha256"], c.sha(digest["text"]))

    def test_six_text_rows_with_three_card_rows_and_ellipsis(self):
        with tempfile.TemporaryDirectory() as temp:
            snapshot = self.make_snapshot(temp)
            obj = json.loads(snapshot.read_text())
            raw = yaml.safe_dump([row(f"Conference{i}", identity=f"conf{i}27") for i in range(6)])
            obj["files"][0].update({"content": raw, "sha256": c.sha(raw)})
            snapshot.write_text(json.dumps(obj))
            cfg = Path(temp) / "config.json"
            cfg.write_text('{"editorial_confirmed":true,"max_items_per_category":6,"media_mode":"generated_card"}')
            manifest = c.build(snapshot, cfg, NOW, Path(temp) / "output", False)
            self.assertEqual(len(manifest["digests"][0]["events"]), 6)
            self.assertEqual(len(manifest["digests"][0]["card_events"]), 3)
            self.assertTrue(manifest["digests"][0]["card_has_more"])
            self.assertIn("ellipsis", manifest["digests"][0]["alt_text"])
            self.assertNotIn("Conference5", manifest["digests"][0]["alt_text"])
            from PIL import Image
            with Image.open(manifest["digests"][0]["image"]) as image:
                self.assertEqual(image.size, (1600, 970))

    def test_public_outputs_omit_internal_closure_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            snapshot = self.make_snapshot(temp)
            obj = json.loads(snapshot.read_text())
            raw = yaml.safe_dump([row(timeline=[{"abstract_deadline": "2026-10-01 23:59:59", "deadline": "2026-10-08 23:59:59"}])])
            obj["files"][0].update({"content": raw, "sha256": c.sha(raw)})
            snapshot.write_text(json.dumps(obj))
            cfg = Path(temp) / "config.json"
            cfg.write_text('{"editorial_confirmed":true,"media_mode":"generated_card"}')
            manifest = c.build(snapshot, cfg, NOW, Path(temp) / "output", False)
            digest = manifest["digests"][0]
            self.assertTrue(digest["events"][0]["abstract_closed"])
            self.assertNotIn("closed", digest["text"] + digest["alt_text"])
            self.assertNotIn("passed", digest["alt_text"])
            self.assertNotIn("As of", digest["alt_text"])

    def test_stale_and_partial_fail_closed(self):
        for complete, age in ((False, 0), (True, 16)):
            with tempfile.TemporaryDirectory() as temp:
                snapshot = self.make_snapshot(temp, complete, age)
                cfg = Path(temp) / "config.json"
                cfg.write_text('{"editorial_confirmed":true,"media_mode":"generated_card"}')
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
