# Daily maintenance with a small context budget

Use this procedure for a recurring sweep. A specific user request, new official link, issue, changed source, or near-term extension overrides ordinary cache/backoff gates. This reference describes a run, not authorization to create an automation.

## Local triage

Run from the repository root with Python and PyYAML (already a repository dependency):

```bash
python3 .agents/skills/ccfddl-conference-update/scripts/daily_candidates.py scan --today YYYY-MM-DD
```

Use the user's current date/timezone for `--today`; do not rely on the host date. The default limit is 12 due candidates. The first JSON line gives due/shown/remaining counts; subsequent lines are compact candidate records, with at most three recent source hints (full history stays in the ledger). Read the shortlisted YAML only. Half of a bounded batch prioritizes urgency/local changes; half serves never-checked/oldest-due work so urgent daily rechecks cannot permanently crowd out other candidates. Deferred candidates remain due. `--limit 0` lists the complete due queue when needed. A bounded run must report any remainder, not imply repository-wide coverage. When the backlog cannot be serviced within the desired revisit period (a week is a useful starting point), increase the batch/work budget or report the actual coverage limit.

The scan considers:

- latest/other active editions, including all four supported deadline fields, TBD values, and possible newly published rounds or author-response/decision dates;
- the next edition after the latest tracked one, gated using several past submission cycles when possible;
- repository changes since a prior check, which invalidate that candidate's cached result and override its historical early gate as a fresh local signal. Unchanged early-gated candidates retain their deliberate future checking window.

Dates inferred from history are used solely to decide whether a source check is worthwhile. The helper makes no network requests and writes no conference data. Event-date parsing and the default 180-day pre-submission checking buffer are conservative fallbacks, not an official publication calendar. Adjust `--lead-days`, override a candidate, or inspect manually when known CFP timing/cadence makes the hint unsuitable. An unknown cadence/window stays eligible for inspection rather than claiming there is no announcement.

`--conference ICML` narrows by title or filename. Add `--force` to bypass both cached and historical gates for that scope. For an untracked conference, the helper prints a lead requiring direct inspection; the absence of YAML is not a reason to ignore a user/issue lead. Verify inclusion/ranking metadata with the repository's conventions and authoritative sources before creating a new file.

## Small remote discovery pass

Read newly updated relevant issues and a compact open-PR index once per run (titles, links, update times; bodies only for relevant candidates). Record the remote watermark locally only after successfully enumerating the period; if unavailable, report that coverage limit. Do not download every PR diff or issue body. Route leads to the relevant conference/edition, force a check when needed, and avoid duplicate work across rounds sharing one source URL.

For each due candidate, reuse the last verified official URL, or open the edition's tracked link. Open the relevant dates/CFP page and extract its small dates/track/timezone section. Search only if that fails to locate current official information; stop broad search fanout once the necessary official evidence is found. A reasonable default is one targeted query followed by a narrower official-domain query if needed, then record an inconclusive result. Expand research for a specific actionable lead when justified, instead of treating this daily default as a hard cap.

Reuse already opened page content within the run. Across runs, store a source revision/ETag/Last-Modified or relevant-section digest when the tool exposes it; conditional retrieval can save content when supported. An unchanged full response/revision can defer a no-change candidate, but never rely on a snippet, failed fetch, or partial stale cache to establish facts or to skip the final official recheck for a PR. Do not build a crawler, vector database, whole-site mirror, or parallel web search per conference.

## Local check ledger

By default the helper reads/writes `.cache/ccfddl-conference-update/state.json`, covered by the repository's existing `.cache` ignore rule. It contains no authoritative conference facts and must never enter a commit. Use `--state /absolute/local/path/state.json` to share a durable ledger across temporary worktrees or to use another writable local location. Preserve it between daily runs; a fresh state legitimately has a larger first-run queue. Do not store it only in a disposable `/tmp` clone if the next run needs reuse.

After checking a candidate, record the observed outcome. Copy its `key` from the scan; commands below use placeholders:

```bash
python3 .agents/skills/ccfddl-conference-update/scripts/daily_candidates.py record --today YYYY-MM-DD --key 'CANDIDATE_KEY' --outcome unchanged --source https://official.example/dates --round 'main / round 1' --revision 'etag-or-dates-section-digest'
```

Allowed outcomes: `unchanged`, `tbd`, `not-announced`, `changed`, `covered-pr`, `source-error`, and `conflict`. For no next-edition announcement, record the official organizer/edition page actually checked. Record `source-error` for an inaccessible source; it must not become `not-announced` or `unchanged`. Keep confirmed observations distinct from inferred gates and unsuccessful attempts.

The ledger stores candidate and source/round `last_checked`, `next_check`, outcome, actual URL, optional revision, and a local YAML fingerprint. Give separate `--round` records to separately checked rounds; use `--round all` only after checking all relevant rounds on that source (it supersedes that URL's prior per-round records). Repeated record calls preserve other source/round records and the overall candidate honors their earliest retry date, so a final unchanged page cannot hide another page's TBD/error. Never mark an unexamined round complete just because another round's page is unchanged. For multiple source pages or partial round coverage, pass `--partial` until all necessary checks are finished; it keeps the overall candidate due while retaining the checked source's result. If a URL moves or a round is no longer relevant, remove its obsolete local source record rather than accumulating artificial due work; retain unresolved current sources.

Default rechecks: daily near a published milestone, every 3 days for TBD, weekly for no-change/no-announcement, with repeated quiet checks backing off to 14 days; transient source errors retry in 1, 2, 4, then 7 days. Source conflicts remain visible with a next-day retry. `--next-check YYYY-MM-DD` overrides these hints for a known announcement window. There is no need to reread unchanged long pages every day. Near milestones, new signals, changed YAML, and explicit `--force` override quiet-period backoff. The helper leaves a candidate due when no actual result was recorded.

After changing YAML or resolving a duplicate PR, record against the current checkout so the fingerprint reflects the state examined. A YAML revision invalidates prior source results; the first new record discards their old retry dates, so recheck all still-relevant sources and use `--partial` until done. A PR waiting for merge can use `covered-pr`; still perform the skill's final official and duplicate checks before creating any new PR. Keep other small local metadata (for example the successful issue watermark) in the ledger's `remote` object; the helper preserves it.

## Finish the run

Group multiple checks of one official page and all verified changes for one conference, then use one conference per PR. Validate only after concrete edits; do not generate empty maintenance commits. Report created/covered PRs, meaningful blockers, checked/cached/early counts, and remaining due work. Schedule the next run only if the user explicitly asked for scheduling.
