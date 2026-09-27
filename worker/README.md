# CCFDDL API

This Cloudflare Worker handles GitHub sign-in, per-edition conference favorites, and the public message wall. The static site calls it through the same-origin `/api/*` route.

## 1. Create the GitHub OAuth app

Create an OAuth app in GitHub with:

- Homepage URL: `https://ccfddl.com`
- Authorization callback URL: `https://ccfddl.com/api/auth/github/callback`
- Application logo: upload [`assets/ccfddl-oauth-logo.png`](assets/ccfddl-oauth-logo.png)

No OAuth scope is requested. The Worker only reads the signed-in user's public GitHub identity and does not store the GitHub access token.

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

## 4. Deploy

The `ccfddl.com` DNS record must be proxied through Cloudflare so the Worker route can intercept `/api/*` while GitHub Pages continues to serve every other path.

```bash
npm test
npm run deploy
```

After deployment, verify `https://ccfddl.com/api/health` returns `{"ok":true}` before publishing the static frontend changes.

When a new migration is added, apply the migration before deploying the Worker version that uses it. The message wall requires migrations `0002` through `0005`.

## Message wall

- Anyone can read the latest 50 messages; signed-in users can page through all older messages.
- A GitHub sign-in is required to post and to delete a message.
- Users can only delete their own messages.
- Signed-in users can like any message, including their own. The most-liked view ranks messages posted in the last 30 days.
- Signed-in users can reply to top-level messages; replies are loaded in pages and support likes.
- Messages are limited to 500 characters and eight lines.
- Each account can post up to 10 messages per UTC day and must wait 30 seconds between messages.

## Stored data

D1 stores the GitHub numeric user ID, login, avatar/profile URLs, hashed site sessions, one row per user/conference-edition favorite, message wall content, likes, and timestamps. Each edition uses its existing unique conference `id`, such as `iclr27`, so different years have independent totals.
