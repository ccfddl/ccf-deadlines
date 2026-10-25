---
name: ccfddl-conference-update
description: Maintain ccfddl/ccf-deadlines with newly announced editions and published, extended, or corrected deadlines for active editions. Use for selective daily maintenance or specific conference updates; historical timing only gates official-source checks.
---

# ccfddl Conference Update

Maintain new editions and still-active editions of `ccfddl/ccf-deadlines`. Cover newly published, extended, and corrected **submission, abstract, rebuttal/author-response, and decision** deadlines, new rounds, and fields that were `TBD`. Also handle specific new-conference leads supplied by the user or repository issues, following the repository's inclusion and ranking conventions.

A future edition already being present does not mean an earlier edition is finished: it can still have open rounds, rebuttal, or decisions pending. Check the relevant active editions rather than only the maximum year. General historical cleanup and unrelated refactoring are outside this workflow. Use `ccfddl-pr-review` for reviewing existing PRs.

## Select work before browsing

For a specific conference or fresh official lead, inspect its YAML and go directly to that lead; do not wait for a historical search window or cache expiry.

For a daily sweep, read [references/daily-maintenance.md](references/daily-maintenance.md). Run the local shortlist helper before reading many YAML files or performing web searches. It checks local dates and history, applies a local-only check ledger, and prints a bounded due list. It neither fetches sources nor changes conference data. Process fresh signals and urgent/TBD milestones first; expand the queue when the user's scope requires it. Do not create scheduled jobs unless requested.

Historical cadence determines **when to look**, never **what to insert**. Use several editions when available; allow for biennial, shifted, and multi-round cycles. A clear early skip means `too early to check`, not `no new edition exists`. The helper's inferred checking windows are conservative hints that fresh evidence or known conference cadence can override.

## Inspect the edition and schema

Read the shortlisted conference's latest and active editions plus enough history to understand its track and round convention. Before editing, inspect `scripts/conference-yaml-schema.yml` and nearby entries. Preserve paths, indentation, key order, IDs, date format, timezone syntax, notes, and round representation.

The current timeline supports `deadline`, `abstract_deadline`, `rebuttal_deadline`, `decision_deadline`, and `comment`. The required `deadline` remains the submission deadline; do not replace it with a rebuttal or decision date. Add optional fields only when officially published and relevant to the tracked round. An absent optional field need not mean an undiscovered deadline exists. Represent unknown values only as permitted by the schema and existing conventions; do not invent a new format or broaden the schema as part of a routine update.

Before adding an edition, check whether its year/ID already exists. Update that entry when applicable. A partial new edition is acceptable only when established repository conventions permit it and the edition itself is officially announced. Never construct a future URL or copy facts from a previous year.

## Obtain current official evidence

Open the known official edition/CFP/important-dates URL first. Follow its relevant links; use a targeted conference/year/track search only when the known source is missing, stale, or insufficient. Prefer the conference, its official submission system linked by the conference, and its organizer or sponsor (for example ACM, IEEE, USENIX, or AAAI).

Secondary sources and issues are discovery leads. Aggregators, snippets, blogs, social posts, cached third-party pages, and AI summaries do not establish repository facts. A tool/network error or a blocked page is `source unavailable`, not proof that no announcement exists.

Confirm the precise name, edition/year, track, and round. Reused domains may show old dates. Distinguish main research papers from workshops, tutorials, demos, posters, artifact evaluation, industry, journal, and co-located tracks. A rebuttal window's opening is not its closing deadline; a notification/decision date is not another submission round. Preserve explicitly published windows or qualifications in `comment` when appropriate to repository conventions.

Verify all available relevant fields together: official URL, dates, location, submission and abstract deadlines, rebuttal and decision deadlines, timezone, rounds, and notes. Add only announced rounds; do not extrapolate a full annual schedule from Round 1. For extensions or corrections, replace the old value in the matching round and retain useful official qualifications in notes.

Treat timezone and precision as part of each deadline. Verify published time/zone from the current source, including AoE, offsets, DST, and 11:59 PM; never inherit the prior year's timezone as evidence. For a date-only announcement, a documented repository default (such as end of day or AoE, if the repository specifies it for that situation) may supply the representation. Identify it in the comment/PR as a repository convention rather than claiming the official source published that time/zone. Do not invent such a default from examples alone. If neither the source nor an applicable documented convention resolves the precision, keep it unknown and explain the published date in a comment when appropriate. Since `timezone` is edition-wide, explicitly verify any conversion needed for fields announced in different zones. Do not silently combine incompatible zones.

## Make a focused, verified PR

Search open PRs for the same conference, year, track, round, and fields before editing or creating a PR. In a daily sweep, retrieve a compact PR index once and recheck the specific candidate immediately before submission. If an open PR covers the same change, report `existing PR already covers it`; use the review workflow for an incorrect PR rather than opening a competing update unless requested.

Use **one conference per PR**. Multiple relevant fields/rounds for that conference can be updated together. Keep unrelated data cleanup, generated files, and the local maintenance ledger out of the diff. Inspect the full diff, validate YAML/schema, and run applicable repository checks.

Immediately before opening the PR, reopen the official source, verify every changed fact and its year/track/round/timezone, inspect the diff, and check again for a duplicate PR. Cached checks never replace this final verification. If current sources conflict or remain insufficient, leave unsupported facts out and report the blocker; prefer `TBD` or no change to speculation.

Use exactly `Update <ACRONYM> <YEAR>` as the PR title, for example `Update ICME 2027`, including when adding a new conference or edition. Do not append changed fields, rounds, or other change descriptions to the title; put those details in the body. The body should state the resulting change, direct official sources, and material round/timezone clarification. Follow repository policy on signatures. Proceed within the user's authorization; the skill adds no separate approval requirement.

Confirm that GitHub actually created the PR before reporting its number/link. Record conference, edition/rounds, changed fields, branch/head SHA, sources, and CI state if available. Do not claim running CI passed or that an open PR is merged.

## Record outcomes

For daily runs, persist the actual check outcome and next-check hint locally as described in the daily reference. Report useful changes/PRs and a compact count of remaining work; distinguish `already up to date`, `too early to check`, `cached — not due`, `checked — no announcement`, `checked — relevant information still TBD`, `update available`, `existing PR already covers it`, `PR created`, and `blocked — conflicting/insufficient/unavailable official sources`.

Do not report unvisited candidates as checked. Search selectively, verify current evidence, and update promptly when it supports a change.
