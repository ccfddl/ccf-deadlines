# Conference link-preview cards

The SEO generator writes one public 1200 × 630 PNG beside each edition's
`index.html`. Open Graph and Twitter metadata contain its absolute HTTPS URL.
The renderer consumes the generated conference-page stylesheet and uses the
computed `.detail-page .home` font family, so there is no separate card font.
The website uses a platform fallback stack; the actual font can differ between
operating systems. No font binary or visitor-facing webfont is added.

Run `python scripts/build_data.py && python scripts/generate_seo_pages.py`.
The PNG step requires Node.js 22+ and Chrome/Chromium (or `CHROME_BINARY`).
Deploy selects the runner's preinstalled stable Google Chrome at
`/usr/bin/google-chrome` through `CHROME_BINARY`, rather than the Chromium snapshot.
Only Deploy runs the browser-launcher tests and real share-image tests, including
PNG generation, before assembling data and building the site.
MergeCheck uses `python scripts/generate_seo_pages.py --skip-share-images` to
validate the static pages and sitemap without starting a browser.
The default command used by Deploy still requires every share image to render successfully.
It starts one browser for all editions, renders locally to canvas, and does not
download external assets.
Conference values are passed as data, never executable HTML. Cards include every known abstract, paper, rebuttal and decision timestamp in
source round order, with the unconverted source timezone shown prominently.
Single-round cards use labeled rows; multi-round cards use a complete date table.
Date/time cells are never truncated. More than 12 populated rounds, an
unsupported deadline field, a duplicate field or an overflowing date cell fails
explicitly rather than publishing an incomplete image. The current largest
edition is VLDB 2027: 24 dates across 12 rounds. Non-date titles/descriptions may
be shortened; unknown dates are not invented. Cards omit live countdowns and
next-deadline status because social previews are cached. The HTML page body is
unchanged; metadata uses `share.png?v=deadlines-2` to refresh earlier previews.

Tests: `python -m unittest discover -s scripts -p 'test_*share_image.py'`.
The PNG URLs become publicly accessible only after the regular site deployment.

Startup prints the selected browser/version, retains a bounded stderr tail for
failures, and exits without publishing if rendering fails. Launcher regression tests:
`node --test scripts/test_share_browser.mjs`.
