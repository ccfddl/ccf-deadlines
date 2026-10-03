# Source and publication reference

## Canonical data

- Site and outbound link: https://ccfddl.com
- Source: https://github.com/ccfddl/ccf-deadlines
- Schema: `scripts/conference-yaml-schema.yml`
- Per-conference files: `conference/<subject>/<slug>.yml`
- Generated website data: `https://ccfddl.com/conference/allconf.json`; useful for comparison, but its generated version is not atomically tied to a Git commit. Prefer pinned YAML snapshots for publication provenance.

Each YAML file contains an array of conference objects: `title`, `description`, `sub`, `rank.ccf`, `dblp`, and `confs`. Editions contain `year`, `id`, `link`, `timeline`, `timezone`, `date`, and `place`. Timeline items may contain `abstract_deadline`, `deadline`, `rebuttal_deadline`, `decision_deadline`, and `comment`. Select only the first two fields. Preserve all timeline rounds; do not assume the last round or one edition per title. The source file path plus edition ID, round, and deadline field is the stable identity because conference titles can collide.

Use CCF A plus the exact explicit paths `conference/AI/iclr.yml` and `conference/MX/mlsys.yml`. ICLR is already CCF A at the initial verified source, but keep the requested override. MLSys is CCF N/sub MX and maps to this campaign's Data Systems category.

Treat comments with non-submission wording conservatively and flag for review. Conference event date and place are contextual metadata, never a fallback deadline. Never infer a time from a date-only string. Source values such as 23:59:00 can reflect repository convention; do not claim organizer-level second precision without checking the official page.

## Known conflict

As of 2026-10-03, MLSys 2027's official CFP lists October 30, 2026 at 20:00 UTC; the official Dates page and homepage show 12:00 PM PDT (19:00 UTC). The configured `mlsys27` quarantine prevents a misleading exact countdown. Revisit:

- https://mlsys.org/Conferences/2027/CallForResearchPapers
- https://mlsys.org/Conferences/2027/Dates

Do not remove the quarantine merely because the repository matches one side. Require organizer clarification or aligned authoritative pages, then refresh the source record and regenerate.

## Scheduler and provider boundaries

The personal skill itself is not a scheduler or an X integration. Discover installed provider tools rather than inventing an endpoint. A suggested provider such as Metricool is not connected until a harmless account read succeeds. Verify exact X handle, platform, and usable image-post capability. Do not save credentials in the skill. For Metricool, `createScheduledPost` accepts `blogId`, `date`, `info` as a JSON string, and optional `mediaFiles`; these field names alone do not define the inner JSON or upload contract. Obtain the current schema through actual tool descriptions or official documentation. Keep each X digest a single post. Length counts are advisory because account capabilities vary; return an exact provider length error to the user rather than silently shortening or retrying.

Configure one daily schedule with America/Los_Angeles morning timing. The two category digests belong to the same run. A DST-safe IANA timezone is essential: fixed UTC scheduling would shift local posting time across DST.

Before posting, check both durable state and recent/provider-scheduled posts for the local day/category. After reserving, allow only one send attempt until the outcome is known. A successful media upload is not a successful post. A provider job ID is not an X post ID. Keep pending outcomes blocked until read-back resolves them.

Persist the exact source SHA, as-of UTC, selected source paths/deadlines, text/card hash, provider job ID if relevant, and verified post ID/URL in private run state. Do not place runtime state in the portable skill or public repository.

## Portable files

Mirror `SKILL.md`, `agents/openai.yaml`, `scripts/countdown.py`, `scripts/test_countdown.py`, and the two reference files when authorized. Generated artifacts remain outside the skill. Dependencies are Python 3.10+, PyYAML, Pillow, Liberation Sans (Arial-compatible), and zoneinfo data. The deterministic script performs no network, credential, or X calls; live actions stay in the agent/provider workflow.

## Optional routes

- Direct X browser: verify the authenticated @ccfddl profile and composer, inspect the browser's actual scheduling support, and ensure future runs can access the same authorized session. Use secure login handoff when required. Do not claim a scheduled task can reuse a session without checking.
- Buffer: use as the user-selected preferred free route, once connected. Follow the official ChatGPT OAuth setup at https://support.buffer.com/en-us/articles/connecting-buffer-to-automation-tools-and-ai-assistants-MMoXpjDEEo: Buffer dashboard profile → Apps & Integrations → Integrations → ChatGPT. The official ChatGPT route uses OAuth and does not require a personal API key; never ask for a key in chat. The user must approve the actual access grant in the supported secure flow. Verify the Buffer connection and its exact @ccfddl X channel with a harmless read before scheduling. Check current plan and X/API support at https://buffer.com/pricing, https://support.buffer.com/en-us/articles/what-is-buffers-api-GtIYIQilz5, and https://developers.buffer.com/guides/posts-and-scheduling.html. Do not assume the free plan, OAuth connection, or X channel already exists. Keep credentials and tokens out of the skill and repository.
- Metricool: use only if the user selects an appropriate plan and connects X. A connected brand with no social network cannot publish. Never purchase a plan/add-on merely to make this workflow run.

## Buffer media gate

Buffer API/MCP requires media at a public URL; it does not accept a local PNG upload. Keep the URL reachable until the post publishes, including when queued for later. Source: https://support.buffer.com/en-us/articles/what-is-buffers-api-GtIYIQilz5, Native media uploads.

Verify an authorized public hosting route for the final card before enabling the campaign or creating a post. Check anonymous retrieval returns the correct image and that its availability covers publication. Never expose a private Library file URL, temporary signed download URL, credentials, manifests, or ledger. Publish only the generated cards authorized for public use. If hosting is unavailable or unverified, block the image-post workflow and report the specific gap; do not downgrade to text-only or claim the connection is fully ready. Do not create another setup request merely to record this gate.

## Email notification format

Use the repository's actual email reminder template as the visual and text reference: https://github.com/ccfddl/ccf-deadlines/blob/a8b906a1842d8ce1264d6ffa98feb12adf4d68ef/worker/src/email_reminders.js#L90-L153. Recheck the live template when maintaining this skill.

- Heading: `<category> Daily deadline reminders`.
- Text rows: `<remaining time> · <conference year round stage> · <YYYY/MM/DD HH:mm> (<source timezone>)`. Keep the canonical ccfddl.com link.
- Card: #f2f2f2 page; white panel and event cards; #d44f3f masthead, top border, and countdown; #242933 event title; #5f6975 exact date; rounded #e7e2dd borders; Arial/Helvetica-style sans-serif. Use Liberation Sans as the deterministic metric-compatible font.
- Show `ccf-deadlines`, `REMINDER`, and `DEADLINE NOTICE`, with the template's submission good-luck footer. Omit email preferences and unsubscribe links from social output.
- Keep seconds and timezone semantics internally and show seconds on the card. Keep the exact UTC as-of and source SHA in the social image footer. Do not replace true remaining-time counts with the email implementation's calendar-day differences.
