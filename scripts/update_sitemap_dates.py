#!/usr/bin/env python3
"""Date venue sitemap entries when their published content actually changes."""

import argparse
import json
import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


BASE_URL = 'https://ccfddl.com'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ElementTree.register_namespace('', NS)


class PageContent(HTMLParser):
    """Compare content, links and metadata, excluding scripts and presentation."""

    def __init__(self, html):
        super().__init__()
        self.main = False
        self.title = False
        self.jsonld = False
        self.ignored = []
        self.buffer = []
        self.text = []
        self.titles = []
        self.links = []
        self.fields = []
        self.metadata = []
        self.structured = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.ignored:
            if tag in {'script', 'style', 'svg'}:
                self.ignored.append(tag)
            return
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.jsonld = True
            self.buffer = []
            return
        if tag in {'script', 'style', 'svg'}:
            self.ignored.append(tag)
            return
        if tag == 'main':
            self.main = True
        if tag == 'title':
            self.title = True
        if tag == 'meta' and attrs.get('name') == 'description':
            self.metadata.append(attrs.get('content', ''))
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.metadata.append(attrs.get('href', ''))
        if self.main:
            if tag == 'a' and 'href' in attrs:
                self.links.append(attrs['href'])
            fields = {key: value for key, value in attrs.items() if key in {
                'datetime', 'data-raw', 'data-source-tz', 'data-en', 'data-zh',
                'data-ccf', 'data-core', 'data-thcpl', 'data-search',
            }}
            if fields:
                self.fields.append(fields)

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag == 'script' and self.jsonld:
            self.structured.append(json.loads(''.join(self.buffer)))
            self.jsonld = False
        elif tag == 'main':
            self.main = False
        elif tag == 'title':
            self.title = False

    def handle_data(self, data):
        if self.ignored:
            return
        if self.jsonld:
            self.buffer.append(data)
        elif self.title:
            self.titles.append(data)
        elif self.main:
            self.text.append(data)

    def value(self):
        normalize = lambda parts: ' '.join(' '.join(parts).split())
        return (normalize(self.titles), normalize(self.text), self.links,
                self.fields, self.metadata, self.structured)


def venue_file(root: Path, url: str) -> Path | None:
    parsed = urlsplit(url)
    if f'{parsed.scheme}://{parsed.netloc}' != BASE_URL or parsed.query or parsed.fragment:
        raise ValueError(f'Non-canonical sitemap URL: {url}')
    path = unquote(parsed.path)
    if path == '/':
        # App content is in WebAssembly; its build time is not a content date.
        return None
    if not path.startswith('/venues/') or not path.endswith('/') or '\\' in path:
        raise ValueError(f'Unexpected venue URL: {url}')
    if any(part in {'.', '..'} for part in path.split('/')):
        raise ValueError(f'Unsafe venue URL: {url}')
    target = root / path.lstrip('/') / 'index.html'
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Venue URL leaves site directory: {url}')
    return target


def valid_lastmod(value: str | None, now: datetime) -> bool:
    if not value:
        return False
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return date.fromisoformat(value) <= now.date()
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})', value):
            return False
        when = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return when <= now
    except ValueError:
        return False


def update_dates(output: Path, previous: Path, *, now: datetime | None = None) -> int:
    if not previous.is_dir():
        raise ValueError('Published site checkout is missing')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Update time must include a timezone')
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    previous_sitemap = previous / 'sitemap.xml'
    old_dates = {}
    if previous_sitemap.exists():
        for entry in ElementTree.parse(previous_sitemap).getroot().findall(f'{{{NS}}}url'):
            old_dates[entry.findtext(f'{{{NS}}}loc')] = entry.findtext(f'{{{NS}}}lastmod')
    sitemap = output / 'sitemap.xml'
    tree = ElementTree.parse(sitemap)
    updated = 0
    for entry in tree.getroot().findall(f'{{{NS}}}url'):
        url = entry.findtext(f'{{{NS}}}loc')
        current_file = venue_file(output, url or '')
        if current_file is None:
            continue
        if not current_file.is_file():
            raise ValueError(f'Sitemap venue page is missing: {url}')
        old_file = venue_file(previous, url)
        current = PageContent(current_file.read_text(encoding='utf-8')).value()
        changed = (previous_sitemap.exists() and url not in old_dates) or not old_file.is_file()
        if not changed:
            changed = current != PageContent(old_file.read_text(encoding='utf-8')).value()
        value = now.isoformat().replace('+00:00', 'Z') if changed else old_dates.get(url)
        # An unchanged page with no known date remains undated on first rollout.
        for element in entry.findall(f'{{{NS}}}lastmod'):
            entry.remove(element)
        if valid_lastmod(value, now):
            ElementTree.SubElement(entry, f'{{{NS}}}lastmod').text = value
        updated += changed
    sitemap.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' +
                        ElementTree.tostring(tree.getroot(), encoding='utf-8') + b'\n')
    return updated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--previous', type=Path, required=True)
    args = parser.parse_args()
    count = update_dates(args.output, args.previous)
    print(f'Dated {count} new or changed venue pages; preserved known dates for unchanged pages')
