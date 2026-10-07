"""Deterministic, public PNG previews matching the conference page palette.

Use the bundled, licensed DejaVu font so builds do not depend on OS fonts or a network
renderer. Images intentionally contain no clock, countdown or next-deadline
status: social platforms may cache these previews for a long time.
"""

from functools import lru_cache
from pathlib import Path
from unicodedata import normalize

from PIL import Image, ImageDraw, ImageFont


FONT = Path(__file__).resolve().parent / 'share_fonts/DejaVuSans.ttf'
SIZE = (1200, 630)
BACKGROUND = '#faf9f7'
INK = '#2c3e50'
MUTED = '#67727e'
ACCENT = '#d9554f'


@lru_cache(maxsize=16)
def font_for(size):
    return ImageFont.truetype(str(FONT), size=size)


def fit_lines(draw, value, font, width, limit):
    """Wrap even unbroken strings, and ellipsize only the last visible line."""
    remaining = ' '.join(normalize('NFKC', str(value or '')).split())
    lines = []
    while remaining and len(lines) < limit:
        end = len(remaining)
        while end > 1 and draw.textlength(remaining[:end], font=font) > width:
            end -= 1
        if end < len(remaining) and len(lines) + 1 < limit:
            space = remaining.rfind(' ', 0, end + 1)
            if space > 0:
                end = space
        line, remaining = remaining[:end].rstrip(), remaining[end:].lstrip()
        if remaining and len(lines) + 1 == limit:
            while line and draw.textlength(line + '...', font=font) > width:
                line = line[:-1]
            line += '...'
        lines.append(line)
    return lines


def share_image(conference: dict, edition: dict, category: str, target: Path):
    image = Image.new('RGB', SIZE, BACKGROUND)
    draw = ImageDraw.Draw(image)

    def label(value, xy, size, fill=INK, width=1024, limit=1):
        font = font_for(size)
        for number, line in enumerate(fit_lines(draw, value, font, width, limit)):
            draw.text((xy[0], xy[1] + number * (size + 8)), line, font=font, fill=fill)

    label('CCFDDL Open', (64, 42), 28)
    label('Deadlines', (267, 42), 28, ACCENT)
    draw.line((64, 91, 1136, 91), fill='#e5ded6', width=2)
    draw.rounded_rectangle((48, 119, 1152, 540), radius=16, fill='#fffdfa', outline='#e5ded6', width=2)
    rank = (conference.get('rank') or {}).get('ccf')
    label(f'CCF {rank}  /  {category}' if rank else category, (80, 146), 23, MUTED)
    label(f"{conference['title']} {edition['year']}", (80, 192), 62, width=1040)
    label(conference.get('description') or conference['title'], (80, 272), 28, MUTED, width=1040, limit=2)
    label('CONFERENCE DATES', (80, 371), 17, MUTED)
    label(edition.get('date') or 'Dates to be announced', (80, 403), 27, width=1008)
    label(edition.get('place') or 'Location to be announced', (80, 457), 25, MUTED, width=1008)
    label('Conference deadlines and details', (64, 568), 23, MUTED)
    label('ccfddl.com', (961, 565), 27, ACCENT, width=200)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format='PNG', optimize=True)
