# Website data loading

Run `python scripts/build_data.py` before `trunk build` or `trunk serve`.

The complete `public/conference/allconf.yml`, `allacc.yml`, `allconf.json`, and
`allacc.json` remain available with their original structures. Conference YAML
entries and acceptance-rate YAML entries are still maintained separately.

Additional generated files support smaller requests:

- `initial.json` contains the latest edition of each conference, editions with
  future submission/rebuttal/decision dates, and the previous edition needed to
  estimate a TBD deadline. It references a content-named history file.
- `parts/history-<hash>.json` contains the remaining editions. The frontend loads
  it when showing past conferences, changing the reference time, or restoring
  a favorite absent from the initial data. Merging removes duplicate edition IDs.
- `parts/acceptance-00.json` through `acceptance-15.json` contain all acceptance
  years, grouped by an FNV-1a hash of the conference title. Opening a conference
  detail loads just that group; the original two-year display is preserved.

No localStorage data cache is added. Loaded groups are reused only while the
page is open. If a split file is unavailable during deployment, the frontend
falls back to the original full JSON file. Generated files remain ignored by Git
and are assembled in both CI builds and deployment builds.

Run regression checks with:

```bash
python -m unittest discover -s scripts -p 'test_*.py'
cargo test
```
