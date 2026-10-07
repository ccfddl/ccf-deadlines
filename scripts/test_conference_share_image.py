import tempfile
import unittest
import struct
from html.parser import HTMLParser
from pathlib import Path

from conference_share_image import share_images
from generate_seo_pages import generate, stylesheet


class Metadata(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.values[attrs.get('property') or attrs.get('name')] = attrs.get('content')


class ShareImageTests(unittest.TestCase):
    def test_detail_metadata_and_public_png(self):
        conference = {'title': 'A&B "Conference"', 'description': 'A <special> conference',
                      'sub': 'AI', 'confs': [{'year': 2027, 'id': 'ab27'}]}
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            paths = generate([conference], {'AI': 'Artificial Intelligence'}, output)
            page = output / paths[0].lstrip('/') / 'index.html'
            html = page.read_text()
            meta = Metadata(html).values
            canonical = 'https://ccfddl.com/venues/ai/a-b-conference-2027/'
            self.assertEqual(meta['og:url'], canonical)
            self.assertEqual(meta['og:image'], canonical + 'share.png')
            self.assertEqual(meta['twitter:image'], meta['og:image'])
            self.assertEqual(meta['twitter:card'], 'summary_large_image')
            self.assertEqual(meta['twitter:site'], '@ccfddl')
            self.assertEqual(meta['og:image:type'], 'image/png')
            self.assertEqual(meta['og:title'], meta['twitter:title'])
            self.assertIn('A&B "Conference"', meta['og:title'])
            self.assertEqual(meta['description'], meta['og:description'])
            self.assertEqual(meta['description'], meta['twitter:description'])
            self.assertEqual(meta['og:image:alt'], meta['twitter:image:alt'])
            data = (page.parent / 'share.png').read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', data[16:24]), (1200, 630))
            self.assertLess((page.parent / 'share.png').stat().st_size, 5_000_000)
            self.assertNotIn('twitter:image', (output / 'venues/index.html').read_text())

    def test_repeatable_unicode_cards_use_site_stylesheet(self):
        card = {'path': '/venues/ai/aaai-2027/', 'title': 'AAAI 2027',
                'description': 'Conference on Artificial Intelligence', 'category': 'CCF A / Artificial Intelligence',
                'date': 'February 16–23, 2027', 'place': 'Montréal, Québec, Canada，Virtual'}
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            share_images([card], stylesheet(), output)
            target = output / 'venues/ai/aaai-2027/share.png'
            before = target.read_bytes()
            share_images([card], stylesheet(), output)
            self.assertEqual(before, target.read_bytes())
            # Rendering must consume the site's actual computed font stack,
            # not maintain another hardcoded or bundled font.
            renderer = Path(__file__).with_name('render_share_images.mjs').read_text()
            self.assertIn('getComputedStyle(home).fontFamily', renderer)
            self.assertNotIn('DejaVu', renderer)
            self.assertIn('"Roboto Mono","SF Mono",Monaco,monospace', stylesheet())

    def test_long_and_unknown_text_renders(self):
        with tempfile.TemporaryDirectory() as temp:
            share_images([{'path': '/venues/ai/long-2027/', 'title': 'X' * 200,
                           'description': 'A very long conference name ' * 30,
                           'category': 'Artificial Intelligence', 'date': None, 'place': None}], stylesheet(), Path(temp))
            self.assertTrue((Path(temp) / 'venues/ai/long-2027/share.png').is_file())


if __name__ == '__main__':
    unittest.main()
