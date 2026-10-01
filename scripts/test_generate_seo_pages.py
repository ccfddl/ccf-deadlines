import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from generate_seo_pages import generate


class SeoPageTests(unittest.TestCase):
    def test_acl_page_has_crawlable_content_and_directory_link(self):
        conference = {
            "title": "ACL",
            "description": "Annual Meeting of the Association for Computational Linguistics",
            "sub": "AI",
            "rank": {"ccf": "A"},
            "confs": [
                {"year": 2026, "id": "acl26", "timeline": [{"deadline": "2026-01-05 23:59:59"}], "timezone": "UTC-12", "date": "July 2026", "place": "San Diego"},
                {"year": 2027, "id": "acl27", "link": "https://2027.aclweb.org/", "timeline": [{"deadline": "2027-01-04 23:59:59", "comment": "ARR Submission <script>"}], "timezone": "UTC-12", "date": "August 17-22, 2027", "place": "Kyoto, Japan"},
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            paths = generate([conference], {"AI": "Artificial Intelligence"}, output)
            self.assertIn("/conferences/ai/acl-2027/", paths)
            page = (output / "conferences/ai/acl-2027/index.html").read_text()
            self.assertIn("ACL 2027 Deadline and Conference Dates | CCFDDL", page)
            self.assertIn('rel="canonical" href="https://ccfddl.com/conferences/ai/acl-2027/"', page)
            self.assertIn("2027-01-04 23:59", page)
            self.assertIn("Kyoto, Japan", page)
            self.assertIn("ARR Submission &lt;script&gt;", page)
            self.assertNotIn("ARR Submission <script>", page)
            self.assertIn('href="/conferences/ai/acl-2026/"', page)
            directory = (output / "conferences/index.html").read_text()
            self.assertIn('href="/conferences/ai/acl-2027/"', directory)
            sitemap = ElementTree.parse(output / "sitemap.xml")
            urls = [node.text for node in sitemap.iter() if node.tag.endswith("loc")]
            self.assertEqual(len(urls), 4)
            self.assertIn("https://ccfddl.com/conferences/ai/acl-2027/", urls)

    def test_duplicate_urls_fail_build(self):
        conference = {"title": "ACL", "sub": "AI", "confs": [{"year": 2027, "id": "one", "timeline": []}]}
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Duplicate conference page"):
                generate([conference, conference], {}, Path(temporary))


if __name__ == "__main__":
    unittest.main()
