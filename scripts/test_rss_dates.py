import copy
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extensions/cli/ccfddl"))
from convert_to_rss import ATOM_NAMESPACE, convert_to_rss


class RssDateTests(unittest.TestCase):
    def setUp(self):
        self.conference = {
            "title": "Example",
            "description": "Example Conference",
            "sub": "AI",
            "rank": {"ccf": "A", "core": "A*"},
            "dblp": "example",
            "confs": [{
                "year": 2099,
                "link": "https://example.com/conference/2099/",
                "timezone": "AoE",
                "date": "July 20-23, 2099",
                "place": "Example City",
                "timeline": [{
                    "abstract_deadline": "2099-01-01 23:59:59",
                    "deadline": "2099-01-08 23:59:59",
                    "rebuttal_deadline": "2099-02-01 23:59:59",
                    "decision_deadline": "2099-03-01 23:59:59",
                    "comment": "Regular round",
                }],
            }],
        }

    def feed(self, conferences, lang="en", other_files=(), feed_url=None):
        with tempfile.TemporaryDirectory() as directory:
            sources = []
            for index, records in enumerate((conferences, *other_files)):
                source = Path(directory) / f"conference-{index}.yml"
                source.write_text(yaml.safe_dump(records), encoding="utf-8")
                sources.append(str(source))
            output = Path(directory) / "deadlines.xml"
            convert_to_rss(sources, str(output), lang, {"AI": "人工智能"}, feed_url)
            return ET.fromstring(output.read_bytes())

    def test_future_deadlines_do_not_claim_future_publication_dates(self):
        root = self.feed([self.conference])
        channel = root.find("channel")
        self.assertEqual(root.attrib["version"], "2.0")
        for required in ("title", "link", "description"):
            self.assertTrue(channel.findtext(required))
        self.assertIsNone(channel.find("lastBuildDate"))
        items = channel.findall("item")
        self.assertEqual(len(items), 4)
        timeline = self.conference["confs"][0]["timeline"][0]
        dates = [timeline[field] for field in ("abstract_deadline", "deadline",
                                               "rebuttal_deadline", "decision_deadline")]
        for item, key, raw in zip(items, ("abstract", "deadline", "rebuttal", "decision"), dates):
            with self.subTest(key=key):
                self.assertIsNone(item.find("pubDate"))
                self.assertIn(f"Deadline (AoE): {raw}", item.findtext("description"))
                self.assertIn("[Regular round]", item.findtext("title"))
                self.assertEqual(item.findtext("link"), "https://example.com/conference/2099/")
                self.assertEqual(item.findtext("category"), "AI")
                self.assertEqual(item.findtext("guid"), f"Example-2099-{key}-{raw}@ccfddl.com")
                self.assertEqual(item.find("guid").attrib, {"isPermaLink": "false"})

    def test_date_only_and_pt_deadlines_keep_source_precision_in_both_languages(self):
        for zone in ("PT", "UTC+8"):
            for lang, label in (("en", "Deadline"), ("zh", "截止时间")):
                with self.subTest(zone=zone, lang=lang):
                    conference = copy.deepcopy(self.conference)
                    edition = conference["confs"][0]
                    edition["timezone"] = zone
                    edition["timeline"] = [{"deadline": "2020-01-08"},
                                           {"deadline": "2099-07-08 23:59:59"}]
                    channel = self.feed([conference], lang).find("channel")
                    items = channel.findall("item")
                    self.assertEqual(len(items), 2)
                    self.assertEqual(channel.findtext("language"), "en" if lang == "en" else "zh-CN")
                    for item, entry in zip(items, edition["timeline"]):
                        self.assertIn(f"{label} ({zone}): {entry['deadline']}", item.findtext("description"))
                        self.assertIsNone(item.find("pubDate"))

    def test_unknown_and_invalid_dates_are_still_skipped(self):
        edition = self.conference["confs"][0]
        edition["timeline"] = [{"deadline": value} for value in
                               ("TBD", "2099-02-30", "2099-01-08 25:00:00")]
        self.assertEqual(self.feed([self.conference]).findall("./channel/item"), [])
        edition["timeline"] = [{"deadline": "2099-01-08 23:59:59"}]
        edition["timezone"] = "UNKNOWN"
        self.assertEqual(self.feed([self.conference]).findall("./channel/item"), [])
        self.assertEqual(self.feed(None).findall("./channel/item"), [])

    def test_newer_venue_years_first_across_files_with_stable_rounds_and_types(self):
        first = copy.deepcopy(self.conference)
        old = copy.deepcopy(first["confs"][0])
        old["year"] = 2098
        latest = copy.deepcopy(first["confs"][0])
        latest["year"] = 2100
        latest["timeline"].append({"deadline": "2099-04-01", "comment": "Second round"})
        first["confs"] = [old, latest]
        middle = copy.deepcopy(self.conference)
        middle["title"] = "Middle"
        tied = copy.deepcopy(self.conference)
        tied["title"] = "Other"
        tied["confs"][0]["year"] = "2100"
        tied["confs"][0]["timeline"] = [{"deadline": "2099-05-01"}]

        for lang in ("en", "zh"):
            with self.subTest(lang=lang):
                channel = self.feed([first], lang, ([middle, tied],)).find("channel")
                items = channel.findall("item")
                guids = [item.findtext("guid") for item in items]
                expected = []
                for title, edition in (("Example", latest), ("Other", tied["confs"][0]),
                                       ("Middle", middle["confs"][0]), ("Example", old)):
                    for entry in edition["timeline"]:
                        for field, key in (("abstract_deadline", "abstract"), ("deadline", "deadline"),
                                           ("rebuttal_deadline", "rebuttal"), ("decision_deadline", "decision")):
                            if field in entry:
                                expected.append(f"{title}-{edition['year']}-{key}-{entry[field]}@ccfddl.com")
                self.assertEqual(guids, expected)
                self.assertTrue(all(item.find("pubDate") is None for item in items))
                self.assertEqual([child.tag for child in channel][:4],
                                 ["title", "link", "description", "language"])

    def test_optional_self_link_identifies_feed_without_changing_items(self):
        for lang in ("en", "zh"):
            with self.subTest(lang=lang):
                plain = self.feed([self.conference], lang).find("channel")
                url = f"https://example.com/feeds/deadlines_{lang}_core_Astar_AI.xml"
                published = self.feed([self.conference], lang, feed_url=url).find("channel")
                tag = f"{{{ATOM_NAMESPACE}}}link"
                self.assertIsNone(plain.find(tag))
                self.assertEqual([link.attrib for link in published.findall(tag)], [{
                    "href": url, "rel": "self", "type": "application/rss+xml",
                }])
                self.assertEqual(ET.tostring(plain.find("link")), ET.tostring(published.find("link")))
                self.assertEqual([ET.tostring(item) for item in plain.findall("item")],
                                 [ET.tostring(item) for item in published.findall("item")])
        for invalid in ("/feeds/deadlines.xml", "javascript:alert(1)", "https:///feed.xml"):
            with self.subTest(url=invalid), self.assertRaises(ValueError):
                self.feed([self.conference], feed_url=invalid)

    def test_shared_deadline_rounds_keep_distinct_ids_across_languages_and_filters(self):
        conference = copy.deepcopy(self.conference)
        shared = '2099-03-01 23:59:59'
        conference['confs'][0]['timeline'] = [
            {'deadline': 'TBD', 'comment': 'Unannounced round'},
            {'decision_deadline': shared, 'deadline': '2099-01-08', 'comment': 'First round'},
            {'decision_deadline': shared, 'deadline': '2099-02-08', 'comment': 'Second round'},
            {'decision_deadline': shared, 'comment': 'Third round'},
        ]
        unrelated = copy.deepcopy(self.conference)
        unrelated['title'] = 'Other'
        expected = [
            'Example-2099-deadline-2099-01-08@ccfddl.com',
            f'Example-2099-decision-{shared}@ccfddl.com',
            'Example-2099-deadline-2099-02-08@ccfddl.com',
            f'Example-2099-decision-{shared}-round-3@ccfddl.com',
            f'Example-2099-decision-{shared}-round-4@ccfddl.com',
        ]
        for lang in ('en', 'zh'):
            for other_files in ((), ([unrelated],)):
                with self.subTest(lang=lang, filtered=not other_files):
                    items = self.feed([conference], lang, other_files).findall('./channel/item')
                    selected = [item for item in items if item.findtext('title').startswith('Example ')]
                    self.assertEqual([item.findtext('guid') for item in selected], expected)
                    self.assertEqual(len({item.findtext('guid') for item in selected}), len(selected))
                    self.assertIn('[Second round]', selected[3].findtext('title'))


if __name__ == "__main__":
    unittest.main()
