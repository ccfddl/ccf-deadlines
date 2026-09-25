---
name: ccfddl-conference-update
description: Add the latest conference edition or newly announced deadline information to ccfddl/ccf-deadlines. Use for proactive latest-edition maintenance, with historical timing only as a gate for when official-source checking is worthwhile.
---

# ccfddl Conference Update

Add newly available conference editions and newly announced deadline information to `ccfddl/ccf-deadlines`.

This skill is intentionally limited to maintaining the **latest conference edition**. It is not a general historical-data cleanup or PR-review workflow.

## Scope

Use this skill when asked to:

- check whether conferences need a new edition added
- maintain the latest conference deadlines
- find newly announced conference editions
- add newly published deadlines for the latest edition
- periodically update the repository with new conference-year information

Do not use this skill for:

- general historical-data cleanup
- arbitrary correction of old conference entries
- reviewing existing PRs
- broad repository refactoring
- speculative future deadlines

Use the `ccfddl-pr-review` skill for existing pull requests.

## Core strategy

For each conference under consideration:

1. inspect the latest edition currently tracked
2. inspect historical timing
3. estimate whether the next edition is likely to have announced relevant information yet
4. skip conferences that are clearly too early
5. search official sources only after the conference enters a reasonable announcement window
6. create an update only when current official information supports it

Historical timing controls **when to search**.

Official primary sources control **what to write**.

Never turn historical timing into factual repository data.

## Phase 1: Repository discovery

Determine:

- the latest edition currently tracked
- latest known submission round when applicable
- previous several editions when available
- historical submission months
- historical CFP or announcement timing
- historical conference months
- whether the conference is annual or follows another cadence

Prefer multiple historical editions when available rather than relying on one unusual year.

## Phase 2: Search gating

Before web research, estimate whether it is reasonably likely that the next edition has published relevant information.

Useful signals include:

- typical month when the next edition's website appears
- typical CFP publication month
- typical abstract/submission deadline month
- typical lead time between CFP publication and submission deadline
- typical conference month
- annual or multi-round cadence
- how recently the latest tracked edition occurred

Historical data is only a search-gating heuristic.

### Early-skip rule

If the next edition is clearly too early based on historical cadence, do not perform web research for that conference.

Classify it as:

`too early to check`

Examples:

- CFPs normally appear around December and it is currently May
- deadlines normally occur around March of the conference year and the next cycle is still far away
- the current edition has just taken place and historical next-edition announcements occur months later

This optimization does not assert that no next-edition page exists. It only means a current check is not justified yet.

### Conservative search window

Do not wait until the exact historical announcement date.

Start official-source checking once the conference enters a reasonable pre-announcement window, using a conservative lead buffer appropriate to that conference's historical cadence.

Do not apply one rigid global rule to every conference.

## Historical data must never become repository data

Historical dates may answer:

`Should we check now?`

They must never answer:

`What is the new deadline?`

Never derive or predict submission deadlines, abstract deadlines, timezones, conference dates, locations, rounds, or URLs from previous editions.

If previous deadlines cluster around a particular season, that can justify checking official sources around that season. It cannot justify inserting a guessed date.

## Phase 3: Official discovery

For conferences that pass the search gate, search current primary sources.

Preferred source order:

1. official conference website
2. official Call for Papers
3. official Important Dates page
4. official submission-system page linked by the conference
5. official ACM / IEEE / USENIX / AAAI / organizer page
6. official sponsoring-organization page

Secondary sources may be used only to locate the official source.

Do not treat deadline aggregators, search snippets, blogs, Reddit, social posts, cached third-party pages, prior repository entries, or AI summaries as authoritative evidence.

## Confirm the next edition

Before changing anything, verify that the official source refers to the exact next edition.

Confirm:

- conference name
- year
- edition if numbered
- relevant track
- relevant submission round

Be careful with sites that retain old content under a reused domain.

Do not confuse the main conference with workshops, tutorials, demos, posters, artifact evaluation, journal tracks, industry tracks, or co-located events.

## Determine whether an update is actionable

An update is actionable when current official information exists that should be represented in the repository.

Examples:

- the next conference edition is officially announced
- a submission deadline is published
- an abstract deadline is published
- a new submission round is published
- a previously TBD field now has an official value
- an official URL for the new edition is available

If the next-edition page exists but relevant information remains `TBD`, `TBA`, `To be announced`, `Coming soon`, or equivalent, do not guess.

Follow repository conventions for representing unknown information.

## Decide whether to add the edition

Do not require every possible field to be known if repository conventions permit partial or TBD entries.

However:

- every populated factual value must have current official support
- unknown values must remain unknown
- do not copy unknown values from a previous edition
- do not create a new edition solely from a historical prediction

Follow existing repository conventions for when a new conference year should first be added.

## Verify all available fields together

When adding or updating the latest edition, verify all relevant officially published fields together, including when applicable:

- conference year
- official URL
- conference dates
- location
- abstract deadline
- submission deadline
- timezone / AoE
- submission round
- relevant notes

This avoids multiple unnecessary PRs when one official page already provides all relevant information.

## Timezone rules

Treat timezone as part of the deadline.

Verify it directly from the current official source.

Never inherit timezone from the previous edition without current evidence.

Pay special attention to AoE, UTC, UTC offsets, local time, daylight-saving transitions, and 11:59 PM deadlines.

If the official source is ambiguous, do not invent precision.

## Multi-round conferences

For conferences with multiple rounds:

- identify which rounds the repository tracks
- follow the existing schema and convention
- add only officially announced rounds
- do not infer later rounds from prior years
- preserve TBD for announced-but-unpublished rounds when appropriate

Do not treat a newly announced Round 1 as evidence for a complete annual schedule.

## Existing edition check

Before editing, verify whether the repository already contains the same conference year.

Possible outcomes include:

- latest edition already present and current
- edition exists but new official fields are now available
- edition is missing
- repository intentionally tracks a different cycle or round structure

Do not add duplicate conference-year entries.

## Existing PR check

Before creating a PR, search open PRs for the same conference, year, round, and update.

If an open PR already covers the same change:

- do not create a duplicate
- classify the result as `existing PR already covers it`

If the existing PR is incorrect, use the PR-review workflow rather than opening a competing PR unless explicitly requested.

## Repository convention check

Before editing, inspect:

- nearby conference entries
- previous editions of the same conference
- recently merged PRs adding a new edition

Follow established conventions for:

- file location
- YAML schema
- indentation
- key ordering
- date formatting
- timezone syntax
- round representation
- URL format
- notes

Prefer repository consistency over inventing a new format.

## Change scope

Use one conference per PR.

A PR may update multiple fields or rounds belonging to the same conference edition.

Allowed:

`Add ICDE 2028 deadlines, conference dates, location, and official URL`

Not allowed:

`Add ICDE 2028 + SIGMOD 2028 + VLDB 2028`

Keep the diff focused and exclude unrelated cleanup.

## Branch and diff validation

Before opening a PR:

- inspect the final changed files
- inspect the complete diff
- confirm only the intended conference was changed
- verify YAML or metadata syntax
- run applicable repository validation when available
- ensure no unrelated or generated files were accidentally included

## Final official re-check

Immediately before creating the PR:

1. re-open the official source
2. verify the conference year
3. verify track and round
4. verify every populated changed field
5. verify timezone
6. inspect the final repository diff
7. check again for an existing open PR

If any factual field cannot be verified, do not guess it.

## Pull request

Use a focused title consistent with repository conventions, for example:

- `Add ICDE 2028`
- `Add ICDE 2028 deadlines`
- `Add SIGMOD 2028 Round 1`

The PR body should concisely state:

- what was added
- the official source
- relevant round or track clarification
- relevant timezone clarification when useful

Do not add a model-specific signature unless explicitly required by the current repository policy.

## After PR creation

Verify that GitHub actually created the PR.

Record:

- PR number
- conference
- year
- branch
- head SHA
- fields added or updated
- official source
- current CI state if available

Do not claim that the PR exists before GitHub confirms it, that CI is green while it is still running, or that the update is merged merely because a PR was created.

## Result states

Classify each conference considered using one of:

- `already up to date`
- `too early to check`
- `checked — no official next edition found`
- `checked — next edition exists but relevant information is still TBD`
- `new edition/update available`
- `existing PR already covers it`
- `PR created`
- `blocked by conflicting official sources`
- `blocked by insufficient official information`

Do not treat `too early to check` as equivalent to `no new edition exists`.

## Efficiency rules

Avoid unnecessary web research.

Prioritize conferences that are:

- near their historical CFP or deadline-announcement window
- missing an edition that would normally already be announced
- currently marked TBD during a period when dates are historically published soon
- multi-round conferences with another round approaching

Skip conferences whose next cycle is clearly far away.

## Maintenance standard

Search selectively.

Verify conservatively.

Update promptly once official information appears.

Never turn historical patterns into factual conference data.

Prefer `TBD` over speculation.

Prefer no PR over an unsupported PR.

Prefer one focused conference PR over a batch of unrelated updates.
