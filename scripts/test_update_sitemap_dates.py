import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from update_sitemap_dates import BASE_URL, NS, PageContent, update_dates, venue_file


NOW = datetime(2026, 10, 12, 6, 30, tzinfo=timezone.utc)
NEXT_DAY = datetime(2026, 10, 13, 6, 30, tzinfo=timezone.utc)
PATH = '/venues/ai/aaai-2027/'


def page(*, deadline='2026-07-28 23:59:59', latest='2027', css='old', script='old',
         description='AAAI conference deadlines', structured=None):
    structured = structured or {'@type': 'BreadcrumbList', 'name': 'AAAI'}
    return f'''<!doctype html><html><head><title>AAAI 2027 | CCFDDL</title>
    <meta name="description" content="{description}">
    <link rel="canonical" href="{BASE_URL}{PATH}">
    <link rel="stylesheet" href="/venues/style-{css}.css">
    <script type="application/ld+json">{json.dumps(structured)}</script>
    </head><body><header>Clock: {script}</header><main><h1>AAAI 2027</h1>
    <time data-raw="{deadline}" data-source-tz="AoE">Paper submission</time>
    <a href="/venues/ai/aaai-{latest}/">View latest venue</a>
    <style>.card{{color:{css}}}</style><script src="/app-{script}.js"></script>
    </main><footer>Copyright {script}</footer></body></html>'''


def sitemap(root, paths, dates=None):
    urlset = ElementTree.Element(f'{{{NS}}}urlset')
    for path in paths:
        entry = ElementTree.SubElement(urlset, f'{{{NS}}}url')
        ElementTree.SubElement(entry, f'{{{NS}}}loc').text = BASE_URL + path
        if path in (dates or {}):
            ElementTree.SubElement(entry, f'{{{NS}}}lastmod').text = dates[path]
    (root / 'sitemap.xml').write_bytes(ElementTree.tostring(urlset))


def write_page(root, path, html):
    target = root / path.lstrip('/') / 'index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding='utf-8')


def dates(root):
    return {entry.findtext(f'{{{NS}}}loc'): entry.findtext(f'{{{NS}}}lastmod')
            for entry in ElementTree.parse(root / 'sitemap.xml').getroot()}


class SitemapDatesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'output'
        self.previous = Path(self.temp.name) / 'previous'
        self.output.mkdir()
        self.previous.mkdir()

    def prepare(self, old=None, new=None, old_date=None):
        sitemap(self.previous, ['/', PATH], {PATH: old_date} if old_date else {})
        sitemap(self.output, ['/', PATH])
        write_page(self.output, PATH, new or page())
        if old is not None:
            write_page(self.previous, PATH, old)

    def test_first_rollout_leaves_unchanged_old_pages_undated(self):
        self.prepare(old=page())
        self.assertEqual(update_dates(self.output, self.previous, now=NOW), 0)
        self.assertEqual(dates(self.output), {BASE_URL + '/': None, BASE_URL + PATH: None})

    def test_new_page_gets_date_and_redeployment_preserves_it(self):
        self.prepare()
        self.assertEqual(update_dates(self.output, self.previous, now=NOW), 1)
        self.assertEqual(dates(self.output)[BASE_URL + PATH], '2026-10-12T06:30:00Z')
        # The newly published output becomes the previous site on the next build.
        self.assertEqual(update_dates(self.output, self.output, now=NEXT_DAY), 0)
        self.assertEqual(dates(self.output)[BASE_URL + PATH], '2026-10-12T06:30:00Z')

    def test_changed_deadline_only_dates_affected_page(self):
        self.prepare(old=page(), new=page(deadline='2026-07-29 23:59:59'), old_date='2026-10-01')
        unrelated = '/venues/db/sigmod-2027/'
        write_page(self.previous, unrelated, page())
        write_page(self.output, unrelated, page(css='new', script='new'))
        sitemap(self.previous, ['/', PATH, unrelated], {PATH: '2026-10-01', unrelated: '2026-09-30'})
        sitemap(self.output, ['/', PATH, unrelated])
        self.assertEqual(update_dates(self.output, self.previous, now=NOW), 1)
        result = dates(self.output)
        self.assertEqual(result[BASE_URL + PATH], '2026-10-12T06:30:00Z')
        self.assertEqual(result[BASE_URL + unrelated], '2026-09-30')
        self.assertIsNone(result[BASE_URL + '/'])

    def test_assets_styles_clock_footer_and_whitespace_do_not_refresh_dates(self):
        self.prepare(old=page(), new=page(css='new', script='new').replace('<h1>', '\n<h1>'),
                     old_date='2026-09-30T23:30:00-07:00')
        self.assertEqual(update_dates(self.output, self.previous, now=NOW), 0)
        self.assertEqual(dates(self.output)[BASE_URL + PATH], '2026-09-30T23:30:00-07:00')

    def test_privacy_entry_does_not_affect_venue_content_dates(self):
        for venue_changed in (False, True):
            with self.subTest(venue_changed=venue_changed):
                self.prepare(old=page(), new=page(deadline='2026-07-29 23:59:59') if venue_changed else page(),
                             old_date='2026-10-01')
                sitemap(self.previous, ['/', '/privacy.html', PATH], {PATH: '2026-10-01'})
                sitemap(self.output, ['/', '/privacy.html', PATH])
                (self.previous / 'privacy.html').write_text('<main>Previous policy</main>', encoding='utf-8')
                (self.output / 'privacy.html').write_text('<main>Updated policy</main>', encoding='utf-8')
                self.assertEqual(update_dates(self.output, self.previous, now=NOW), int(venue_changed))
                result = dates(self.output)
                self.assertIsNone(result[BASE_URL + '/privacy.html'])
                self.assertEqual(result[BASE_URL + PATH],
                                 '2026-10-12T06:30:00Z' if venue_changed else '2026-10-01')

    def test_generated_next_deadline_rollover_preserves_date_but_source_edit_updates_it(self):
        import generate_seo_pages as seo

        conference = {'title': 'AAAI', 'sub': 'AI', 'confs': [{
            'year': 2027, 'timezone': 'AoE', 'timeline': [{
                'deadline': '2026-10-12 23:59:59',
                'decision_deadline': '2026-11-30 23:59:59',
            }],
        }]}

        class Clock(datetime):
            value = NOW

            @classmethod
            def now(cls, tz=None):
                return cls.value

        def render(now):
            Clock.value = now
            with patch.object(seo, 'datetime', Clock):
                return seo.edition_page(conference, conference['confs'][0], {}, {})

        old, new = render(NOW), render(NEXT_DAY)
        self.assertNotEqual(old, new)
        self.prepare(old=old, new=new, old_date='2026-10-01')
        self.assertEqual(update_dates(self.output, self.previous, now=NEXT_DAY), 0)
        self.assertEqual(dates(self.output)[BASE_URL + PATH], '2026-10-01')

        # The next widget still points to November, but October's source date changes.
        conference['confs'][0]['timeline'][0]['deadline'] = '2026-10-11 23:59:59'
        self.prepare(old=new, new=render(NEXT_DAY), old_date='2026-10-01')
        self.assertEqual(update_dates(self.output, self.previous, now=NEXT_DAY), 1)

    def test_next_widget_nested_markup_does_not_hide_following_source_content(self):
        before = '<main><div class="conference-detail-next" data-nosnippet><div><strong>Today</strong></div></div><time data-raw="2026-10-12">Paper submission</time></main>'
        after = before.replace('Today', 'Passed')
        self.assertEqual(PageContent(before).value(), PageContent(after).value())
        self.assertNotEqual(PageContent(after).value(), PageContent(after.replace('2026-10-12', '2026-10-13')).value())

    def test_latest_link_metadata_and_structured_data_changes_refresh_dates(self):
        for new in [page(latest='2028'), page(description='Updated conference location'),
                    page(structured={'@type': 'BreadcrumbList', 'name': 'AAAI conference'})]:
            with self.subTest(new=new):
                self.prepare(old=page(), new=new, old_date='2026-10-01')
                self.assertEqual(update_dates(self.output, self.previous, now=NOW), 1)

    def test_jsonld_formatting_and_key_order_do_not_refresh_dates(self):
        original = page()
        changed = original.replace(json.dumps({'@type': 'BreadcrumbList', 'name': 'AAAI'}),
                                   json.dumps({'name': 'AAAI', '@type': 'BreadcrumbList'}, indent=2))
        self.assertEqual(PageContent(original).value(), PageContent(changed).value())

    def test_invalid_or_future_previous_dates_are_omitted(self):
        for old_date in ['2026-02-30', '2027-01-01', '2027-01-01T00:00:00Z',
                         '2026-10-01T00:00:00', 'yesterday', '2026-10-01T00:00:00+24:00']:
            with self.subTest(old_date=old_date):
                self.prepare(old=page(), old_date=old_date)
                self.assertEqual(update_dates(self.output, self.previous, now=NOW), 0)
                self.assertIsNone(dates(self.output)[BASE_URL + PATH])

    def test_missing_previous_sitemap_does_not_invent_old_dates(self):
        self.prepare(old=page())
        (self.previous / 'sitemap.xml').unlink()
        self.assertEqual(update_dates(self.output, self.previous, now=NOW), 0)
        self.assertIsNone(dates(self.output)[BASE_URL + PATH])

    def test_reintroduced_url_is_new_even_if_an_old_file_remains(self):
        self.prepare(old=page())
        sitemap(self.previous, ['/'])
        self.assertEqual(update_dates(self.output, self.previous, now=NOW), 1)
        self.assertEqual(dates(self.output)[BASE_URL + PATH], '2026-10-12T06:30:00Z')

    def test_missing_checkout_or_current_page_fails_before_publishing(self):
        self.prepare(old=page())
        with self.assertRaisesRegex(ValueError, 'checkout is missing'):
            update_dates(self.output, self.previous / 'missing', now=NOW)
        (self.output / PATH.lstrip('/') / 'index.html').unlink()
        with self.assertRaisesRegex(ValueError, 'page is missing'):
            update_dates(self.output, self.previous, now=NOW)

    def test_only_canonical_local_venue_urls_are_read(self):
        for url in ['https://other.test' + PATH, BASE_URL + PATH + '?view=table',
                    BASE_URL + '/venues/../private/', BASE_URL + '/venues/%2e%2e/private/',
                    BASE_URL + '/venues/%5cprivate/', BASE_URL + '/venues/ai/aaai-2027',
                    'https://other.test/privacy.html', BASE_URL + '/privacy.html?view=policy',
                    BASE_URL + '/privacy.html#policy', BASE_URL + '/privacy.html/',
                    BASE_URL + '/%70rivacy.html', BASE_URL + '/private/../privacy.html']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                venue_file(self.output, url)
        self.assertIsNone(venue_file(self.output, BASE_URL + '/'))
        self.assertIsNone(venue_file(self.output, BASE_URL + '/privacy.html'))


if __name__ == '__main__':
    unittest.main()
