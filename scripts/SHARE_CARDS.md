# Conference link-preview cards

The SEO generator writes one public 1200 × 630 PNG beside each edition's
`index.html`. Open Graph and Twitter metadata contain its absolute HTTPS URL.
The renderer consumes the generated conference-page stylesheet and uses the
computed `.detail-page .home` font family, so there is no separate card font.
The website uses a platform fallback stack; the actual font can differ between
operating systems. No font binary or visitor-facing webfont is added.

Run `python scripts/build_data.py && python scripts/generate_seo_pages.py`.
The PNG step requires Node.js 22+ and Chrome/Chromium (or `CHROME_BINARY`), the
same tools used by the existing browser tests. CI and deployment explicitly
select `/usr/bin/chromium` through `CHROME_BINARY` so neither silently chooses
a different Google Chrome release from a changing runner image. It starts one browser for all
editions, renders locally to canvas, and does not download external assets.
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
CI uploads AAAI, SIGMOD and VLDB 2027 images as `deadline-card-previews` for
visual review before deployment.

Tests: `python -m unittest discover -s scripts -p 'test_*share_image.py'`.
The PNG URLs become publicly accessible only after the regular site deployment.

Startup prints the selected browser/version, retains a bounded stderr tail for
failures, and exits without publishing if rendering fails. Both workflows run
a small render test before the expensive Rust build. Launcher regression tests:
`node --test scripts/test_share_browser.mjs`.
