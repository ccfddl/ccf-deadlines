import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from conference_share_image import FONT, fit_lines, share_image
from generate_seo_pages import generate


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
            with Image.open(page.parent / 'share.png') as image:
                self.assertEqual(image.size, (1200, 630))
                self.assertEqual(image.format, 'PNG')
                self.assertEqual(image.mode, 'RGB')
            self.assertLess((page.parent / 'share.png').stat().st_size, 5_000_000)
            self.assertNotIn('twitter:image', (output / 'venues/index.html').read_text())

    def test_deterministic_no_countdown_or_deadline_dependency(self):
        conference = {'title': 'AAAI', 'description': 'Conference on Artificial Intelligence', 'rank': {'ccf': 'A'}}
        edition = {'year': 2027, 'date': 'February 16–23, 2027', 'place': 'Montréal, Canada'}
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / 'one.png', Path(temp) / 'two.png'
            share_image(conference, edition, 'Artificial Intelligence', first)
            edition['timeline'] = [{'deadline': '1900-01-01 23:59:59'}]
            share_image(conference, edition, 'Artificial Intelligence', second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_long_text_wraps_and_ellipsizes_within_bounds(self):
        draw = ImageDraw.Draw(Image.new('RGB', (1200, 630)))
        font = ImageFont.truetype(str(FONT), size=28)
        for value in ('A long conference name ' * 30, 'X' * 200, 'Unicode Montréal – Zürich'):
            lines = fit_lines(draw, value, font, 400, 2)
            self.assertLessEqual(len(lines), 2)
            self.assertTrue(all(draw.textlength(line, font=font) <= 400 for line in lines))
        self.assertEqual(fit_lines(draw, '', font, 400, 2), [])


if __name__ == '__main__':
    unittest.main()
