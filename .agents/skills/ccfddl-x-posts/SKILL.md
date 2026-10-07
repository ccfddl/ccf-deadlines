---
name: ccfddl-x-posts
description: Prepare and, with a verified authenticated publishing route and authorization, publish daily conference-deadline countdown posts for @ccfddl on X/Twitter. Use for the recurring CCFDDL campaign, AI/Data Systems countdown text, email-notification-style social cards, schedule setup, publication checks, or maintaining this workflow. Read the live CCFDDL source, include CCF A and B plus ICLR and MLSys, and link every digest to ccfddl.com.
---

# CCFDDL X Posts

Create up to two English digests per publication day: one **AI**, one **Data Systems**, with concise countdown text and one canonical CCFDDL detail-page link for the first selected conference. Use that page for the platform link preview; do not attach a generated PNG by default.

## Campaign contract

- Use exactly the verified X account **@ccfddl**. Do not treat a display name, brand name, or workspace as account proof.
- Include CCF A and CCF B conferences plus explicit ICLR and MLSys exceptions. Classify `sub: AI` as AI and **all remaining source subjects** as Data Systems. This is the requested campaign grouping, not a claim about the source taxonomy.
- Publish in the morning in **America/Los_Angeles**, with automatic daylight-saving changes. Prefer flexible scheduling around 08:00 local; do not impose an exact time unless requested.
- Use English as the stated operational default. Preserve later user changes in campaign configuration.
- Publish at most one digest per category per local calendar day. Choose future abstract or paper deadlines within the configured 120-day horizon, up to six text rows. When the user explicitly selects the optional generated-card fallback, show only the first three rows in the image, followed by an ellipsis when more eligible rows exist. Keep all candidates when they fit; on overflow, retain representation of both eligible CCF A and CCF B tiers instead of allowing nearer B deadlines to displace every A conference. Record any omissions in the manifest and surface material omissions rather than silently hiding a tier. Skip empty categories.
- Include no unrelated posts, replies, DMs, follows, or engagement actions. Do not put credentials, account identifiers beyond the public handle, private state, or publication ledgers in the public source repository.
- Treat this skill as the workflow, not proof that a schedule or publishing connection exists. Never report live posting as enabled without verifying the actual provider and schedule.

Read [references/config.json](references/config.json) for editable campaign settings. Read [references/source-and-publishing.md](references/source-and-publishing.md) for source mapping, identity, conflict handling, provider checks, and state transitions.

## 1. Check the connection and authorization

Before creating a scheduled task, perform a harmless read through the intended publishing route and verify an authenticated X account whose exact normalized handle is `ccfddl`. Prefer a suitable connected provider; an authorized authenticated X browser is an alternative when no suitable provider is available. For a provider, discover its tools and supported media/publication operations; do not guess them. For a browser route, inspect the actual signed-in profile and composer and verify that the scheduling environment can use that authenticated session. Never assume the current browser login will be available to a future task.

If the chosen route is unconnected, unauthenticated, or points at another account, prepare previews and report the precise blocker. Use the supported plugin or browser login setup flow. Respect cancelled login/setup requests and wait for the user to continue rather than automatically reopening them. Metricool is optional; do not require it or subscribe to a paid service without authorization. For Metricool, a connected plugin alone is insufficient: read brand settings and verify an actual connected X network. Do not guess the `info` JSON schema or media-file format for `createScheduledPost`; inspect current tool documentation and official provider documentation first. Do not request or store an API key or password in chat. Installing this skill does not connect X.

Default to `media_mode: link_preview`: submit the approved text with its one conference detail-page URL and no separate image attachment. Verify the URL, page canonical, sharing metadata, and referenced image anonymously before publication. A successful metadata check is not proof that X will display a preview. Buffer documentation has ambiguous long-post limitations; validate the actual account/provider publishing capability and report uncertain preview rendering. For an explicitly requested generated-card fallback only, apply the public-image gate in the source-and-publishing reference when using API media uploads.

Use the user's bounded authorization for this recurring campaign. Ask before expanding its audience, topic, account, or scope. Obtain any additional action-specific confirmations required by the platform or applicable policy. Do not publish a preview merely to test the connector.

## 2. Acquire a coherent current source

Use the verified canonical source: `https://github.com/ccfddl/ccf-deadlines`, directory `conference/`. Fetch the latest default-branch commit read-only and pin every YAML file to that same full 40-character SHA. Verify the source against official CFP/date pages whenever a record changes, an ambiguity appears, or a known conflict needs resolution.

Use the bundled snapshot command on a fresh, read-only checkout, or construct the same snapshot with authorized connector results. Do not edit the conference repository as a side effect of publication.

```bash
python3 <skill>/scripts/countdown.py snapshot --repo <fresh-read-only-source-checkout> --output <run>/snapshot.json
```

The snapshot stores `repository`, `commit`, `fetched_at_utc`, `complete_catalog`, and `files` (`path`, exact UTF-8 `content`, SHA256). When assembling with a connector, set `complete_catalog: true` only after confirming all conference YAML paths at that commit were retrieved. Sample subsets must have `complete_catalog: false` and remain previews. `snapshot` reads committed Git objects, never uncommitted working files.

Never convert `TBD`, historical patterns, website estimates, conference dates, decisions, rebuttals, or camera-ready dates into submission deadlines. Preserve source seconds. Resolve AoE as UTC−12, fixed UTC offsets explicitly, and IANA zones with date-specific DST. Reject incomplete dates and ambiguous/nonexistent local DST times. Interpret PT as America/Los_Angeles. Quarantine unknown timezone labels rather than guessing.

Apply only the explicitly evidenced, exact-fingerprint EDBT 2027 official clock correction in the config; recheck its official page before publication, retain the original value in the private manifest, and stop for review if the source fingerprint changes to an unrecognized instant. Do not silently publish the known-bad AoE value.

Keep the existing MLSys 2027 exact-clock quarantine until the conflicting official sources agree or the organizer resolves it. Report the discrepancy without selecting whichever time is convenient. Retain MLSys in the campaign scope for other verified editions.

## 3. Build and inspect

Use a current explicit UTC as-of time. Require Python 3.10+, PyYAML, Pillow, and Liberation Sans (Arial-compatible). Use the executor's existing packages or an authorized reputable package source; do not silently install from an unknown source.

```bash
python3 <skill>/scripts/countdown.py build \
  --snapshot <run>/snapshot.json --config <skill>/references/config.json \
  --as-of <current-UTC-ISO8601> --output <run>/posts --preview
```

For an actual publication run, omit `--preview` after all gates are satisfied. A non-preview build requires a complete catalog, confirmed editorial configuration, and a snapshot fetched within 15 minutes. Recheck latest source SHA immediately before sending; if it changed, regenerate the affected content before posting.

The following visual rules apply only to the optional generated-card fallback (`media_mode: generated_card`), which requires user authorization before replacing the default link-preview route. Inspect every fallback PNG with an image-view tool. Confirm legible text, no overlaps/clipping, correct category, approved heading and event labels, exact deadline and zone, branding, and no crossed-out footer elements. Keep as-of UTC and source SHA in the private manifest only; retain the canonical link in tweet text, not in the image. Adapt the live repository email reminder template (`worker/src/email_reminders.js`) for social cards: gray page, white bordered cards, brick-red reminder accent, Arial-compatible sans-serif typography, and countdown → event title → exact deadline hierarchy. Use exactly `NAME YEAR Abstract Deadline` for abstract events and `NAME YEAR Deadline` for paper events, retaining a meaningful round label. Do not display an `abstract closed` warning in tweet text, cards, or alt text; keep the factual flag in the private manifest only. Keep the card heading as `CCFDDL deadline reminders (AI)` or `CCFDDL deadline reminders (Data Systems)`, without the tweet-only publication date. Remove the in-image website CTA and the visible as-of/source footer; preserve top branding, REMINDER, DEADLINE NOTICE, and the good-luck/team closing. Use the final category-specific plain-text contract below for tweet wording and retain category names on the attached cards. Omit unsubscribe/settings controls and retain ccfddl.com in tweet text only. Preserve precise elapsed-time countdowns rather than copying email calendar-day arithmetic. Every countdown is a snapshot, not a live clock.

Inspect the manifest and each tweet. Honor the skipped-for-review list. Preserve round labels and distinguish abstract from paper. Keep the passed-abstract fact internally, but omit its public qualifier as requested. Such paper deadlines apply to already-registered submissions; do not claim a new submission is still possible. Keep `stage_selection: nearest` as the default: select the next future deadline per timeline round deterministically. When multiple stages are explicitly selected, support separate rows with `stage_selection: all_future`; do not change the campaign default merely because the wording changed. Preserve every selected stage and display every `abstract_deadline` as `abstract` in both text and card, even when the official site calls it registration. Keep the official term only in source provenance, never as a reg/registration display override.

Keep the full selected digest in the text (up to six rows). For the optional generated-card fallback, render only its first three rows in the card and add an ellipsis if additional eligible entries exist. Do not add an ellipsis when there are no additional entries. Preserve `events` (all text rows), `card_events` (visible image rows), and `card_has_more` separately in the manifest. Make alt text describe only the visible image rows and the ellipsis, without claiming all text rows are pictured. Keep the default digests concise. Treat the script's weighted-length count and 280-character advisory as editorial diagnostics, not a universal hard limit: the connected account may support Premium long posts. Check the actual provider/account capability. Keep the current approved six-row compact style within the verified account limit; if it does not fit, report the tradeoff instead of silently dropping CCF A entries or changing the requested format. The script counts the entire canonical detail-page URL as 23 characters, NFC-normalizes Unicode, and conservatively overcounts complex emoji. Never use a naive character count, silently truncate, or automatically split a digest into a thread. If the provider returns a text-too-long error, report the exact error and do not rewrite and retry without new authorization. Include alt text from the manifest when the selected route supports it.

### Final plain-text contract

Use exactly `CCFDDL deadline reminders (AI) · YYYY/MM/DD` as the AI first line and `CCFDDL deadline reminders (Data Systems) · YYYY/MM/DD` as the Data Systems first line, with no trailing colon. Resolve `YYYY/MM/DD` from the explicit as-of time in `America/Los_Angeles`, including daylight-saving changes; add the date to tweet text only, keeping the card heading unchanged. Render each selected event as `NAME'YY (stage, round N) · N days`, omitting `, round N` for a single-round conference. Omit `left` from day-based tweet countdowns (use `1 day` for singular). Keep card countdown wording unchanged. Use the existing hour/minute countdown for near-term deadlines. Put one blank line after the heading and one blank line before `see details: <first-selected-conference-detail-URL>`. Include only that one URL, never an additional homepage link. Follow it immediately on the next line with exactly `#conf_deadline #deadline #蓝v` for both categories; keep hashtags out of the image. Keep exact dates and timezones on the conference detail pages rather than repeating them in the compact tweet. Optional fallback cards retain their three visible rows. Use ordinary text with no Markdown bold or Unicode bold. Uniformly label `abstract_deadline` as `abstract` in the tweet and `NAME YEAR Abstract Deadline` in its matching card; do not relabel CVPR as reg or registration. Do not invent dates from examples. Omit `abstract closed` from all public output while retaining its private fact flag. Do not claim that new registrations or new submissions are still possible. The image retains the AI/Data Systems category.

### Detail-link and publication preflight

Resolve the first event **after** digest selection and ordering. Match the website generator's canonical route: `https://ccfddl.com/venues/{source-subject-lower}/{slug}-{full-year}/`, where the slug is the source conference title lowercased with runs of non-ASCII-alphanumeric characters replaced by hyphens and trimmed; use the edition ID slug only if the title slug is empty. Use the actual source `sub` (for example DB or MX), never the campaign name Data Systems. Do not hardcode the user's AAAI example.

Before every send, fetch that exact URL anonymously, require HTTP 200 and its matching canonical, confirm the page is for the intended edition, and inspect its Open Graph/Twitter metadata and referenced image. If unavailable, incorrect, or not deployed, pause and report; do not silently substitute another URL or an uploaded card. Inspect the provider composer when possible and distinguish metadata readiness from an actual X preview, which X controls and may omit.

Preserve all selected rows and the approved Data Systems wording. If the weighted length exceeds 280, the manifest marks `needs_publication_capability_validation: true`; verify that the actual provider and @ccfddl account accept the full single post before sending. Buffer long-post link-preview behavior is ambiguous, so do not promise an image from metadata alone. Never shorten, drop rows, move the URL, split posts, or switch media modes without authorization. If the full post is blocked, report the exact capability or provider error.

## 4. Publish idempotently

Use a stable, persistent campaign ledger shared by all runs, or equivalent provider-native durable idempotency. Do not use a temporary directory for live state. If durable state is unavailable, stop before sending.

Compute the publication day in America/Los_Angeles. Check both the ledger and provider's recent/scheduled posts for an existing @ccfddl digest for that day/category. Reconcile existing provider records before proceeding. Never create both a direct post and a separate provider-scheduled copy.

```bash
python3 <skill>/scripts/countdown.py ledger check --path <persistent-ledger> --day YYYY-MM-DD --category AI
python3 <skill>/scripts/countdown.py ledger reserve --path <persistent-ledger> --day YYYY-MM-DD --category AI --content-sha256 <manifest-hash>
```

Use the verified authenticated @ccfddl publishing route with the approved full text, one detail-page URL, and no PNG attachment in default link-preview mode. If the composer still contains an earlier image attachment, remove it before final inspection. Complete the detail-link and length preflight above before reserving. Only use generated-card upload/public hosting when the user explicitly selects that fallback; never silently replace a missing link preview with an attached card.

Reserve immediately before the single publication request; the reservation uses an exclusive file lock and atomic state replacement. Use the exact approved text and detail-page URL (or explicitly authorized fallback card and alt text). If an optional upload fails before any post request, determine the exact state without duplicate publication. If sending times out or returns an uncertain result, leave the entry pending, inspect the provider and X, and **do not resend automatically**. A pending reservation blocks additional sends. Reconcile manually only after establishing whether publication occurred.

After the provider confirms publication, independently read the post and verify the @ccfddl author, full text, detail-page URL, actual preview or its absence, and exact post ID before confirming the ledger:

```bash
python3 <skill>/scripts/countdown.py ledger confirm --path <persistent-ledger> --day YYYY-MM-DD --category AI --post-id <verified-numeric-id> --post-url https://x.com/ccfddl/status/<verified-numeric-id>
```

A queued/scheduled job is not a published tweet; retain its provider job ID in durable campaign state and confirm only after read-back. Report material blockers or conflicts and link verified published posts. Follow the user's notification preferences and avoid repetitive daily success messages.

## 5. Create or maintain the schedule

Only after the authenticated-route read succeeds, create a daily morning task with the user's supported scheduler. Preserve `America/Los_Angeles` in the schedule; use flexible timing around 08:00 local. The task must invoke this workflow, refresh source data, perform read-back and idempotency checks, and keep private state outside the public repository. Verify that the task is enabled and tied to the correct provider/account before claiming it is active. Do not create a second schedule if one already exists.

Maintain the reusable skill in the user's personal skill directory. When separately authorized for repository maintenance, mirror only the portable skill files to `.agents/skills/ccfddl-x-posts/` through the repository's normal review workflow. Keep the personal installed copy and repository copy aligned when updating behavior. Never commit generated posts, snapshots, private ledger state, credentials, or provider tokens.

## Validation

Run the deterministic test suite after changing dates, selection, rendering, or ledger logic:

```bash
python3 <skill>/scripts/test_countdown.py
```

Forward-test a new representative source snapshot, inspect the resolved detail URLs and any optional rendered cards, and exercise the uncertain-send/duplicate guard before enabling changed live behavior. Treat tests and preview creation as validation, never as proof that a post was sent or the schedule is active.
