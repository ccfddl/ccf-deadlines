# Source and publication reference

## Canonical data

- Site: https://ccfddl.com; each digest ends with only its most-starred selected conference’s full detail URL and the hashtags
- Source: https://github.com/ccfddl/ccf-deadlines
- Schema: `scripts/conference-yaml-schema.yml`
- Per-conference files: `conference/<subject>/<slug>.yml`
- Generated website data: `https://ccfddl.com/conference/allconf.json`; useful for comparison, but its generated version is not atomically tied to a Git commit. Prefer pinned YAML snapshots for publication provenance.

Each YAML file contains an array of conference objects: `title`, `description`, `sub`, `rank.ccf`, `dblp`, and `confs`. Editions contain `year`, `id`, `link`, `timeline`, `timezone`, `date`, and `place`. Timeline items may contain `abstract_deadline`, `deadline`, `rebuttal_deadline`, `decision_deadline`, and `comment`. Select only the first two fields and exclude rows explicitly described as post-review commitments. Commitment deadlines are not fresh-paper submissions or extra submission rounds. Preserve all timeline rounds; do not assume the last round or one edition per title. The source file path plus edition ID, round, and deadline field is the stable identity because conference titles can collide.

Use CCF A and CCF B plus the exact explicit paths `conference/AI/iclr.yml` and `conference/MX/mlsys.yml`. ICLR is already CCF A at the initial verified source, but keep the requested scope exception. MLSys is CCF N/sub MX and maps to this campaign's Data Systems category.

Treat comments with non-submission wording conservatively and flag for review. Conference event date and place are contextual metadata, never a fallback deadline. Never infer a time from a date-only string. Preserve the repository’s exact values and timestamp precision when publishing; do not describe them as independently organizer-verified.

## Repository-exact publishing policy

The latest pinned default-branch repository is the publishing authority. Use its deadline fields, timezone, edition, and source subject unchanged for selection, text, optional cards and countdowns. The configuration records `publishing_source_policy: repository_exact`; legacy `official_deadline_overrides` and `quarantine_events` are not applied.

Use EDBT’s repository value rather than an independent official-page clock correction. Include MLSys whenever its repository record is eligible under the explicit MLSys scope exception; an outside-source clock conflict does not quarantine it. Preserve normal A/B + ICLR/MLSys scope, horizon, stage, round, expired/TBD and source-validation behavior.

External official discrepancies belong to a separate data-review task and may justify a separately authorized repository correction. They never authorize silently changing the publication catalog or timestamp. Do not edit conference YAML as part of a publication run.

## Scheduler and provider boundaries

The personal skill itself is not a scheduler or an X integration. Discover installed provider tools rather than inventing an endpoint. A suggested provider such as Metricool is not connected until a harmless account read succeeds. Verify exact X handle, platform, and usable full-text/link-post capability. Do not save credentials in the skill. For Metricool, `createScheduledPost` accepts `blogId`, `date`, `info` as a JSON string, and optional `mediaFiles`; these field names alone do not define the inner JSON or upload contract. Obtain the current schema through actual tool descriptions or official documentation. Keep each X digest a single post. Length counts are advisory because account capabilities vary; return an exact provider length error to the user rather than silently shortening or retrying.

Configure one daily schedule with America/Los_Angeles morning timing. The two category digests belong to the same run. A DST-safe IANA timezone is essential: fixed UTC scheduling would shift local posting time across DST.

Before posting, check both durable state and recent/provider-scheduled posts for the local day/category. After reserving, allow only one send attempt until the outcome is known. A successful media upload is not a successful post. A provider job ID is not an X post ID. Keep pending outcomes blocked until read-back resolves them.

Persist the exact source SHA, as-of UTC, selected source paths/deadlines, text/optional-card hash, provider job ID if relevant, and verified post ID/URL in private run state. Do not place runtime state in the portable skill or public repository.

## Portable files

Mirror `SKILL.md`, `agents/openai.yaml`, `scripts/countdown.py`, `scripts/test_countdown.py`, and the two reference files when authorized. Generated artifacts remain outside the skill. Dependencies are Python 3.10+, PyYAML, Pillow, Liberation Sans (Arial-compatible), and zoneinfo data. The deterministic script performs no network, credential, or X calls; live actions stay in the agent/provider workflow.

## Public star-count source and failure semantics

Use anonymous GET `https://ccfddl.com/api/bootstrap`, which returns HTTP 200 JSON `{user:null, counts:{editionID:nonnegativeInteger}, starred:[]}`. Verified implementation: `worker/src/index.js` bootstrap/starCounts reads every `conference_star_counts` row without pagination; anonymous counts can be cached for 300 seconds. Counter migrations delete zero-count rows, and the frontend uses zero for absent keys. These are website favorite counts by repository `confs[].id`, not series totals or GitHub repository stars.

Freeze one complete response for both digests with the `stars` command, recording actual UTC fetch time, exact body SHA256, source URL, HTTP status and completeness. Require `build --stars <file>`; snapshots older than 15 minutes, future-dated beyond one minute, modified, partial, malformed, wrong-source or unavailable fail closed. The converter must only receive a genuinely fetched HTTP-200 body; never invent counts or re-date an old body. Zero for absent IDs is valid only under this confirmed complete sparse API contract. It is never a network/error fallback.

After existing deadline selection (maximum six each), choose the selected edition with the greatest count and retain the entire deadline list in its original order. Stable ties, including all-zero ties, choose the earliest selected row; repeated rounds of the same edition share one count. Do not link an unselected conference even if its count is higher. Require a genuine repository edition ID. Record all selected counts and the winning edition/count in the manifest along with provenance. The repository remains the sole authority for deadline facts; this separate read-only public counter selects only the detail link.

## Single-link footer and default preview route

Default `media_mode` is `link_preview`: no PNG is generated or attached. Both AI and Data Systems use a maximum of six selected rows, with fewer rows when fewer are eligible. The footer is `see details: ` followed on the same line by the most-starred selected conference’s full canonical detail URL, followed immediately on the next line by `#ccfddl #conf_deadline #蓝v`. Omit the entire `see details: ccfddl.com` line and any second homepage link.

Choose the highest-starred edition among the already-selected rows, without changing their selection or order; break ties by existing row order. Match `scripts/generate_seo_pages.py`: `/venues/{sub.lower()}/{slugify(title) or slugify(edition.id)}-{year}/`, where slugify lowercases, replaces `[^a-z0-9]+` runs with hyphens and trims them. Use the source subject (DB, MX, etc.), never Data Systems. Verify HTTP 200, canonical, edition, sharing metadata and referenced image before publication.

X controls whether a preview appears. Metadata or a Buffer composer preview is not a guarantee. Do not invent hidden links or independent linkAttachment support. Count the one full URL as 23 weighted characters, with CJK hashtag weighting. Above 280, preserve all selected rows and require actual provider/account full-post capability validation.

Manifest `link_url`, `visible_detail_url` and `card_target_url` all identify the single posted conference URL. Do not retain a homepage `display_link`. Keep `requires_live_url_verification: true`, `link_preview_guaranteed: false`, and `preview_selection_guaranteed: false`. Offline build success is not a completed live preflight.

## Optional routes

- Direct X browser: verify the authenticated @ccfddl profile and composer, inspect the browser's actual scheduling support, and ensure future runs can access the same authorized session. Use secure login handoff when required. Do not claim a scheduled task can reuse a session without checking.
- Buffer web composer: use the verified @ccfddl X channel with the exact approved text and the single conference URL and hashtag footer. Do not upload a generated PNG in default link-preview mode. Inspect the composer and confirm no old image attachment remains. X constructs its own link preview at publication; a Buffer preview or metadata check is not proof of the final X rendering.
- Buffer API/MCP fallback: use only when this route and its media requirements are authorized and verified. Follow the official ChatGPT OAuth setup at https://support.buffer.com/en-us/articles/connecting-buffer-to-automation-tools-and-ai-assistants-MMoXpjDEEo: Buffer dashboard profile → Apps & Integrations → Integrations → ChatGPT. The official ChatGPT route uses OAuth and does not require a personal API key; never ask for a key in chat. The user must approve the actual access grant in the supported secure flow. Verify the Buffer connection and its exact @ccfddl X channel with a harmless read before scheduling. Check current plan and X/API support at https://buffer.com/pricing, https://support.buffer.com/en-us/articles/what-is-buffers-api-GtIYIQilz5, and https://developers.buffer.com/guides/posts-and-scheduling.html. Do not assume the free plan, OAuth connection, or X channel already exists. Keep credentials and tokens out of the skill and repository.
- Metricool: use only if the user selects an appropriate plan and connects X. A connected brand with no social network cannot publish. Never purchase a plan/add-on merely to make this workflow run.

## Optional generated-card API/MCP media gate

This gate applies only when the user explicitly selects the generated-card fallback, not the default URL-preview post. Buffer API/MCP requires attached media at a public URL; it does not accept a local PNG upload. Keep the URL reachable until the post publishes, including when queued for later. Source: https://support.buffer.com/en-us/articles/what-is-buffers-api-GtIYIQilz5, Native media uploads.

For the API/MCP fallback only, verify a separately authorized public hosting route for the final card before enabling that route or creating a post. An explicitly authorized generated-card web-composer fallback instead uses native local upload; it does not need an additional image host. Check anonymous retrieval returns the correct image and that its availability covers publication. Never expose a private Library file URL, temporary signed download URL, credentials, manifests, or ledger. Publish only the generated cards authorized for public use. If hosting is unavailable or unverified, block the image-post workflow and report the specific gap; do not downgrade to text-only or claim the connection is fully ready. Do not create another setup request merely to record this gate.

## Optional email-style generated-card fallback and tweet format

Use the repository's actual email reminder template as the visual and text reference: https://github.com/ccfddl/ccf-deadlines/blob/a8b906a1842d8ce1264d6ffa98feb12adf4d68ef/worker/src/email_reminders.js#L90-L153. Recheck the live template when maintaining this skill.

- Optional card heading: exactly `CCFDDL deadline reminders (AI)` or `CCFDDL deadline reminders (Data Systems)`, without the tweet-only date. Card entries: `NAME YEAR Abstract Deadline` or `NAME YEAR Deadline`, with a meaningful round label. Do not show an abstract-closed qualifier in public text, cards, or alt text; retain it only as an internal fact. Do not use a middle-dot Submission/Registration label.
- Final tweet format: first line exactly `CCFDDL daily reminders (AI) · YYYY/MM/DD` for AI or `CCFDDL daily reminders (Data Systems) · YYYY/MM/DD` for Data Systems, with no trailing colon and the date calculated from the as-of time in `America/Los_Angeles` (including daylight-saving changes); keep the card heading undated; one blank line after the heading; each event line `NAME'YY (stage, round N) · N days`; one blank line before `see details: ` followed on the same line by the most-starred selected conference’s full detail URL; follow it immediately with exactly `#ccfddl #conf_deadline #蓝v` on the next line for both categories. Omit the entire `see details: ccfddl.com` line and any second homepage link. Do not add hashtags to the image. Omit the round qualifier for a single round. Use ordinary unbolded text, with no Markdown or Unicode bold. Omit `left` from all tweet countdown units: use `1 day`/`N days`, `1 hour`/`N hours`, `1 min`/`N min`, or `<1 min`, preserving near-term hour/minute precision. Keep optional card countdown wording unchanged. For explicitly requested fallback cards, put exact dates/timezones on the first three image rows and add an ellipsis if further eligible rows exist; the full selected list stays in tweet text. Omit public abstract-closed wording and never claim new registration is still possible.
- Keep the default nearest stage per timeline round. Support explicitly selected multiple stages as separate rows by setting `stage_selection: all_future`; use `nearest` otherwise. Do not infer new dates from an example. Per the user's final label choice, every `abstract_deadline` uses `abstract` in text and `NAME YEAR Abstract Deadline` on cards, even if an official page calls it paper registration. Record that official wording only in provenance; do not introduce a display alias such as reg or registration.
- Card: #f2f2f2 page; white panel and event cards; #d44f3f masthead, top border, and countdown; #242933 event title; #5f6975 exact date; rounded #e7e2dd borders; Arial/Helvetica-style sans-serif. Use Liberation Sans as the deterministic metric-compatible font.
- Show `ccf-deadlines`, `REMINDER`, and `DEADLINE NOTICE`, with the template's submission good-luck footer. Omit email preferences and unsubscribe links from social output.
- Keep seconds and timezone semantics internally and show seconds on the card. Keep the exact UTC as-of and source SHA in the private manifest only. Remove the image website CTA, visible as-of timestamp, and source hash, as marked by the user. Preserve the masthead, REMINDER, DEADLINE NOTICE, heading, event rows, and good-luck/team closing. Do not replace true remaining-time counts with the email implementation's calendar-day differences.

## Tier coverage and compact capacity

Use up to six text rows per category and preserve all candidates when they fit. For the optional generated-card fallback, independently set `card_limit: 3`: show only the first three selected entries, with an ellipsis iff additional eligible entries exist. Keep full `events` and visible `card_events` separate; image alt text describes only the visible rows plus the continuation indication. If more than the category limit exist, select nearest deadlines while ensuring both CCF A and CCF B remain represented when eligible. Record total and omitted counts in the manifest; do not silently erase a tier. The currently approved AI example contains all six eligible conferences: AAMAS, COLING, NAACL, CVPR, ICAPS, and ACL. Do not hardcode their dates or keep this example list after the source changes. The approved category-specific compact text leaves exact dates/timezones on the website (and optional fallback card rows) and places a blank line after the header and before the website link.

## Verified Buffer X card-target limitation

The current Buffer X route exposes no independent linkAttachment/card-target input. Buffer documents separate link attachments for Facebook, LinkedIn, Threads and Bluesky, while X constructs its card from the posted URL and ignores the Buffer-generated preview. Do not use deprecated generic assets.link as proof of X support. Sources: https://developers.buffer.com/guides/integrations/mcp.html and https://support.buffer.com/en-us/articles/attaching-images-videos-and-other-media-to-your-posts-eudySt0TnS. The user now wants only the visible conference URL, so no independent-card-target capability is required. Verify and report actual preview rendering without promising an image will appear.
