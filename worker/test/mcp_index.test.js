import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/index.js";

function rpcRequest(url, method, params = {}, headers = {}) {
  return new Request(url, {
    method: "POST",
    headers: { Host: new URL(url).host, "Content-Type": "application/json", Accept: "application/json, text/event-stream", ...headers },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
}

const initialize = {
  protocolVersion: "2025-11-25",
  capabilities: {},
  clientInfo: { name: "ccfddl-tests", version: "1.0.0" },
};

async function rpcResponse(response) {
  const body = await response.text();
  if (!response.headers.get("Content-Type")?.includes("text/event-stream")) return JSON.parse(body);
  const messages = body.split(/\r?\n\r?\n/).map((frame) => frame.split(/\r?\n/)
    .filter((line) => line.startsWith("data: ")).map((line) => line.slice(6)).join("\n"))
    .filter(Boolean).map((data) => JSON.parse(data));
  const result = messages.find((message) => message.id === 1);
  assert.ok(result, "Expected a JSON-RPC response in the SSE stream");
  return result;
}

test("serves API health and MCP initialization through the same Worker", async () => {
  const health = await worker.fetch(new Request("https://ccfddl.com/api/health"), {});
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { ok: true });
  for (const url of ["https://ccfddl.com/mcp", "http://localhost/mcp"]) {
    const response = await worker.fetch(rpcRequest(url, "initialize", initialize), {});
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
    const data = await rpcResponse(response);
    assert.equal(data.result.serverInfo.name, "ccfddl");
    assert.equal(data.result.serverInfo.version, "1.2.0");
  }
});

test("lists and calls MCP tools without a database or site login", async () => {
  const url = "https://ccfddl.com/mcp";
  const listed = await worker.fetch(rpcRequest(url, "tools/list"), {});
  assert.equal(listed.status, 200);
  assert.deepEqual((await rpcResponse(listed)).result.tools.map((tool) => tool.name).sort(), [
    "get_acceptance_rates", "get_conference", "get_filter_options", "search_conferences", "upcoming_deadlines",
  ]);
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (source) => {
    if (source === "https://ccfddl.com/conference/allconf.json") return Response.json([
      { title: "ICLR", sub: "AI", rank: { ccf: "A" }, confs: [{ year: 2027, id: "iclr27", timeline: [] }] },
    ]);
    assert.equal(source, "https://ccfddl.com/conference/allacc.json");
    return Response.json([{ title: "ICLR", accept_rates: [{ year: 2026, submitted: 100, accepted: 30, rate: 0.3 }] }]);
  };
  try {
    const search = await worker.fetch(rpcRequest(url, "tools/call", {
      name: "search_conferences", arguments: { query: "ICLR" },
    }), {});
    assert.equal(search.status, 200);
    const searchData = (await rpcResponse(search)).result;
    assert.equal(searchData.isError, undefined);
    assert.equal(searchData.structuredContent.total, 1);
    const rates = await worker.fetch(rpcRequest(url, "tools/call", {
      name: "get_acceptance_rates", arguments: { name_or_id: "ICLR", year: 2026 },
    }), {});
    assert.equal(rates.status, 200);
    const rateData = (await rpcResponse(rates)).result.structuredContent;
    assert.equal(rateData.status, "available");
    assert.equal(rateData.results[0].rate_percent, 30);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("serves domain verification on the primary domain", async () => {
  const challenge = "test-challenge";
  const url = "https://ccfddl.com/.well-known/openai-apps-challenge";
  const verified = await worker.fetch(new Request(url), {
    OPENAI_DOMAIN_VERIFICATION_TOKEN: challenge,
  });
  assert.equal(verified.status, 200);
  assert.equal(await verified.text(), challenge);
  const unconfigured = await worker.fetch(new Request(url), {});
  assert.equal(unconfigured.status, 404);
});

test("does not serve retired MCP paths", async () => {
  for (const path of ["/api/mcp", "/health"]) {
    const response = await worker.fetch(rpcRequest("https://ccfddl.com" + path, "initialize", initialize), {});
    assert.equal(response.status, 404);
  }
});

test("applies the shared rate limiter to MCP requests", async () => {
  const response = await worker.fetch(rpcRequest("https://ccfddl.com/mcp", "initialize", initialize, {
    "CF-Connecting-IP": "192.0.2.1",
  }), { API_RATE_LIMITER: { limit: async ({ key }) => {
    assert.equal(key, "192.0.2.1");
    return { success: false };
  } } });
  assert.equal(response.status, 429);
  assert.equal(response.headers.get("Retry-After"), "60");
});

test("rejects untrusted MCP hosts and origins", async () => {
  for (const [url, headers] of [
    ["https://untrusted.example/mcp", {}],
    ["https://mcp.ccfddl.com/mcp", {}],
    ["https://ccfddl.com/mcp", { Origin: "https://untrusted.example" }],
  ]) {
    const response = await worker.fetch(rpcRequest(url, "initialize", initialize, headers), {});
    assert.ok(response.status >= 400 && response.status < 500);
  }
});
