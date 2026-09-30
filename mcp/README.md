# CCFDDL MCP plugin

This is a public, read-only MCP server for conference search and published deadlines. It runs as a separate Cloudflare Worker at `https://mcp.ccfddl.com/mcp`. It reads `https://ccfddl.com/conference/allconf.json` with a 15-minute in-isolate cache and has no D1 binding.

Tools:

- `search_conferences`: name, CCF rank, and subject category search.
- `get_conference`: recent editions and known deadline nodes.
- `upcoming_deadlines`: future nodes within a specified time window.

The server retains source timezone labels and supplies UTC instants where a date is known. `TBD` is not converted or predicted. Each result includes the source dataset URL and fetch time. Conference links come from the source data.

## Local verification

From this directory:

```bash
npm install
npm test
npm run check
npm run dev
```

Use MCP Inspector with `http://localhost:8787/mcp`. Test `initialize`, `tools/list`, and each tool call, including empty results and timezone boundaries. The `/health` route only confirms the Worker is running; it does not check the data source.

## Deployment

Deploy after the code and plugin metadata have been reviewed:

```bash
npm run deploy
```

Wrangler config binds the separate `ccfddl-mcp` Worker to `mcp.ccfddl.com`. Cloudflare must be authorized in the deployment environment. Verify `https://mcp.ccfddl.com/health` and connect `https://mcp.ccfddl.com/mcp` with MCP Inspector and ChatGPT developer mode.

When OpenAI provides the domain-verification challenge, save its exact token as the Worker secret `OPENAI_DOMAIN_VERIFICATION_TOKEN` and redeploy. The Worker returns that token at `/.well-known/openai-apps-challenge`. Do not place the token in Git.

## Public plugin submission

The portable plugin package is under `plugin/ccfddl/`. After deployment, verify the public support, privacy, and terms pages, and review their wording with the publisher. Build the ZIP with:

```bash
mkdir -p dist
cd plugin/ccfddl
zip -r ../../dist/ccfddl-plugin.zip plugin.json mcp.json assets
```

Upload the ZIP in the OpenAI Platform Plugins portal, connect the MCP URL, complete domain verification, and run the tool scan. The manifest contains five positive and three negative review cases. Record a demonstration video and add its URL in the portal. Select the verified publisher identity and review the public listing before submitting; approval and publishing are separate actions.

The manifest's publisher identity, privacy terms, and policy URLs must be confirmed by the account owner before public submission. The plugin does not include payment or user authentication.
