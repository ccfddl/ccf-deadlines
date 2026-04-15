<div align="center">
  <img src="assets/ccf-ddl-tracker-logo.png" alt="CCF DDL Tracker Logo" width="96" />

  # CCF DDL Tracker

  Chrome extension for tracking CCF deadlines with a compact popup, import flow, and local-only storage.

  **Version:** `v2.0`

  [中文版本](README.zh-CN.md) ·
  [Chrome Web Store](https://chromewebstore.google.com/detail/fnnpcnlkehcbickmdmepjpjimgcleidd?utm_source=item-share-cb) ·
  [Chrome Extension README](chrome/README.md) ·
  [CCFDDL Source](https://github.com/ccfddl/ccf-deadlines) ·
  [Repository](https://github.com/jaychempan/ccf-ddl-tracker)
</div>

---

## Preview

<div align="center">
  <img src="assets/previewv2.0.png" alt="CCF DDL Tracker v2.0 Preview" width="720" />
</div>

The v2.0 popup focuses on density and speed: compact top cards, a persistent import panel, a floating conference picker, footer shortcuts, and a lightweight settings popover.

---

## Install

### Chrome Web Store

Install directly from the Chrome Web Store:

<div align="center">
  <a href="https://chromewebstore.google.com/detail/fnnpcnlkehcbickmdmepjpjimgcleidd?utm_source=item-share-cb" target="_blank" rel="noopener">
    <img src="https://fonts.gstatic.com/s/i/productlogos/chrome_store/v7/192px.svg" alt="Chrome Web Store" width="56" height="56" />
  </a>
</div>

### Load Unpacked

1. Open Chrome and visit `chrome://extensions/`.
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select the [`chrome/`](chrome/) directory in this repository.
5. Pin `CCF DDL Tracker` to the toolbar and click the icon to use it.

<details>
  <summary>Need more extension-specific details?</summary>

  See [chrome/README.md](chrome/README.md) for the extension-only guide.
</details>

---


## Highlights

- **Native popup experience**: Clicking the extension icon opens a compact Chrome popup instead of a separate window.
- **Manual + imported deadlines**: You can add custom deadlines or import recommended conferences from CCFDDL.
- **Official site shortcuts**: Imported conferences retain homepage links, and added cards can open the conference website directly.
- **Bilingual UI**: Switch between Chinese and English from the bottom toolbar.
- **Display preferences**: Choose 24-hour or 12-hour time, and switch date order between `YYYY/MM/DD` and `MM/DD/YYYY`.
- **Local-only data**: All data stays in `chrome.storage.local`, with no account or cloud sync.

---

## Customization

- **Language**: Toggle between Chinese and English from the popup footer.
- **Time format**: Choose `24-hour` or `12-hour (AM/PM)` in the settings panel.
- **Date order**: Choose `YYYY/MM/DD` or `MM/DD/YYYY`.
- **Imported conference cards**: Imported items can be added to your own list and opened directly on the conference website.

---

## Data Source & Privacy

- **Primary source**: [`ccfddl/ccf-deadlines`](https://github.com/ccfddl/ccf-deadlines)
- **Fallback**: CCFDDL ICS feeds when GitHub data is unavailable
- **Storage**: `chrome.storage.local`
- **Privacy**: no account, no cloud sync, no telemetry

---

## Development

- Repository: <https://github.com/jaychempan/ccf-ddl-tracker>
- Chrome extension docs: [chrome/README.md](chrome/README.md)
- Tech stack: Manifest V3, Vanilla JavaScript, `chrome.storage.local`
- Contribution: Issues and pull requests are welcome

---

## Changelog

<details open>
  <summary><strong>v2.0</strong> - UI overhaul, import improvements, settings, and versioning</summary>

  - Reworked the popup into a denser layout with two entry cards and a bottom utility bar
  - Kept the import panel visible by default while moving recommendations into a floating search picker
  - Imported conferences now keep homepage links and added cards can open the official conference site
  - Added display settings for `24-hour / 12-hour` time and `year-month-day / month-day-year` date order
  - Added a `v2.0` version label in the popup header and bumped the extension version
</details>

<details>
  <summary><strong>v1.0.1</strong> - Refresh and day-count fixes</summary>

  - Fixed automatic date refresh issues
  - Added a manual refresh button
  - Corrected same-day deadlines to display `0 days`
</details>

---

## License

MIT License
