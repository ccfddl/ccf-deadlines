# CCFDDL API

This Cloudflare Worker handles GitHub sign-in, per-edition conference favorites, and the public message wall. The static site calls it through the same-origin `/api/*` route. It also redirects existing `/conference/deadlines_*` calendar and RSS subscriptions to `/conference/deadlines/`.

## 1. Create the GitHub OAuth app

Create an OAuth app in GitHub with:

- Homepage URL: `https://ccfddl.com`
- Authorization callback URL: `https://ccfddl.com/api/auth/github/callback`
- Application logo: upload [`assets/ccfddl-oauth-logo.png`](assets/ccfddl-oauth-logo.png)

Normal sign-in requests no OAuth scope. When a signed-in user explicitly enables email reminders, a separate GitHub authorization requests `user:email` to read their verified primary email address. The Worker does not store the GitHub access token.

GitHub setup references: [creating an OAuth app](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app) and [the web application flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#web-application-flow).

## 2. Create and migrate D1

```bash
cd worker
npm install
npx wrangler login
npx wrangler d1 create ccfddl
```

Copy the returned database ID into `wrangler.jsonc`, then run:

```bash
npm run db:migrate:remote
```

Cloudflare references: [D1 setup and bindings](https://developers.cloudflare.com/d1/get-started/) and [D1 migrations](https://developers.cloudflare.com/d1/reference/migrations/).

## 3. Configure secrets

```bash
npx wrangler secret put GITHUB_CLIENT_ID
npx wrangler secret put GITHUB_CLIENT_SECRET
npx wrangler secret put SESSION_SECRET
```

Use a cryptographically random value of at least 32 bytes for `SESSION_SECRET`.

To enable email reminders, verify a sending domain with [Resend](https://resend.com/domains) and configure:

```bash
npx wrangler secret put RESEND_API_KEY
npx wrangler secret put EMAIL_FROM
```

`EMAIL_FROM` is a verified sender, for example `CCFDDL <reminders@ccfddl.com>`. Keep both values in Worker secrets, not in the repository.

## 4. Deploy

The `ccfddl.com` DNS record must be proxied through Cloudflare so the Worker route can intercept `/api/*` while GitHub Pages continues to serve every other path.

```bash
npm test
npm run deploy
```

After deployment, verify `https://ccfddl.com/api/health` returns `{"ok":true}` before publishing the static frontend changes.

When a new migration is added, apply the migration before deploying the Worker version that uses it. The message wall requires migrations `0002` through `0006`. Migration `0006` enforces posting limits atomically in D1; deploy it before this Worker version to keep message posting working. It preserves existing daily quotas in a separate counter, avoiding double-counting while the previous Worker is still running. Email reminders require migrations `0007` and `0008`; migration `0008` adds the optional daily mode, off by default for existing users. Migration `0009` backfills favorite counts and keeps them current with database triggers; apply it before deploying the Worker that queries `conference_star_counts`. Migration `0010` indexes email send dates for daily retention cleanup. Deploy the static site with `/conference/deadline_events.json` before enabling the sender secrets and deploying this Worker version.

## Security configuration

- All cookie-authenticated writes require an `Origin` matching `PUBLIC_ORIGIN`; cross-site fetch metadata is rejected. CLI clients must also send this header.
- OAuth state is signed and expires after 10 minutes on the server. PKCE remains enabled. Login return paths reject backslashes and control characters.
- Sessions use random, hashed tokens and HttpOnly cookies with Secure and the `__Host-` prefix on HTTPS, preventing subdomain cookie injection. Local HTTP development uses unprefixed cookies. Existing users will need to sign in once after this cookie-name update. Expired sessions are removed during login; each account keeps at most 20 sessions.
- JSON bodies are limited to 8 KiB while streaming. Messages retain their 500-character limit and are displayed as plain text.
- Rate-limit bindings in `wrangler.jsonc` allow 10,000 API requests per minute per IP, 300 OAuth requests per minute per IP, and 600 authenticated writes per minute per account. The generous API limit allows shared networks; adjust the namespaces if they already belong to another Worker in your Cloudflare account. These edge limits apply per Cloudflare location, while the message quota is enforced globally in D1.
- The database trigger enforces 10 posts per UTC day and a 30-second cooldown, including replies. Deleting a message cannot reset either limit. A failed insert does not consume quota.
- API responses include `nosniff`, a restrictive CSP, and a no-referrer policy. Operational failures return a generic error rather than sensitive details.

The rate-limit bindings are deployed with the Worker configuration. No extra secret is required. See the [Cloudflare rate-limit binding documentation](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/).

Worker logs are enabled in `wrangler.jsonc`. After deployment, view diagnostic logs in Workers & Pages → ccfddl-api → Observability. Automatic invocation logs are disabled to avoid storing OAuth callback URLs containing authorization codes. Login failures include a safe stage-specific `code` in the JSON response; logs omit codes, tokens, cookies, secrets, and raw upstream error messages.

To test migration and concurrency behavior locally:

```bash
python -m unittest discover -s ../scripts -p 'test_*.py'
npm test
```

## Message wall

- Anyone can read the latest 50 messages; signed-in users can page through all older messages.
- A GitHub sign-in is required to post and to delete a message.
- Users can only delete their own messages.
- Signed-in users can like any message, including their own. The most-liked view ranks messages posted in the last 30 days.
- Signed-in users can reply to top-level messages; replies are loaded in pages and support likes.
- Messages are limited to 500 characters and eight lines.
- Each account can post up to 10 messages per UTC day and must wait 30 seconds between messages.

## Favorites calendar subscription

Favorite totals are read from `conference_star_counts`, maintained by triggers on `conference_stars`. Guest requests use a five-minute edge cache to avoid reading D1 on every page load and can show totals up to five minutes old. Signed-in requests read fresh totals from D1, as well as the user's own favorite state.

Signed-in users can select up to 100 starred conference editions from **Batch Subscribe** in the account menu. The resulting public `webcal://`/HTTPS link contains only the selected edition IDs and can be added once to a calendar app. The Worker filters the static `/conference/deadlines/deadlines_en.ics` or `deadlines_zh.ics` feed when the calendar app refreshes; the deployment workflow regenerates those files from conference YAML. No new D1 migration or secret is needed. Anyone with a subscription link can see its selected conference IDs. To change the selection, copy a new link and replace the old subscription.

Deploy the static site with the updated calendar generator before enabling this Worker endpoint: new calendar events carry an `X-CCFDDL-ID` field that the Worker uses to select editions. In conference details, Google Calendar provides a direct event link for each known deadline, while iCloud Calendar downloads a one-time ICS containing all known deadlines for that edition. Only the batch link is a refreshing feed. Google Calendar requires adding the subscription HTTPS link from **Other calendars → From URL** on a computer; iCloud/Apple Calendar can open the batch `webcal://` link directly.

## Email reminders

The account menu offers an optional **Email Reminders** setting. Enabling it starts a separate GitHub OAuth authorization for `user:email`. The Worker reads the verified primary address from GitHub, stores that address and the chosen time zone/language in D1, and discards the access token. Users can change the time zone/language, reauthorize to refresh the address, toggle daily reminders, or turn reminders off. Every email also includes a signed unsubscribe link.

The static deployment generates `/conference/deadline_events.json` from the same English ICS calendar used for subscriptions. A Cron Trigger runs every 15 minutes in UTC and sends at most one combined email per user's local date at or shortly after 09:00. By default, it includes starred-conference deadlines 7 or 1 local calendar days away. With daily reminders enabled, it instead includes every future deadline from starred conferences, and sends on each day that at least one future deadline remains. D1 records each daily send, and Resend receives an idempotency key so a retry cannot intentionally send a duplicate. If the sender secrets are absent, the job skips sending and the UI reports reminders unavailable. Monitor Worker logs for delivery errors and the [Resend dashboard](https://resend.com/emails) for accepted messages. Sender quota and verified-domain limits depend on the Resend account plan.

At 00:00 UTC each day, the Cron Trigger deletes `email_digest_sends` rows whose local date is more than seven days old, including any stale pending payloads. Recent rows preserve same-day retry and duplicate protection while limiting retained email content.

## Stored data

D1 stores the GitHub numeric user ID, login, avatar/profile URLs, hashed site sessions, one row per user/conference-edition favorite, message wall content, likes, and timestamps. Email reminders additionally store the verified primary email, chosen time zone/language, daily-mode setting, and recent send records for about seven days. Each edition uses its existing unique conference `id`, such as `iclr27`, so different years have independent totals.
