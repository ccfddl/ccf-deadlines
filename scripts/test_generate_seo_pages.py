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
            paths = generate(
                [conference],
                {"DS": "计算机体系结构/并行与分布计算/存储系统", "AI": "Artificial Intelligence"},
                output,
                {"ACL": [{"year": 2026, "str": "20.0%"}, {"year": 2025, "str": "19.0%"}]},
            )
            self.assertIn("/conferences/ai/acl-2027/", paths)
            page = (output / "conferences/ai/acl-2027/index.html").read_text()
            self.assertIn("ACL 2027 Deadline and Conference Dates | CCFDDL", page)
            self.assertIn('rel="canonical" href="https://ccfddl.com/conferences/ai/acl-2027/"', page)
            self.assertIn("2027-01-04 23:59", page)
            self.assertIn("Kyoto, Japan", page)
            self.assertIn("ARR Submission &lt;script&gt;", page)
            self.assertNotIn("ARR Submission <script>", page)
            self.assertIn('class="conference-detail-next"', page)
            self.assertIn("Acc. Rate: 20.0%  ·  19.0%", page)
            self.assertNotIn('id="language-switch"', page)
            self.assertIn('id="github-login-link"', page)
            self.assertIn('id="github-star-count"', page)
            self.assertIn('id="display-clock"', page)
            self.assertIn('id="display-timezone"', page)
            self.assertIn('class="directory-toolbar detail-toolbar"', page)
            self.assertNotIn('id="conference-search"', page)
            self.assertNotIn('data-rank-key="ccf"', page)
            self.assertNotIn('class="category-filter-grid"', page)
            self.assertIn('data-raw="2027-01-04 23:59:59"', page)
            self.assertIn("fetch('/api/bootstrap'", page)
            self.assertIn("fetch('/api/auth/logout'", page)
            self.assertIn("Maintained by @ccfddl. If you find it useful, star or follow", page)
            self.assertIn('data-zh="Artificial Intelligence"', page)
            self.assertIn('href="/conferences/ai/acl-2026/"', page)
            self.assertIn('<a href="https://ccfddl.com/">Main site</a>', page)
            self.assertLess(page.index('class="breadcrumb"'), page.index('id="display-timezone"'))
            directory = (output / "conferences/index.html").read_text()
            self.assertIn('href="/conferences/ai/acl-2027/"', directory)
            self.assertIn('<a href="https://ccfddl.com/">Main site</a>', directory)
            self.assertIn('id="language-switch"', directory)
            self.assertLess(directory.index('class="breadcrumb"'), directory.index('id="language-switch"'))
            self.assertIn('data-ccf="A"', directory)
            self.assertIn('data-search="ACL Annual Meeting', directory)
            self.assertIn('id="conference-search"', directory)
            self.assertIn('id="display-clock"', directory)
            self.assertIn('placeholder="search conference"', directory)
            self.assertIn('data-rank-key="ccf"', directory)
            self.assertIn('class="category-filter-grid"', directory)
            self.assertIn('function filterDirectory()', (output / "conferences/controls.js").read_text())
            self.assertNotIn("Conference deadlines / 会议截稿时间", directory)
            self.assertNotIn("Browse the latest edition", directory)
            sitemap = ElementTree.parse(output / "sitemap.xml")
            urls = [node.text for node in sitemap.iter() if node.tag.endswith("loc")]
            self.assertEqual(len(urls), 4)
            self.assertIn("https://ccfddl.com/conferences/ai/acl-2027/", urls)

    def test_duplicate_urls_fail_build(self):
        conference = {"title": "ACL", "sub": "AI", "confs": [{"year": 2027, "id": "one", "timeline": []}]}
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Duplicate conference page"):
                generate([conference, conference], {}, Path(temporary))

    def test_unknown_deadline_uses_announced_later_state(self):
        conference = {
            "title": "ACL", "sub": "AI",
            "confs": [{"year": 2027, "id": "acl27", "timeline": [{"deadline": "TBD"}], "timezone": "UTC-12"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            generate([conference], {"AI": "Artificial Intelligence"}, output)
            page = (output / "conferences/ai/acl-2027/index.html").read_text()
            self.assertIn('id="conference-next-deadline" aria-live="off">TBD', page)
            self.assertIn("Dates to be announced", page)
            self.assertNotIn("Paper Submission Deadline</div>", page)
            self.assertNotIn('id="google-calendar-button"', page)


if __name__ == "__main__":
    unittest.main()
