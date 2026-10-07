# Conference share-card font

DejaVu Sans 2.37 is bundled unchanged for repeatable offline PNG rendering,
including accented conference locations such as Montréal and Québec.
Source: https://dejavu-fonts.github.io/
See LICENSE.txt for the Bitstream Vera license and DejaVu public-domain changes.

The renderer uses the existing conference-page palette. Every edition gets a
1200 × 630 RGB `share.png` next to its generated `index.html`; both Open Graph
and Twitter metadata use its absolute HTTPS URL. Conference dates and location
are used instead of a countdown so cached previews do not claim a stale number
of days remaining. Unknown fields have explicit fallback labels. Long text is
wrapped or ellipsized. These files are generated during the existing SEO build
step, with no external image host, font download, or browser dependency.

Run `python -m unittest discover -s scripts -p 'test_*share_image.py'` and
`python scripts/build_data.py && python scripts/generate_seo_pages.py` to verify.
Preview PNGs are only publicly available after the regular site deployment.
