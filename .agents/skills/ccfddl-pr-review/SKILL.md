---
name: ccfddl-pr-review
description: Review open, non-draft pull requests in ccfddl/ccf-deadlines. Use for PR review, re-review after new commits, conference-information approval decisions, comment-only reviews of other PR types, and CI/source verification.
---

# ccfddl PR Review

Review open pull requests in `ccfddl/ccf-deadlines` against the latest repository state, official conference sources, and CI results.

Apply the same review rules to every PR regardless of author identity, repository role, or permissions.

## Scope

Use this skill when asked to:

- review one or more pull requests
- continue reviewing open PRs
- check whether a PR is correct
- approve eligible conference-information-only PRs
- request changes on incorrect conference-information-only PRs
- comment on all other PR types for a human maintainer to approve
- re-review a PR after new commits

Skip closed PRs and draft PRs.

Do not proactively search the repository for new conference editions. Use the `ccfddl-conference-update` skill for that.

Do not manually merge a PR unless the current user request explicitly asks for a merge operation.

## PR type and permitted actions

Classify each PR from its complete current diff before choosing a review action. Apply this classification to the whole PR, not only its title, labels, author, or conference-related subset.

### Conference-information-only PRs

A PR is eligible for the existing full review workflow only when every change is a conference-information update, such as conference metadata, dates, deadlines, tracks, rounds, locations, official URLs, or directly associated data formatting.

For these PRs, retain all official-source verification, current-head CI, unresolved-thread, duplicate-action, and final race-check requirements below. Submit `APPROVE` only when all approval gates pass; use `REQUEST_CHANGES` for concrete correctness issues under the existing rules.

### All other PR types

For every other PR type, publish findings only through a `COMMENT` review or a normal PR comment. Never submit `APPROVE` or `REQUEST_CHANGES`, even when the changes look correct, CI is green, or a concrete defect is found. A human maintainer is responsible for approval.

This includes application code, UI, scripts, dependencies, build/CI configuration, automation, documentation, review rules or skills, and any mixed PR containing conference-information changes plus another type of change.

If the PR cannot be confidently classified as conference-information-only, use comment-only review. Mixed PRs remain comment-only unless the complete current diff is safely established to contain only conference-information changes.

Continue reviewing the complete current diff, existing discussion, relevant conventions, and exact-head CI. Independently verify any changed conference facts even in a mixed PR. Clearly describe findings and verification limits in the comment, without converting them into a formal approval or change request.

## Review invariants

A review decision is valid only for the exact PR head SHA that was inspected.

Never approve from:

- an older head SHA
- an earlier conversation
- cached PR state
- a previous CI result
- the PR description alone

For every review attempt, re-read the current PR state.

Treat the review identity as:

`repository + PR number + head SHA`

## Required state

Before making a decision, retrieve and inspect:

- PR number, title, author, state, and draft status
- base branch
- latest head SHA
- complete changed-file list
- complete diff
- existing reviews
- review comments and discussion
- unresolved review threads when available
- latest CI/check status for the current head SHA
- relevant repository conventions

## Review procedure

### 1. Capture the current head SHA

Read the head SHA before reviewing anything else.

If the head SHA changes during review, discard the old decision and restart against the new SHA.

### 2. Read the complete diff

Inspect the entire diff, not only lines mentioned by previous reviewers.

Check for:

- incorrect conference information
- wrong year, edition, track, or submission round
- abstract/submission deadline confusion
- timezone errors
- wrong conference dates or location
- outdated or incorrect URLs
- malformed YAML or metadata
- formatting inconsistent with nearby entries
- duplicate entries
- accidental deletion
- unrelated changes
- stale values copied from older editions

### 3. Read existing review context

Inspect:

- submitted reviews
- review comments
- unresolved threads
- author replies
- previous requested changes

Confirm that previously reported issues are actually fixed in the current head SHA.

A resolved GitHub conversation does not by itself prove that the underlying issue was fixed.

Do not repeat an equivalent review or comment for the same head SHA unless materially new information changes the conclusion.

## Official conference verification

For every conference-related factual change, independently verify the relevant fields using current primary sources.

Preferred source order:

1. official conference website
2. official Call for Papers
3. official Important Dates page
4. official submission-system page linked by the conference
5. official ACM / IEEE / USENIX / AAAI / organizer page
6. official sponsoring-organization page

Secondary sources may be used only to locate primary sources.

Do not use deadline aggregators, blogs, Reddit, social posts, search snippets, AI summaries, cached third-party pages, or previous-year repository values as final evidence when a primary source is available.

## Fields to verify

Verify every changed field that is relevant to the PR, including when applicable:

- conference name
- year and edition
- track
- submission round
- abstract deadline
- paper submission deadline
- timezone / AoE
- notification date
- rebuttal period
- camera-ready date
- conference start/end dates
- location
- official conference URL
- CFP URL
- submission URL
- notes or round-specific metadata

Do not verify only the field mentioned in the PR title.

## Edition, track, and round disambiguation

Before accepting an official source, confirm that it refers to the exact conference, year, track, and round.

Be especially careful not to confuse:

- main conference vs workshop
- research track vs demo/poster/industry track
- journal-first track
- artifact evaluation
- previous-year archived pages
- Round 1 vs later rounds
- abstract deadline vs full-paper deadline

If the source cannot be tied confidently to the changed repository entry, do not approve.

## Deadline and timezone rules

A deadline is correct only when all relevant dimensions match:

- date
- time
- timezone
- track
- round

Treat timezone as part of the deadline.

Pay particular attention to AoE, UTC, UTC offsets, local timezones, daylight-saving transitions, 11:59 PM, and midnight boundaries.

Do not infer a timezone from previous editions.

### Deadline precision and representation

Apply these repository conventions after verifying the official deadline date and any stated time and timezone:

- When an official source states `23:59` (or `11:59 PM`) without seconds, represent it as `23:59:59`, not `23:59:00`.
- When the official source explicitly includes seconds, preserve those seconds exactly. For example, `23:59:00` remains `23:59:00`, and `23:59:30` remains `23:59:30`.
- Preserve all other explicitly stated times under the existing repository conventions. Do not round them up to the end of a minute or day.
- For an officially published date with no time, retain the existing end-of-day default of `23:59:59`.
- If the official source provides no timezone, retain the existing `AoE` default. An explicitly stated timezone takes precedence and must be preserved or converted only as required by repository conventions.
- These representation defaults do not authorize inventing an unpublished date or replacing `TBD` / `TBA`.

Do not flag a verified official `23:59` deadline represented as `23:59:59` as a seconds mismatch. Apply the same normalization consistently in review findings and proposed corrections.

Do not otherwise reinterpret an official deadline unless repository conventions explicitly require a representation conversion.

## TBD and unpublished information

Never infer an unpublished deadline.

If the official source says `TBD`, `TBA`, `To be announced`, `Coming soon`, or equivalent, preserve the repository's established representation of unknown information.

Do not fill an unknown field using last year's date, historical cadence, another deadline site, or an inferred annual pattern.

## Conflicting official sources

If official sources disagree:

1. identify exactly which values conflict
2. determine whether the pages refer to different rounds, tracks, or editions
3. check whether one page is clearly archived or stale
4. prefer a more specific/current official page only when that conclusion is well supported

If the conflict cannot be resolved confidently, hold the PR.

## CI verification

CI must correspond to the current head SHA.

Approve only when all required checks have completed successfully.

Do not approve if a required check is failed, cancelled, timed out, pending, queued, running, missing, or associated only with an older SHA.

Do not treat optional informational jobs as required unless repository protection or rules make them required.

When CI state is ambiguous, hold the PR.

## Decision rules

### APPROVE

Submit `APPROVE` only when all of the following are true:

- the entire PR is confidently classified as conference-information-only
- the complete current diff was reviewed
- relevant official information was independently verified
- all changed factual fields are correct
- repository formatting and conventions are respected
- no blocking issue remains
- no unresolved blocking review thread remains
- all required CI/checks for the current head SHA are green

Review body:

`LGTM (reviewed by <model-name>)`

Replace `<model-name>` with the actual model that performed that specific review. Never hardcode a model name in this skill.

### REQUEST_CHANGES

Use `REQUEST_CHANGES` only for a conference-information-only PR when a concrete correctness issue requires modification before acceptance. For all other or mixed PR types, describe the issue in a `COMMENT` review or normal PR comment instead.

The review must begin with:

`@<submitter-github-username>`

State precisely:

- affected file
- affected conference
- affected field
- current problematic value
- required correction
- official evidence

End with:

`Reviewed by <model-name>`

Use the actual model that performed that review.

Prefer actionable wording. Do not use vague blocking feedback when the exact issue can be identified.

### COMMENT

Use a `COMMENT` review or normal PR comment for every PR that is not confidently conference-information-only, including mixed PRs. Report concrete defects, optional suggestions, and verification limits through comments only; leave approval to a human maintainer.

For conference-information-only PRs, use a normal non-blocking comment when the issue is optional or stylistic and does not justify blocking an otherwise correct PR.

If the comment asks the submitter to take action, begin with:

`@<submitter-github-username>`

### HOLD

Do not approve or request speculative changes when:

- CI is still running
- required checks are missing
- official information cannot be verified
- official sources conflict
- the relevant official page is unavailable
- the correct track or round cannot be determined
- the head SHA changed during review

Report the blocking condition instead.

## Duplicate action prevention

Before submitting a GitHub review or comment, inspect actions already made for the current head SHA.

Do not duplicate an equivalent `APPROVE`, `REQUEST_CHANGES`, blocking comment, or non-blocking comment for the same issue and same SHA.

If a new commit changes the head SHA, perform the complete review workflow again.

Do not automatically carry approval forward from an older SHA.

## Final race check

Immediately before writing any review action to GitHub:

1. fetch the current head SHA again
2. compare it with the reviewed SHA
3. if they differ, do not submit the stale review and restart against the new SHA
4. confirm that the action is permitted for the reviewed PR type; non-conference and mixed PRs allow comments only

After submitting a review, verify that GitHub actually accepted it.

## Reporting

Always distinguish between a review decision and an action actually written to GitHub.

Examples of decisions:

- `PR is eligible for approval.`
- `PR requires changes.`
- `PR is blocked by pending CI.`
- `PR is blocked by conflicting official sources.`

Examples of confirmed actions:

- `APPROVE successfully submitted.`
- `REQUEST_CHANGES successfully submitted.`
- `Comment successfully posted.`

Never report an action as completed unless GitHub confirms success.

If GitHub rejects the action, report the review conclusion, attempted action, actual GitHub state, and the error or restriction encountered.

## Conservative default

When evidence is incomplete, do not approve.

When a conference-information-only PR is correct, verified, and passes every approval gate, approve it without inventing additional requirements.

For every other or uncertain PR type, comment only and leave approval to a human maintainer.

Correctness and source verification take precedence over review throughput.
