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
  const originalNow = Date.now;
  const initialTime = Date.parse("2027-01-01T00:00:00Z");
  let now = initialTime;
  let catalogOffline = false;
  let acceptanceOffline = true;
  Date.now = () => now;
  globalThis.fetch = async (source) => {
    if (source === "https://ccfddl.com/conference/allconf.json" && catalogOffline) return new Response("offline", { status: 503 });
    if (source === "https://ccfddl.com/conference/allconf.json") return Response.json([
      { title: "ICLR", sub: "AI", rank: { ccf: "A" }, confs: [{ year: 2027, id: "iclr27", timezone: "UTC",
        date: "May 1-3, 2027 (To be confirmed)", opening: "2027-05-01 08:00:00",
        opening_is_derived: true, timeline: [] }] },
    ]);
    assert.equal(source, "https://ccfddl.com/conference/allacc.json");
    if (acceptanceOffline) return new Response("offline", { status: 503 });
    return Response.json([{ title: "ICLR", accept_rates: [{ year: 2026, submitted: 100, accepted: 30, rate: 0.3 }] }]);
  };
  try {
    const unavailable = await worker.fetch(rpcRequest(url, "tools/call", {
      name: "search_conferences", arguments: { query: "ICLR" },
    }), {});
    const unavailableData = (await rpcResponse(unavailable)).result.structuredContent;
    assert.equal(unavailableData.stale, false);
    assert.equal(unavailableData.acceptance_data.status, "unavailable");
    assert.equal(unavailableData.acceptance_data.stale, null);
    acceptanceOffline = false;
    const search = await worker.fetch(rpcRequest(url, "tools/call", {
      name: "search_conferences", arguments: { query: "ICLR" },
    }), {});
    assert.equal(search.status, 200);
    const searchData = (await rpcResponse(search)).result;
    assert.equal(searchData.isError, undefined);
    assert.equal(searchData.structuredContent.total, 1);
    assert.equal(searchData.structuredContent.results[0].series_url, "https://ccfddl.com/venues/ai/iclr/");
    assert.equal(searchData.structuredContent.results[0].venue_url, "https://ccfddl.com/venues/ai/iclr-2027/");
    const details = await worker.fetch(rpcRequest(url, "tools/call", {
      name: "get_conference", arguments: { name_or_id: "ICLR 2027" },
    }), {});
    const detailData = (await rpcResponse(details)).result;
    assert.equal(detailData.isError, undefined);
    assert.equal(detailData.structuredContent.conference.series_url, "https://ccfddl.com/venues/ai/iclr/");
    assert.equal(detailData.structuredContent.conference.editions[0].venue_url, "https://ccfddl.com/venues/ai/iclr-2027/");
    assert.equal(detailData.structuredContent.conference.editions[0].opening_is_derived, true);
    assert.deepEqual(JSON.parse(detailData.content[0].text), detailData.structuredContent);
    const upcoming = await worker.fetch(rpcRequest(url, "tools/call", {
      name: "upcoming_deadlines", arguments: { days: 365, deadline_types: ["opening"], display_timezone: "Asia/Shanghai" },
    }), {});
    const upcomingData = (await rpcResponse(upcoming)).result;
    assert.equal(upcomingData.structuredContent.results[0].opening_is_derived, true);
    assert.equal(upcomingData.structuredContent.results[0].date, "May 1-3, 2027 (To be confirmed)");
    assert.deepEqual(JSON.parse(upcomingData.content[0].text), upcomingData.structuredContent);
    const rates = await worker.fetch(rpcRequest(url, "tools/call", {
      name: "get_acceptance_rates", arguments: { name_or_id: "ICLR", year: 2026 },
    }), {});
    assert.equal(rates.status, 200);
    const rateData = (await rpcResponse(rates)).result.structuredContent;
    assert.equal(rateData.status, "available");
    assert.equal(rateData.results[0].rate_percent, 30);

    const calls = [
      ["get_filter_options", {}], ["search_conferences", { query: "ICLR" }],
      ["get_conference", { name_or_id: "ICLR 2027" }],
      ["get_acceptance_rates", { name_or_id: "ICLR", year: 2026 }],
      ["upcoming_deadlines", { days: 365, deadline_types: ["opening"] }],
    ];
    const call = async (name, args) => {
      const response = await worker.fetch(rpcRequest(url, "tools/call", { name, arguments: args }), {});
      assert.equal(response.status, 200);
      const data = (await rpcResponse(response)).result;
      assert.equal(data.isError, undefined);
      assert.deepEqual(JSON.parse(data.content[0].text), data.structuredContent);
      return data.structuredContent;
    };
    const withoutStaleFlags = (data) => {
      const { stale, ...rest } = data;
      if (rest.acceptance_data) {
        const { stale: acceptanceStale, ...envelope } = rest.acceptance_data;
        rest.acceptance_data = envelope;
      }
      return rest;
    };
    const baseline = new Map();
    for (const [name, args] of calls) {
      const data = await call(name, args);
      assert.equal(data.stale, false);
      if (data.acceptance_data) assert.equal(data.acceptance_data.stale, false);
      baseline.set(name, data);
    }
    now += 16 * 60_000;
    catalogOffline = acceptanceOffline = true;
    for (const [name, args] of calls) {
      const data = await call(name, args);
      assert.equal(data.stale, true);
      if (data.acceptance_data) {
        assert.equal(data.acceptance_data.stale, true);
        assert.equal(data.acceptance_data.status, "available");
      }
      assert.deepEqual(withoutStaleFlags(data), withoutStaleFlags(baseline.get(name)));
    }
    catalogOffline = false;
    now += 1000;
    const partialRecovery = await call("get_conference", { name_or_id: "ICLR 2027" });
    assert.equal(partialRecovery.stale, false);
    assert.equal(partialRecovery.acceptance_data.stale, true);
    assert.equal(partialRecovery.fetched_at, new Date(now).toISOString());
    assert.equal(partialRecovery.acceptance_data.fetched_at, new Date(initialTime).toISOString());
    assert.deepEqual(partialRecovery.conference, baseline.get("get_conference").conference);
    acceptanceOffline = false;
    now += 1000;
    const recovered = await call("get_conference", { name_or_id: "ICLR 2027" });
    assert.equal(recovered.stale, false);
    assert.equal(recovered.acceptance_data.stale, false);
    assert.equal(recovered.acceptance_data.fetched_at, new Date(now).toISOString());
    assert.deepEqual(recovered.conference, baseline.get("get_conference").conference);
  } finally {
    globalThis.fetch = originalFetch;
    Date.now = originalNow;
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
