import assert from "node:assert/strict";
import test from "node:test";

import { deadlineToUtc, getConference, loadCatalog, searchConferences, upcomingDeadlines } from "../src/catalog.js";

const conferences = [
  {
    title: "ICLR", description: "Learning Representations", sub: "AI", rank: { ccf: "A" },
    confs: [{ year: 2027, id: "iclr27", link: "https://iclr.cc/Conferences/2027", timezone: "AoE",
      timeline: [{ abstract_deadline: "2026-09-18 23:59:59", deadline: "2026-10-01 23:59:59" }] }],
  },
  {
    title: "SIGMOD", sub: "DB", rank: { ccf: "A" },
    confs: [{ year: 2027, id: "sigmod27", timezone: "PT",
      timeline: [{ deadline: "TBD" }] }],
  },
];

test("converts AoE and Pacific daylight time to UTC", () => {
  assert.equal(deadlineToUtc("2026-10-01 23:59:59", "AoE"), "2026-10-02T11:59:59.000Z");
  assert.equal(deadlineToUtc("2026-07-01 17:00:00", "PT"), "2026-07-02T00:00:00.000Z");
  assert.equal(deadlineToUtc("2026-01-01 17:00:00", "PT"), "2026-01-02T01:00:00.000Z");
  assert.equal(deadlineToUtc("TBD", "AoE"), null);
});

test("searches by name, rank, and category", () => {
  assert.deepEqual(searchConferences(conferences, { query: "learning", ccf_rank: "A", category: "AI" })
    .map((item) => item.title), ["ICLR"]);
  assert.deepEqual(searchConferences(conferences, { ccf_rank: "B" }), []);
});

test("returns explicit deadlines without inventing unknown dates", () => {
  assert.equal(getConference(conferences, "iclr27").editions[0].deadlines.length, 2);
  assert.deepEqual(getConference(conferences, "ICLR 2027").editions.map((edition) => edition.edition), ["iclr27"]);
  assert.equal(getConference(conferences, "sigmod27").editions[0].deadlines.length, 1);
  assert.equal(getConference(conferences, "sigmod27").editions[0].deadlines[0].utc_time, null);
  assert.equal(getConference(conferences, "unknown"), null);
});

test("filters future deadlines and preserves source timezone", () => {
  const now = Date.parse("2026-09-30T00:00:00Z");
  const results = upcomingDeadlines(conferences, { now, days: 7, ccf_rank: "A", category: "AI" });
  assert.equal(results.length, 1);
  assert.equal(results[0].kind, "deadline");
  assert.equal(results[0].timezone, "AoE");
  assert.equal(results[0].website, "https://iclr.cc/Conferences/2027");
});

test("loads and reuses the public dataset without a database", async () => {
  let calls = 0;
  const fetcher = async (url) => {
    calls++;
    assert.equal(url, "https://ccfddl.com/conference/allconf.json");
    return Response.json(conferences);
  };
  const first = await loadCatalog(fetcher, Date.parse("2026-09-30T00:00:00Z"));
  const second = await loadCatalog(fetcher, Date.parse("2026-09-30T00:01:00Z"));
  assert.equal(first, second);
  assert.equal(calls, 1);
});

test("shares stale fallback with concurrent callers and retries after a failed refresh", async () => {
  const initialTime = Date.parse("2026-09-30T01:00:00Z");
  const cached = await loadCatalog(async () => Response.json(conferences), initialTime);
  let refreshCalls = 0;
  let rejectRefresh;
  const failingFetcher = () => {
    refreshCalls++;
    return new Promise((_, reject) => { rejectRefresh = reject; });
  };
  const expiredTime = initialTime + 16 * 60 * 1000;
  const first = loadCatalog(failingFetcher, expiredTime);
  const second = loadCatalog(failingFetcher, expiredTime);
  const responses = Promise.all([first, second]);
  rejectRefresh(new Error("Simulated upstream outage"));

  const [firstResult, secondResult] = await responses;
  assert.equal(refreshCalls, 1);
  assert.equal(firstResult, cached);
  assert.equal(secondResult, cached);

  let recoveryCalls = 0;
  const recovered = await loadCatalog(async () => {
    recoveryCalls++;
    return Response.json(conferences);
  }, expiredTime + 1000);
  assert.equal(recoveryCalls, 1);
  assert.notEqual(recovered, cached);
  assert.equal(recovered.fetched_at, new Date(expiredTime + 1000).toISOString());
});
