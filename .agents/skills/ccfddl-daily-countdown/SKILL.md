---
name: ccfddl-daily-countdown
description: Prepare and, with a verified authenticated publishing route and authorization, publish daily conference-deadline countdown posts for @ccfddl on X/Twitter. Use for the recurring CCFDDL campaign, AI/Data Systems countdown text, website-style social cards, schedule setup, publication checks, or maintaining this workflow. Read the live CCFDDL source, include CCF A plus ICLR and MLSys, and link every digest to ccfddl.com.
---

# CCFDDL Daily Countdown

Create up to two English digests per publication day: one **AI**, one **Data Systems**, with concise countdown text, a matching readable PNG, and `https://ccfddl.com`.

## Campaign contract

- Use exactly the verified X account **@ccfddl**. Do not treat a display name, brand name, or workspace as account proof.
- Include CCF A conferences plus explicit ICLR and MLSys exceptions. Classify `sub: AI` as AI and **all remaining source subjects** as Data Systems. This is the requested campaign grouping, not a claim about the source taxonomy.
- Publish in the morning in **America/Los_Angeles**, with automatic daylight-saving changes. Prefer flexible scheduling around 08:00 local; do not impose an exact time unless requested.
- Use English as the stated operational default. Preserve later user changes in campaign configuration.
- Publish at most one digest per category per local calendar day. Choose the nearest future abstract or paper deadlines within the configured 120-day horizon, up to three rows. Skip empty categories.
- Include no unrelated posts, replies, DMs, follows, or engagement actions. Do not put credentials, account identifiers beyond the public handle, private state, or publication ledgers in the public source repository.
- Treat this skill as the workflow, not proof that a schedule or publishing connection exists. Never report live posting as enabled without verifying the actual provider and schedule.

Read [references/config.json](references/config.json) for editable campaign settings. Read [references/source-and-publishing.md](references/source-and-publishing.md) for source mapping, identity, conflict handling, provider checks, and state transitions.

## 1. Check the connection and authorization

Before creating a scheduled task, perform a harmless read through the intended publishing route and verify an authenticated X account whose exact normalized handle is `ccfddl`. Prefer a suitable connected provider; an authorized authenticated X browser is an alternative when no suitable provider is available. For a provider, discover its tools and supported media/publication operations; do not guess them. For a browser route, inspect the actual signed-in profile and composer and verify that the scheduling environment can use that authenticated session. Never assume the current browser login will be available to a future task.

If the chosen route is unconnected, unauthenticated, or points at another account, prepare previews and report the precise blocker. Use the supported plugin or browser login setup flow. Metricool is optional; do not require it or subscribe to a paid service without authorization. For Metricool, a connected plugin alone is insufficient: read brand settings and verify an actual connected X network. Do not guess the `info` JSON schema or media-file format for `createScheduledPost`; inspect current tool documentation and official provider documentation first. Do not request or store an API key or password in chat. Installing this skill does not connect X.

Use the user's bounded authorization for this recurring campaign. Ask before expanding its audience, topic, account, or scope. Obtain any additional action-specific confirmations required by the platform or applicable policy. Do not publish a preview merely to test the connector.

## 2. Acquire a coherent current source

Use the verified canonical source: `https://github.com/ccfddl/ccf-deadlines`, directory `conference/`. Fetch the latest default-branch commit read-only and pin every YAML file to that same full 40-character SHA. Verify the source against official CFP/date pages whenever a record changes, an ambiguity appears, or a known conflict needs resolution.

Use the bundled snapshot command on a fresh, read-only checkout, or construct the same snapshot with authorized connector results. Do not edit the conference repository as a side effect of publication.

```bash
python3 <skill>/scripts/countdown.py snapshot --repo <fresh-read-only-source-checkout> --output <run>/snapshot.json
```

The snapshot stores `repository`, `commit`, `fetched_at_utc`, `complete_catalog`, and `files` (`path`, exact UTF-8 `content`, SHA256). When assembling with a connector, set `complete_catalog: true` only after confirming all conference YAML paths at that commit were retrieved. Sample subsets must have `complete_catalog: false` and remain previews. `snapshot` reads committed Git objects, never uncommitted working files.

Never convert `TBD`, historical patterns, website estimates, conference dates, decisions, rebuttals, or camera-ready dates into submission deadlines. Preserve source seconds. Resolve AoE as UTC−12, fixed UTC offsets explicitly, and IANA zones with date-specific DST. Reject incomplete dates and ambiguous/nonexistent local DST times. Interpret PT as America/Los_Angeles. Quarantine unknown timezone labels rather than guessing.

Keep the existing MLSys 2027 exact-clock quarantine until the conflicting official sources agree or the organizer resolves it. Report the discrepancy without selecting whichever time is convenient. Retain MLSys in the campaign scope for other verified editions.

## 3. Build and inspect

Use a current explicit UTC as-of time. Require Python 3.10+, PyYAML, Pillow, and DejaVu Sans Mono. Use the executor's existing packages or an authorized reputable package source; do not silently install from an unknown source.

```bash
python3 <skill>/scripts/countdown.py build \
  --snapshot <run>/snapshot.json --config <skill>/references/config.json \
  --as-of <current-UTC-ISO8601> --output <run>/posts --preview
```

For an actual publication run, omit `--preview` after all gates are satisfied. A non-preview build requires a complete catalog, confirmed editorial configuration, and a snapshot fetched within 15 minutes. Recheck latest source SHA immediately before sending; if it changed, regenerate the affected content before posting.

Inspect every final PNG with an image-view tool. Confirm legible text, no overlaps/clipping, correct category, labels, exact deadline and zone, as-of UTC, source SHA, branding, and canonical link. Cards use CCFDDL's warm off-white background, monospace type, orange brand accent, and green/gold/red urgency colors. Every countdown is a snapshot, not a live clock.

Inspect the manifest and each tweet. Honor the skipped-for-review list. Preserve round labels, distinguish abstract from paper, and explicitly disclose when the abstract deadline has already passed. Such paper deadlines apply to already-registered submissions; do not claim a new submission is still possible. The next future deadline per timeline round is selected deterministically.

Use the same selected rows in the text and card. Keep the default digests concise. Treat the script's weighted-length count and 280-character advisory as editorial diagnostics, not a universal hard limit: the connected account may support Premium long posts. Check the actual provider/account capability. The script counts the canonical URL as 23 characters, NFC-normalizes Unicode, and conservatively overcounts complex emoji. Never use a naive character count, silently truncate, or automatically split a digest into a thread. If the provider returns a text-too-long error, report the exact error and do not rewrite and retry without new authorization. Include alt text from the manifest.

## 4. Publish idempotently

Use a stable, persistent campaign ledger shared by all runs, or equivalent provider-native durable idempotency. Do not use a temporary directory for live state. If durable state is unavailable, stop before sending.

Compute the publication day in America/Los_Angeles. Check both the ledger and provider's recent/scheduled posts for an existing @ccfddl digest for that day/category. Reconcile existing provider records before proceeding. Never create both a direct post and a separate provider-scheduled copy.

```bash
python3 <skill>/scripts/countdown.py ledger check --path <persistent-ledger> --day YYYY-MM-DD --category AI
python3 <skill>/scripts/countdown.py ledger reserve --path <persistent-ledger> --day YYYY-MM-DD --category AI --content-sha256 <manifest-hash>
```

Reserve immediately before the single publication request; the reservation uses an exclusive file lock and atomic state replacement. Use the exact approved text, card, and alt text. If upload fails before any post request, determine the exact state without duplicate publication. If sending times out or returns an uncertain result, leave the entry pending, inspect the provider and X, and **do not resend automatically**. A pending reservation blocks additional sends. Reconcile manually only after establishing whether publication occurred.

After the provider confirms publication, independently read the post and verify the @ccfddl author, text, image, and exact post ID before confirming the ledger:

```bash
python3 <skill>/scripts/countdown.py ledger confirm --path <persistent-ledger> --day YYYY-MM-DD --category AI --post-id <verified-numeric-id> --post-url https://x.com/ccfddl/status/<verified-numeric-id>
```

A queued/scheduled job is not a published tweet; retain its provider job ID in durable campaign state and confirm only after read-back. Report material blockers or conflicts and link verified published posts. Follow the user's notification preferences and avoid repetitive daily success messages.

## 5. Create or maintain the schedule

Only after the authenticated-route read succeeds, create a daily morning task with the user's supported scheduler. Preserve `America/Los_Angeles` in the schedule; use flexible timing around 08:00 local. The task must invoke this workflow, refresh source data, perform read-back and idempotency checks, and keep private state outside the public repository. Verify that the task is enabled and tied to the correct provider/account before claiming it is active. Do not create a second schedule if one already exists.

Maintain the reusable skill in the user's personal skill directory. When separately authorized for repository maintenance, mirror only the portable skill files to `.agents/skills/ccfddl-daily-countdown/` through the repository's normal review workflow. Keep the personal installed copy and repository copy aligned when updating behavior. Never commit generated posts, snapshots, private ledger state, credentials, or provider tokens.

## Validation

Run the deterministic test suite after changing dates, selection, rendering, or ledger logic:

```bash
python3 <skill>/scripts/test_countdown.py
```

Forward-test a new representative source snapshot, inspect the rendered cards, and exercise the uncertain-send/duplicate guard before enabling changed live behavior. Treat tests and preview creation as validation, never as proof that a post was sent or the schedule is active.
