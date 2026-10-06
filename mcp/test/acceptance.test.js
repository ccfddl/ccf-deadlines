import assert from "node:assert/strict";
import test from "node:test";

import { ACCEPTANCE_SOURCE, createAcceptanceIndex, enrichAcceptance, getAcceptanceRates } from "../src/acceptance.js";
import { getConference, searchConferencePage, upcomingDeadlinePage } from "../src/catalog.js";

const conferences = [
  { title: "ICLR", sub: "AI", dblp: "iclr", confs: [
    { id: "iclr26", year: 2026, timezone: "AoE", timeline: [] },
    { id: "iclr27", year: 2027, timezone: "AoE", timeline: [{ deadline: "2026-10-01 23:59:59" }] },
  ] },
  { title: "FSE", sub: "SE", confs: [{ id: "fse27", year: 2027, timeline: [] }] },
  { title: "FSE", sub: "SC", confs: [{ id: "crypto-fse27", year: 2027, timeline: [] }] },
  { title: "EMPTY", sub: "MX", confs: [{ year: 2027, timeline: [] }] },
];

const acceptances = [
  { title: "ICLR", accept_rates: [
    { year: 2020, submitted: 100, accepted: 25, rate: 0.25, str: "25%", source: "https://example.org/2020" },
    { year: 2026, submitted: 200, accepted: 60, rate: 0.3, str: "30%", source: "https://example.org/2026" },
    { year: 2025, submitted: 100, accepted: 35, rate: 0.35, str: "35%", source: "https://example.org/2025" },
  ] },
  { title: "FSE", accept_rates: [{ year: 2021, submitted: 407, accepted: 97, rate: 97 / 407 }] },
];
const catalog = (rows = acceptances) => ({ acceptances: rows, source: ACCEPTANCE_SOURCE, fetched_at: "2026-10-06T00:00:00.000Z" });
const index = createAcceptanceIndex(conferences, catalog());

test("returns descending paginated history with paper counts, percentage and record sources", () => {
  const first = getAcceptanceRates(conferences, index, "iclr", { limit: 2 });
  const second = getAcceptanceRates(conferences, index, "ICLR", { limit: 2, offset: first.next_offset });
  assert.equal(first.status, "available");
  assert.equal(first.total, 3);
  assert.deepEqual(first.results.map((record) => record.year), [2026, 2025]);
  assert.deepEqual(first.results[0], { year: 2026, submitted: 200, accepted: 60,
    rate: 0.3, rate_percent: 30, label: "30%", source: "https://example.org/2026" });
  assert.equal(second.results[0].year, 2020);
  assert.equal(second.next_offset, null);
  assert.equal(first.conference.conference_key, "AI/iclr");
});

test("filters statistical years independently of published deadline editions", () => {
  assert.equal(getAcceptanceRates(conferences, index, "ICLR 2020").results[0].year, 2020);
  assert.equal(getAcceptanceRates(conferences, index, "AI/iclr", { year: 2020 }).total, 1);
  assert.equal(getAcceptanceRates(conferences, index, "iclr26").results[0].year, 2026);
  assert.deepEqual(getAcceptanceRates(conferences, index, "ICLR", { from_year: 2025, to_year: 2026 })
    .results.map((record) => record.year), [2026, 2025]);
  assert.equal(getAcceptanceRates(conferences, index, "ICLR 2025", { year: 2026 }).total, 0);
  assert.equal(getAcceptanceRates(conferences, index, "iclr26", { year: 2025 }).total, 0);
});

test("does not claim a missing future year's rate is a historical rate", () => {
  const response = enrichAcceptance({ conference: getConference(conferences, "ICLR") }, index, conferences);
  assert.equal(response.conference.dblp, "iclr");
  assert.equal(response.conference.acceptance_rates_total, 3);
  assert.equal(response.conference.editions[0].acceptance_rate, null);
  assert.deepEqual(response.conference.editions[0].recent_acceptance_rates.map((record) => record.year), [2026, 2025]);
  assert.equal(response.conference.editions[1].acceptance_rate.year, 2026);
  assert.equal(getAcceptanceRates(conferences, index, "ICLR", { year: 2027 }).status, "missing");
});

test("search and upcoming summaries only attach statistics at or before their edition year", () => {
  const search = enrichAcceptance(searchConferencePage(conferences, { query: "ICLR", year: 2026 }), index, conferences, { year: 2026 });
  assert.equal(search.results[0].latest_acceptance_rate.year, 2026);
  const future = enrichAcceptance(upcomingDeadlinePage(conferences, {
    now: Date.parse("2026-09-30T00:00:00Z"), days: 5,
  }), index, conferences);
  assert.equal(future.results[0].year, 2027);
  assert.equal(future.results[0].latest_acceptance_rate.year, 2026);
  const older = enrichAcceptance({ results: [{ conference_key: "AI/iclr", year: 2020 }] }, index, conferences);
  assert.equal(older.results[0].latest_acceptance_rate.year, 2020);
});

test("refuses ambiguous title-only statistics even after choosing a namesake", () => {
  const response = getAcceptanceRates(conferences, index, "FSE");
  assert.equal(response.status, "ambiguous");
  assert.equal(response.conference.matches.length, 2);
  for (const key of ["SE/fse", "SC/fse"]) {
    const response = getAcceptanceRates(conferences, index, key);
    assert.equal(response.status, "ambiguous");
    assert.deepEqual(response.results, []);
  }
  assert.equal(getAcceptanceRates(conferences, index, "FSE", { category: "SC" }).status, "ambiguous");
});

test("uses explicit conference keys or subject metadata to associate namesake statistics", () => {
  const scoped = createAcceptanceIndex(conferences, catalog([
    ...acceptances,
    { title: "FSE", conference_key: "SE/fse", accept_rates: [{ year: 2026, rate: 0.2 }] },
    { title: "FSE", sub: "SC", accept_rates: [{ year: 2025, rate: 0.4 }] },
  ]));
  assert.deepEqual(getAcceptanceRates(conferences, scoped, "SE/FSE").results.map((record) => record.year), [2026]);
  assert.deepEqual(getAcceptanceRates(conferences, scoped, "FSE", { category: "sc" }).results.map((record) => record.year), [2025]);
});

test("distinguishes no record, unknown conference and an unavailable statistics source", () => {
  assert.equal(getAcceptanceRates(conferences, index, "EMPTY").status, "missing");
  assert.equal(getAcceptanceRates(conferences, index, "NO-SUCH-CONFERENCE").status, "not_found");
  const unavailable = createAcceptanceIndex(conferences);
  assert.equal(getAcceptanceRates(conferences, unavailable, "ICLR").status, "unavailable");
  const response = enrichAcceptance({ conference: getConference(conferences, "ICLR") }, unavailable, conferences);
  assert.equal(response.conference.acceptance_status, "unavailable");
  assert.equal(response.conference.editions[0].deadlines[0].kind, "deadline");
});

test("preserves legacy labels and zero rates without parsing labels or predicting missing numbers", () => {
  const sparse = createAcceptanceIndex(conferences, catalog([{ title: "ICLR", accept_rates: [
    { year: 2026, submitted: 100, accepted: 0, srt: "0%" },
    { year: 2025, str: "Unknown", submitted: null, accepted: null },
    { year: 2024, submitted: 0, accepted: 0 },
    { year: "2023", rate: 0.3 },
  ] }]));
  const records = getAcceptanceRates(conferences, sparse, "ICLR").results;
  assert.equal(records.length, 3);
  assert.equal(records[0].rate, 0);
  assert.equal(records[0].rate_percent, 0);
  assert.equal(records[0].label, "0%");
  assert.equal(records[1].rate, null);
  assert.equal(records[1].source, null);
  assert.equal(records[2].rate, null);
});

test("flags contradictory counts and rates while preserving the published numbers", () => {
  const conflicting = createAcceptanceIndex(conferences, catalog([{ title: "ICLR", accept_rates: [
    { year: 2026, submitted: 1701, accepted: 3272, rate: 0.5198655256723717 },
    { year: 2025, submitted: 100, accepted: 20, rate: 0.5 },
  ] }]));
  const records = getAcceptanceRates(conferences, conflicting, "ICLR").results;
  assert.equal(records[0].accepted, 3272);
  assert.equal(records[0].rate_percent, 51.99);
  assert.deepEqual(records[0].data_issues, ["accepted_exceeds_submitted"]);
  assert.deepEqual(records[1].data_issues, ["rate_disagrees_with_counts"]);
});

test("acceptance cache shares concurrent refreshes and preserves stale data on a source outage", async () => {
  const { loadAcceptanceCatalog } = await import("../src/acceptance.js?cache-test");
  const now = Date.parse("2026-10-06T00:00:00Z");
  let calls = 0;
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const fetcher = async (url) => {
    assert.equal(url, ACCEPTANCE_SOURCE);
    calls++;
    await pending;
    return Response.json(acceptances);
  };
  const first = loadAcceptanceCatalog(fetcher, now);
  const concurrent = loadAcceptanceCatalog(fetcher, now);
  release();
  assert.equal(await first, await concurrent);
  const cached = await loadAcceptanceCatalog(fetcher, now + 60_000);
  assert.equal(calls, 1);
  let outages = 0;
  const failing = async () => { outages++; throw new Error("offline"); };
  const stale = await Promise.all([
    loadAcceptanceCatalog(failing, now + 16 * 60_000),
    loadAcceptanceCatalog(failing, now + 16 * 60_000),
  ]);
  assert.equal(outages, 1);
  assert.equal(stale[0], cached);
  assert.equal(stale[1], cached);
  assert.equal(stale[0].fetched_at, new Date(now).toISOString());
});

test("rejects invalid acceptance feeds and recovers after the first-load failure", async () => {
  const { loadAcceptanceCatalog } = await import("../src/acceptance.js?failure-test");
  await assert.rejects(loadAcceptanceCatalog(async () => new Response("offline", { status: 503 })), /unavailable/);
  await assert.rejects(loadAcceptanceCatalog(async () => Response.json([{ title: "ICLR", accept_rates: {} }])), /invalid/);
  const loaded = await loadAcceptanceCatalog(async () => Response.json(acceptances));
  assert.equal(loaded.acceptances.length, 2);
});
