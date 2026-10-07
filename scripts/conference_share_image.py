"""Render public share PNGs using the conference page's own CSS font stack."""

import json
import subprocess
from pathlib import Path


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
