import tempfile
import re
import json
import unittest
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from generate_seo_pages import category_page, deadline_datetime, directory_page, edition_metadata, edition_page, generate, series_page


class BreadcrumbParser(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.structured = []
        self.visible = []
        self.in_json = False
        self.in_breadcrumb = False
        self.in_label = False
        self.buffer = ''
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.in_json = True
            self.buffer = ''
        if tag == 'nav' and attrs.get('class') == 'breadcrumb':
            self.in_breadcrumb = True
        if self.in_breadcrumb and (tag == 'a' or attrs.get('aria-current') == 'page'):
            self.in_label = True

    def handle_data(self, data):
        if self.in_json:
            self.buffer += data
        elif self.in_label:
            self.visible.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.in_json:
            self.structured.append(json.loads(self.buffer))
            self.in_json = False
        if tag in ('a', 'span'):
            self.in_label = False
        if tag == 'nav':
            self.in_breadcrumb = False


class CrawlableMetadataTests(unittest.TestCase):
    def test_breadcrumbs_match_visible_paths_and_edition_canonicals(self):
        editions = [{'year': year, 'timeline': []} for year in (2025, 2027)]
        conference = {'title': 'ACL', 'sub': 'AI', 'confs': editions}
        pages = [
            (directory_page([conference], {}), ['Main site', 'All venues'], '/venues/'),
            (category_page('AI', [conference], {}), ['Main site', 'All venues', 'Artificial Intelligence'], '/venues/ai/'),
            (series_page(conference, {}), ['Main site', 'All venues', 'Artificial Intelligence', 'ACL'], '/venues/ai/acl/'),
        ]
        for edition in editions:
            pages.append((edition_page(conference, edition, {}, {}),
                          ['Main site', 'All venues', 'Artificial Intelligence', 'ACL', str(edition['year'])],
                          f"/venues/ai/acl-{edition['year']}/"))
        for page, labels, path in pages:
            with self.subTest(path=path):
                parsed = BreadcrumbParser(page)
                self.assertEqual(parsed.visible, labels)
                self.assertEqual(len(parsed.structured), 1)
                trail = parsed.structured[0]
                self.assertEqual(trail['@type'], 'BreadcrumbList')
                items = trail['itemListElement']
                self.assertEqual([item['name'] for item in items], labels)
                self.assertEqual([item['position'] for item in items], list(range(1, len(labels) + 1)))
                self.assertTrue(all(item['item'].startswith('https://ccfddl.com/') for item in items))
                self.assertEqual(items[-1]['item'], 'https://ccfddl.com' + path)
                self.assertNotIn('noindex', page)

    def test_jsonld_cannot_close_its_script_with_a_conference_name(self):
        name = 'A&B </script><script>alert(1)</script> 学术'
        edition = {'year': 2027, 'timeline': []}
        conference = {'title': name, 'sub': 'AI', 'confs': [edition]}
        page = edition_page(conference, edition, {}, {})
        parsed = BreadcrumbParser(page)
        self.assertEqual(parsed.structured[0]['itemListElement'][-2]['name'], name)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('\\u003c/script>', page)

    def test_deadline_datetimes_keep_offsets_and_date_precision(self):
        cases = [
            ('2026-07-28 23:59:59', 'AoE', '2026-07-28T23:59:59-12:00'),
            ('2026-07-28 23:59', 'UTC-12', '2026-07-28T23:59:00-12:00'),
            ('2027-01-10 12:30:00', 'UTC', '2027-01-10T12:30:00+00:00'),
            ('2027-01-10 12:30:00', 'UTC+5:30', '2027-01-10T12:30:00+05:30'),
            ('2027-01-10 23:59:59', 'PT', '2027-01-10T23:59:59-08:00'),
            ('2027-07-10 23:59:59', 'PT', '2027-07-10T23:59:59-07:00'),
            ('2027-01-10', '', '2027-01-10'),
        ]
        for raw, zone, expected in cases:
            with self.subTest(raw=raw, zone=zone):
                self.assertEqual(deadline_datetime(raw, zone), expected)
        for raw, zone in [('TBD', 'AoE'), ('2027-02-30', 'UTC'),
                          ('2027-01-10 25:00', 'UTC'), ('2027-01-10 12:00', 'UTC+24'),
                          ('2027-01-10 12:00', 'UTC+5:60'), ('2027-01-10 12:00', 'UNKNOWN'),
                          ('2027-03-14 02:30', 'PT'), ('2027-11-07 01:30', 'PT')]:
            with self.subTest(raw=raw, zone=zone):
                self.assertIsNone(deadline_datetime(raw, zone))

    def test_initial_html_marks_published_deadlines_without_promoting_inferred_opening_times(self):
        edition = {'year': 2027, 'timezone': 'AoE', 'date': 'April 26-30, 2027',
                   'timeline': [{'deadline': '2026-12-01 23:59:59'}]}
        conference = {'title': 'Example', 'sub': 'AI', 'confs': [edition]}
        page = edition_page(conference, edition, {}, {})
        self.assertIn('datetime="2026-12-01T23:59:59-12:00"', page)
        self.assertNotIn('datetime="2027-04-26T08:00:00', page)
        self.assertNotIn('"@type":"Event"', page)
        self.assertNotIn('datePublished', page)
        self.assertIn('class="toolbar-clock" data-nosnippet', page)
        self.assertIn('class="conference-detail-next" data-nosnippet', page)
        deadline = page.split('data-deadline-type="deadline"', 1)[1].split('data-deadline-type="opening"', 1)[0]
        self.assertIn('class="conference-detail-deadline-date">', deadline)
        self.assertIn('class="conference-detail-deadline-status" data-nosnippet', deadline)


class SearchPresentationTests(unittest.TestCase):
    def test_metadata_describes_conference_identity_ratings_and_event(self):
        conference = {'title': 'SIGMOD', 'description': 'ACM Conference on Management of Data',
                      'rank': {'ccf': 'A', 'core': 'A*', 'thcpl': 'A'}}
        edition = {'year': 2027, 'date': 'June 13-19, 2027', 'place': 'Huntington Beach, CA, USA'}
        title, description = edition_metadata(conference, edition)
        self.assertEqual(title, 'SIGMOD 2027: ACM Conference on Management of Data | CCFDDL')
        self.assertEqual(description, 'SIGMOD 2027 (ACM Conference on Management of Data) is a CCF A / CORE A* / THCPL A conference held in Huntington Beach, CA, USA (June 13-19, 2027). Track paper submission deadlines, check deadline time zones, and explore past venues on CCFDDL.')

    def test_metadata_omits_unknown_values_and_duplicate_names(self):
        for unknown in (None, '', 'N', 'TBD', 'TBA', 'Unknown', 'N/A', '-'):
            with self.subTest(unknown=unknown):
                conference = {'title': 'ACL', 'description': 'ACL',
                              'rank': {'ccf': unknown, 'core': unknown, 'thcpl': unknown}}
                title, description = edition_metadata(conference, {'year': 2027, 'date': unknown, 'place': unknown})
                self.assertEqual(title, 'ACL 2027 | CCFDDL')
                self.assertEqual(description, 'ACL 2027 is a conference. Track paper submission deadlines, check deadline time zones, and explore past venues on CCFDDL.')

    def test_metadata_is_escaped_and_consistent_across_search_and_social(self):
        class Metadata(HTMLParser):
            def __init__(self, html):
                super().__init__()
                self.values = {}
                self.feed(html)

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'meta':
                    self.values[attrs.get('property') or attrs.get('name')] = attrs.get('content')

        edition = {'year': 2027, 'place': 'A & B', 'timeline': []}
        conference = {'title': 'A&B', 'description': 'A <special> "conference"',
                      'sub': 'AI', 'confs': [edition]}
        page = edition_page(conference, edition, {}, {})
        meta = Metadata(page).values
        title, description = edition_metadata(conference, edition)
        self.assertIn('A &lt;special&gt; &quot;conference&quot;', page)
        self.assertIn(f'<div class="conference-detail-description" id="conference-overview">{escape(conference["description"])}</div>', page)
        body = page.split('<body', 1)[1]
        self.assertNotIn('Track paper submission deadlines', body)
        self.assertEqual(meta['og:title'], title)
        self.assertEqual(meta['twitter:title'], title)
        for key in ('description', 'og:description', 'twitter:description'):
            self.assertEqual(meta[key], description)

    def test_older_editions_promote_latest_and_keep_history_separate(self):
        # Input order is not guaranteed, and the newest edition can have TBD dates.
        editions = [{'year': year, 'id': f'acl{year}', 'timeline': []}
                    for year in (2025, 2027, 2024, 2026)]
        conference = {'title': 'ACL', 'sub': 'AI', 'confs': editions}
        for edition in editions:
            with self.subTest(year=edition['year']):
                page = edition_page(conference, edition, {}, {})
                self.assertIn(f'rel="canonical" href="https://ccfddl.com/venues/ai/acl-{edition["year"]}/"', page)
                self.assertNotIn('noindex', page)
                has_history = any(other['year'] < edition['year'] for other in editions)
                self.assertEqual('<section class="editions">' in page, has_history)
                history = page.split('<ul class="edition-list">', 1)[1].split('</ul>', 1)[0] if has_history else ''
                self.assertNotIn('This is an earlier edition.', page)
                self.assertNotIn('No earlier edition in the database.', page)
                for other in editions:
                    link = f'href="/venues/ai/acl-{other["year"]}/"'
                    self.assertEqual(link in history, other['year'] < edition['year'])
                if edition['year'] < 2027:
                    self.assertIn('<a href="/venues/ai/acl-2027/">View latest venue: ACL 2027</a>', page)
                    self.assertLess(page.index('<aside class="conference-edition-notice"'), page.index('<article'))
                else:
                    self.assertNotIn('<aside class="conference-edition-notice"', page)

        directory = directory_page([conference], {})
        self.assertIn('href="/venues/ai/acl-2027/"', directory)
        for year in (2024, 2025, 2026):
            self.assertNotIn(f'href="/venues/ai/acl-{year}/"', directory)

    def test_single_edition_has_no_self_link_notice(self):
        edition = {'year': 2027, 'timeline': []}
        conference = {'title': 'ACL', 'sub': 'AI', 'confs': [edition]}
        page = edition_page(conference, edition, {}, {})
        self.assertNotIn('<aside class="conference-edition-notice"', page)
        self.assertNotIn('No earlier edition in the database.', page)
        self.assertNotIn('<section class="editions">', page)

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
        self.assertIn('<title>Venue Directory | CCFDDL</title>', directory)
        self.assertNotIn('noindex', directory)


class VenueHubTests(unittest.TestCase):
    def setUp(self):
        self.conference = {
            'title': 'ACL', 'description': 'Association for Computational Linguistics', 'sub': 'AI',
            'confs': [
                {'year': 2026, 'timeline': [{'deadline': '2026-01-05 23:59:59'}]},
                {'year': 2027, 'timeline': [{'deadline': 'TBD'}]},
                {'year': 2025, 'timeline': []},
            ],
        }

    def test_series_uses_latest_year_even_when_dates_are_unknown(self):
        page = series_page(self.conference, {'AI': 'Artificial Intelligence'})
        self.assertIn('rel="canonical" href="https://ccfddl.com/venues/ai/acl/"', page)
        self.assertIn('View latest venue: ACL 2027', page)
        self.assertIn('Dates to be announced', page)
        self.assertNotIn('2026-01-05', page)
        history = page.split('<ul class="edition-list">')[1].split('</ul>')[0]
        self.assertLess(history.index('ACL 2026'), history.index('ACL 2025'))
        self.assertNotIn('ACL 2027', history)
        self.assertIn('href="/venues/ai/"', page)
        self.assertNotIn('noindex', page)
        self.assertNotIn('id="display-clock"', page)
        self.assertNotIn('id="display-timezone"', page)
        self.assertNotIn('src="/venues/controls.js"', page)
        self.assertNotIn('IMPORTANT DEADLINES', page)

    def test_new_pages_escape_names_and_preserve_source_timezone(self):
        conference = {'title': 'A&B', 'description': '<script>bad</script>', 'sub': 'AI',
                      'confs': [{'year': 2027, 'timeline': [{'deadline': '2026-11-10 23:59:59'}],
                                 'timezone': 'UTC-12'}]}
        series = series_page(conference, {})
        category = category_page('AI', [conference], {'AI': 'Artificial Intelligence'})
        for page in (series, category):
            self.assertIn('A&amp;B', page)
            self.assertIn('&lt;script&gt;bad&lt;/script&gt;', page)
            self.assertNotIn('<script>bad</script>', page)
        self.assertIn('data-source-tz="UTC-12"', series)
        self.assertNotIn('Past venues', series.split('<body', 1)[1])

    def test_generation_connects_directory_categories_series_and_editions(self):
        db = {'title': 'VLDB', 'sub': 'DB', 'confs': [{'year': 2027, 'timeline': []}]}
        empty = {'title': 'Unannounced', 'sub': 'SC', 'confs': []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = generate([self.conference, db, empty], {'AI': '人工智能', 'DB': '数据库', 'SC': '安全'}, root)
            ai = (root / 'venues/ai/index.html').read_text()
            self.assertIn('<title>Artificial Intelligence Conference Deadlines | CCFDDL</title>', ai)
            self.assertIn('rel="canonical" href="https://ccfddl.com/venues/ai/"', ai)
            self.assertIn('href="/venues/ai/acl/"', ai)
            self.assertIn('href="/venues/ai/acl-2027/"', ai)
            self.assertNotIn('VLDB', ai)
            self.assertNotIn('href="/venues/sc/"', ai)
            self.assertNotIn('id="directory-controls-root"', ai)
            directory = (root / 'venues/index.html').read_text()
            self.assertIn('<h2><a href="/venues/ai/"', directory)
            self.assertIn('href="/venues/ai/acl/"', directory)
            for year in (2025, 2026, 2027):
                page = (root / f'venues/ai/acl-{year}/index.html').read_text()
                breadcrumb = page.split('<nav class="breadcrumb"')[1].split('</nav>')[0]
                self.assertIn('href="/venues/ai/"', breadcrumb)
                self.assertIn('href="/venues/ai/acl/"', breadcrumb)
                self.assertIn(f'rel="canonical" href="https://ccfddl.com/venues/ai/acl-{year}/"', page)
            urls = [node.text for node in ElementTree.parse(root / 'sitemap.xml').iter() if node.tag.endswith('loc')]
            self.assertEqual(set(urls), {'https://ccfddl.com' + path for path in ['/', '/venues/', *paths]})
            self.assertEqual(len(urls), len(set(urls)))
            self.assertTrue((root / 'llms.txt').is_file())
            self.assertIn('https://ccfddl.com/mcp', (root / 'llms.txt').read_text())

    def test_series_and_annual_path_collision_fails_build(self):
        namesake = {'title': 'ACL-2027', 'sub': 'AI', 'confs': [{'year': 2028, 'timeline': []}]}
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'Duplicate conference page'):
                generate([self.conference, namesake], {}, Path(temporary))


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
            self.assertIn("ACL 2027: Annual Meeting of the Association for Computational Linguistics | CCFDDL", page)
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
            self.assertIn('<span aria-current="page">All venues</span>', directory)
            self.assertIn('rel="canonical" href="https://ccfddl.com/venues/"', directory)
            self.assertNotIn('.rank-filter{', (output / "venues/style.css").read_text())
            self.assertNotIn("Conference deadlines / 会议截稿时间", directory)
            self.assertNotIn("Browse the latest edition", directory)
            sitemap = ElementTree.parse(output / "sitemap.xml")
            urls = [node.text for node in sitemap.iter() if node.tag.endswith("loc")]
            self.assertEqual(len(urls), 6)
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
            self.assertEqual(len(urls), 8)

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
