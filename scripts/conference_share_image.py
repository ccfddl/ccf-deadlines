"""Render public share PNGs using the conference page's own CSS font stack."""

import json
import re
import subprocess
from pathlib import Path


DEADLINE_FIELDS = (
    ('abstract_deadline', 'Abstract'), ('deadline', 'Paper'),
    ('rebuttal_deadline', 'Rebuttal'), ('decision_deadline', 'Decision'),
)
KNOWN_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}(?::\d{2})?)?$")


def deadline_card_data(edition: dict) -> dict:
    """Keep every known source timestamp, field and original round identity."""
    deadlines = []
    for number, point in enumerate(edition.get('timeline') or [], 1):
        for field, label in DEADLINE_FIELDS:
            raw = str(point.get(field) or '').strip()
            if KNOWN_DATE.fullmatch(raw):
                deadlines.append({'round': number, 'field': field, 'label': label, 'raw': raw})
    return {'deadlines': deadlines, 'round_count': len(edition.get('timeline') or []), 'timezone': str(edition.get('timezone') or 'Timezone not listed')}


def share_images(cards: list[dict], css: str, output: Path):
    if not cards:
        return
    # One browser session for the whole build; no fonts or browser packages are
    # downloaded. CI already uses Chrome and Node for the site's browser tests.
    subprocess.run(
        ['node', str(Path(__file__).with_name('render_share_images.mjs')), str(output.resolve())],
        input=json.dumps({'cards': cards, 'css': css}), text=True, check=True,
        timeout=600,
    )
