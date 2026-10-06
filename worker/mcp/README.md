# CCFDDL MCP plugin

This is a public, read-only MCP server for conference search, published deadlines and historical acceptance statistics. It runs inside the same `ccfddl-api` Cloudflare Worker as the site's API, at `https://ccfddl.com/mcp` using **Streamable HTTP**. It reads `https://ccfddl.com/conference/allconf.json` and `https://ccfddl.com/conference/allacc.json` with independent 15-minute in-isolate caches. MCP tools do not use D1 or site sessions.

Source files are under `worker/src/mcp/`, tests are under `worker/test/mcp_*.test.js`, and the portable plugin package is under `worker/mcp/plugin/ccfddl/`. The shared dependencies and deployment configuration are in `worker/package.json` and `worker/wrangler.jsonc`.

Tools:

- `get_filter_options`: subject codes with English/Chinese names, CCF/CORE/THCPL rankings, edition years, and supported event types.
- `search_conferences`: name, description, conference key, subject, CCF/CORE/THCPL rank, and edition year search, with the latest known acceptance statistics up to that edition year.
- `get_conference`: recent editions, known deadline nodes, explicitly published conference opening times, DBLP identifier, and historical acceptance statistics. Accepts a name, name plus year, edition ID, or returned conference key.
- `get_acceptance_rates`: historical acceptance rates, submitted and accepted paper counts, percentages and sources, filtered by statistical year or inclusive year range and paginated newest first.
- `upcoming_deadlines`: future nodes within a specified time window, filtered by ranking, subject, edition year, and node type, with the latest known historical acceptance statistics up to the edition year.

Search and upcoming results include `total`, `offset`, `limit`, and `next_offset`. Pass `next_offset` as the next request's `offset`; `null` means the final page. The default limit is 20 and the maximum is 50. Filters use the conference **edition year**, which can differ from the year of its submission deadline. Rank `N` selects unranked conferences, including entries without that ranking.

For namesakes such as FSE, `get_conference` returns `ambiguous: true` and candidate `matches` inside `conference`. Retry with a returned `conference_key` or a `category` instead of assuming the first result is correct. Named lookups return up to six editions by default; `edition_limit` can request up to 20.

`get_conference` and `upcoming_deadlines` accept `display_timezone` (an IANA name such as `Asia/Shanghai`). Responses retain the source `local_time`, `timezone`, and `utc_time`, and add `display_time` and `display_timezone` for known dates. Unknown dates have no converted instant.

For upcoming nodes, `deadline_types` accepts `abstract_deadline`, `deadline`, `rebuttal_deadline`, `decision_deadline`, and `opening`. The default includes the four submission/review types and excludes openings. Examples:

```json
{"days": 30, "category": "AI", "core_rank": "A*", "deadline_types": ["abstract_deadline", "deadline"], "display_timezone": "Asia/Shanghai"}
```

```json
{"days": 90, "year": 2027, "deadline_types": ["opening"], "limit": 50}
```

The server retains source timezone labels and supplies UTC instants where a date is known. `TBD`, missing openings, and invalid calendar dates are not converted or predicted. Each response includes the source dataset URL and fetch time. Conference links come from the source data.

## Acceptance statistics

`get_acceptance_rates` requires `name_or_id` and accepts `category`, `year`, `from_year`, `to_year`, `offset`, and `limit`. Here `year` refers to the **statistics year**, independently of whether the deadline catalog contains that edition. A name with a year or an edition ID selects its year; a conflicting explicit `year` returns no matching statistics. Ranges are inclusive and `from_year` must not exceed `to_year`.

```json
{"name_or_id": "ICLR", "from_year": 2022, "to_year": 2026, "limit": 20}
```

Each record contains `year`, `submitted`, `accepted`, `rate` (a fraction between 0 and 1), `rate_percent` (a percentage rounded to two decimal places), `label`, and `source` (the published record's provenance). A missing numeric rate is derived only from valid counts; labels are never parsed into numbers. Original labels, including the legacy `srt` field, are retained. Missing values remain `null`.

Responses distinguish `available`, `missing`, `ambiguous`, `unavailable`, and `not_found` statuses. A valid query with no statistics for its year returns `missing`. `ambiguous` can mean that the conference name needs disambiguation, or that a chosen conference cannot be safely associated with title-only statistics. If acceptance data has no key or subject metadata, it is joined by title only when that title identifies a single conference. This prevents FSE statistics from being attributed to the wrong conference. Contradictory source numbers are preserved and marked with `data_issues` (`accepted_exceeds_submitted` or `rate_disagrees_with_counts`); they must not be silently corrected or presented without that qualification.

Search and upcoming results add `acceptance_status` and a nullable `latest_acceptance_rate` with its own year and provenance. Conference details add `acceptance_rates` (the newest 10 historical records), `acceptance_rates_total`, and `acceptance_status`. Each edition has a nullable exact-year `acceptance_rate` and up to two `recent_acceptance_rates` from that year or earlier. The complete history is available through `get_acceptance_rates`. Historical statistics are not predictions for an upcoming edition or an individual paper.

Tools that read statistics include an `acceptance_data` envelope with the dataset `source`, `fetched_at`, and feed status. Acceptance data loads alongside conference data. If its source is unavailable and no cached snapshot exists, deadline queries still succeed, statistics are empty or `null`, and their status is `unavailable`. A cached snapshot can be served during an outage with its original fetch timestamp.

## Local verification

From `worker/`:

```bash
npm ci
npm run check
npm run dev
```

Use MCP Inspector with `http://localhost:8787/mcp`. Test `initialize`, `tools/list`, and each tool call, including empty results and timezone boundaries. `/api/health` checks the shared Worker; it does not check the data sources.

## Deployment

Deploy from `worker/` after the code and plugin metadata have been reviewed:

```bash
npm run deploy
```

This single command deploys the site's API, email scheduler, and MCP service together as `ccfddl-api`. Cloudflare must be authorized in the deployment environment. Verify `https://ccfddl.com/api/health`, then connect `https://ccfddl.com/mcp` and call a tool; no separate MCP deployment is needed.

When OpenAI provides a domain-verification challenge for `ccfddl.com`, save its exact token as the `ccfddl-api` Worker secret `OPENAI_DOMAIN_VERIFICATION_TOKEN` and redeploy. The Worker returns that token at `https://ccfddl.com/.well-known/openai-apps-challenge`. Do not place the token in Git.

## Public plugin submission

The portable plugin package is under `worker/mcp/plugin/ccfddl/`. After deployment, verify the public support, privacy, and terms pages, and review their wording with the publisher. From `worker/mcp/`, build the ZIP with:

```bash
mkdir -p dist
cd plugin
zip -r ../dist/ccfddl-plugin.zip ccfddl
```

Upload the ZIP in the OpenAI Platform Plugins portal, connect the MCP URL, complete domain verification, and run the tool scan. The manifest contains acceptance-history and missing-statistics cases alongside deadline queries. Record a demonstration video and add its URL in the portal. Select the verified publisher identity and review the public listing before submitting; approval and publishing are separate actions.

The manifest's publisher identity, privacy terms, and policy URLs must be confirmed by the account owner before public submission. The plugin does not include payment or user authentication.
