import tempfile
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from generate_seo_pages import directory_page, edition_page, generate


class SearchPresentationTests(unittest.TestCase):
    def test_conference_heading_excludes_favorites_and_footer_is_not_a_snippet(self):
        class SearchContent(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_heading = False
                self.headings = []
                self.excluded = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'h1':
                    self.in_heading = True
                    self.headings.append('')
                if 'data-nosnippet' in attrs:
                    self.excluded.append(attrs.get('class'))

            def handle_endtag(self, tag):
                if tag == 'h1':
                    self.in_heading = False

            def handle_data(self, data):
                if self.in_heading:
                    self.headings[-1] += data

        edition = {'year': 2026, 'id': 'cloud26', 'timeline': []}
        conference = {'title': 'Cloud', 'sub': 'MX', 'confs': [edition]}
        detail = edition_page(conference, edition, {}, {})
        parsed = SearchContent()
        parsed.feed(detail)
        self.assertEqual(parsed.headings, ['Cloud 2026'])
        self.assertIn('conference-detail-star-count', parsed.excluded)
        self.assertIn('footer-credit', parsed.excluded)
        self.assertIn('class="conference-detail-star-number">0</span>', detail)
        self.assertIn('rel="canonical" href="https://ccfddl.com/venues/mx/cloud-2026/"', detail)
        self.assertNotIn('noindex', detail)

        directory = directory_page([conference], {})
        parsed = SearchContent()
        parsed.feed(directory)
        self.assertIn('footer-credit', parsed.excluded)
        self.assertIn('<title>Venue Deadlines Directory | CCFDDL</title>', directory)
        self.assertNotIn('noindex', directory)


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
            self.assertIn("/venues/ai/acl-2027/", paths)
            page = (output / "venues/ai/acl-2027/index.html").read_text()
            self.assertIn("ACL 2027 Deadline and Conference Dates | CCFDDL", page)
            self.assertIn('rel="canonical" href="https://ccfddl.com/venues/ai/acl-2027/"', page)
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
            self.assertIn('data-raw="2027-08-17 08:00:00" data-source-tz="UTC-12"', page)
            self.assertEqual(page.count('>Conference Opening</div>'), 1)
            self.assertNotIn('Round 1 Conference Opening', page)
            self.assertIn("fetch('/api/bootstrap'", page)
            self.assertIn("fetch('/api/auth/logout'", page)
            self.assertIn("Maintained by @ccfddl. If you find it useful, star or follow", page)
            self.assertIn('data-zh="Artificial Intelligence"', page)
            self.assertIn('href="/venues/ai/acl-2026/"', page)
            self.assertIn('<a href="https://ccfddl.com/">Main site</a>', page)
            self.assertIn('or <a href="https://ccfddl.com/venues/" target="_blank" rel="noopener noreferrer">directory</a>.', page)
            self.assertLess(page.index('class="breadcrumb"'), page.index('id="display-timezone"'))
            directory = (output / "venues/index.html").read_text()
            self.assertIn('href="/venues/ai/acl-2027/"', directory)
            self.assertIn('<a href="https://ccfddl.com/">Main site</a>', directory)
            self.assertIn('id="directory-controls-root"', directory)
            self.assertLess(directory.index('class="breadcrumb"'), directory.index('id="directory-controls-root"'))
            self.assertIn('data-ccf="A"', directory)
            self.assertIn('data-search="ACL Annual Meeting', directory)
            # Controls are rendered by the shared Leptos island, not copied here.
            self.assertNotIn('id="language-switch"', directory)
            self.assertNotIn('id="conference-search"', directory)
            self.assertNotIn('data-rank-key="ccf"', directory)
            self.assertIn('class="directory-categories"', directory)
            self.assertIn('<span>All venues</span>', directory)
            self.assertIn('rel="canonical" href="https://ccfddl.com/venues/"', directory)
            self.assertNotIn('.rank-filter{', (output / "venues/style.css").read_text())
            self.assertNotIn("Conference deadlines / 会议截稿时间", directory)
            self.assertNotIn("Browse the latest edition", directory)
            sitemap = ElementTree.parse(output / "sitemap.xml")
            urls = [node.text for node in sitemap.iter() if node.tag.endswith("loc")]
            self.assertEqual(len(urls), 4)
            self.assertIn("https://ccfddl.com/venues/", urls)
            self.assertFalse(any("/conferences/" in url for url in urls))
            self.assertFalse((output / "conferences").exists())
            self.assertIn("https://ccfddl.com/venues/ai/acl-2027/", urls)

    def test_directory_loads_the_same_versioned_app_and_stylesheet(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "index.html").write_text(
                '<link rel="stylesheet" href="/styles-abc.css">'
                '<link rel="modulepreload" href="/ccfddl-abc.js">'
                '<link rel="modulepreload" href="/snippets/ccfddl-abc/inline0.js">'
                '<link rel="preload" type="application/wasm" href="/ccfddl-abc_bg.wasm">'
            )
            generate([], {}, output)
            directory = (output / "venues/index.html").read_text()
            bootstrap_path = re.search(r'src="(/venues/app-[0-9a-f]+\.js)"', directory).group(1)
            bootstrap = (output / bootstrap_path.lstrip('/')).read_text()
            self.assertIn('href="/styles-abc.css"', directory)
            self.assertNotIn('src="/venues/app.js"', directory)
            self.assertIn('await import("/ccfddl-abc.js")', bootstrap)
            self.assertIn('module_or_path: "/ccfddl-abc_bg.wasm"', bootstrap)
            self.assertIn('DirectoryControlsFailed', bootstrap)
            self.assertIn('id="directory-startup-recovery"', directory)
            self.assertIn('location.reload()', directory)

            # New HTML must never reuse a cached bootstrap pointing to an old build.
            built = (output / 'index.html').read_text()
            (output / 'index.html').write_text(built.replace('abc', 'next'))
            generate([], {}, output)
            next_directory = (output / 'venues/index.html').read_text()
            next_path = re.search(r'src="(/venues/app-[0-9a-f]+\.js)"', next_directory).group(1)
            self.assertNotEqual(bootstrap_path, next_path)
            self.assertIn('/ccfddl-next.js', (output / next_path.lstrip('/')).read_text())

    def test_static_css_is_versioned_on_directory_and_edition_pages(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            conference = {'title': 'ACL', 'sub': 'AI', 'confs': [{'year': 2027, 'timeline': []}]}
            generate([conference], {'AI': 'Artificial Intelligence'}, output)
            directory = (output / 'venues/index.html').read_text()
            css_path = re.search(r'href="(/venues/style-[0-9a-f]+\.css)"', directory).group(1)
            self.assertTrue((output / css_path.lstrip('/')).exists())
            edition = (output / 'venues/ai/acl-2027/index.html').read_text()
            self.assertIn(f'href="{css_path}"', edition)

    def test_incomplete_app_build_fails_instead_of_shipping_missing_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "index.html").write_text('<html></html>')
            with self.assertRaisesRegex(ValueError, "after Trunk"):
                generate([], {}, output)

    def test_duplicate_urls_fail_build(self):
        conference = {"title": "ACL", "sub": "AI", "confs": [{"year": 2027, "id": "one", "timeline": []}]}
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Duplicate conference page"):
                generate([conference, conference], {}, Path(temporary))

    def test_directory_and_sitemap_include_every_conference(self):
        conferences = [
            {"title": "ACL", "sub": "AI", "confs": [{"year": 2027, "id": "acl27", "timeline": []}]},
            {"title": "VLDB", "sub": "DB", "confs": [{"year": 2027, "id": "vldb27", "timeline": []}]},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            generate(conferences, {"AI": "Artificial Intelligence", "DB": "Database"}, output)
            directory = (output / "venues/index.html").read_text()
            urls = [node.text for node in ElementTree.parse(output / "sitemap.xml").iter() if node.tag.endswith("loc")]
            for path in ("ai/acl-2027", "db/vldb-2027"):
                self.assertTrue((output / f"venues/{path}/index.html").exists())
                self.assertIn(f'href="/venues/{path}/"', directory)
                self.assertIn(f"https://ccfddl.com/venues/{path}/", urls)
            self.assertEqual(len(urls), 4)

    def test_unknown_deadline_uses_announced_later_state(self):
        conference = {
            "title": "ACL", "sub": "AI",
            "confs": [{"year": 2027, "id": "acl27", "timeline": [{"deadline": "TBD"}], "timezone": "UTC-12"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            generate([conference], {"AI": "Artificial Intelligence"}, output)
            page = (output / "venues/ai/acl-2027/index.html").read_text()
            self.assertIn('id="conference-next-deadline" aria-live="off">TBD', page)
            self.assertIn("Dates to be announced", page)
            self.assertNotIn("Paper Submission</div>", page)
            self.assertNotIn('id="google-calendar-button"', page)
            self.assertIn('data-deadline-type="opening"', page)
            self.assertEqual(page.count('>Conference Opening</div>'), 1)

    def test_known_opening_is_available_when_submission_deadline_is_unknown(self):
        conference = {
            "title": "Example", "sub": "AI", "confs": [{
                "year": 2099, "id": "example99", "timezone": "PT",
                "date": "June 20-25, 2099", "timeline": [{"deadline": "TBD"}],
            }],
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            generate([conference], {"AI": "Artificial Intelligence"}, output)
            page = (output / "venues/ai/example-2099/index.html").read_text()
            self.assertIn('data-raw="2099-06-20 08:00:00" data-source-tz="PT"', page)
            self.assertIn('id="google-calendar-button"', page)
            self.assertNotIn('id="conference-next-deadline" aria-live="off">TBD', page)


if __name__ == "__main__":
    unittest.main()
