import assert from "node:assert/strict";
import test from "node:test";

import { deadlineToUtc, getConference, loadCatalog, searchConferencePage, searchConferences, upcomingDeadlinePage, upcomingDeadlines } from "../src/mcp/catalog.js";

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

test("provides canonical citation URLs separately from the official conference website", () => {
  const conference = getConference(conferences, "ICLR 2027");
  const edition = conference.editions[0];
  assert.equal(conference.series_url, "https://ccfddl.com/venues/ai/iclr/");
  assert.equal(edition.series_url, conference.series_url);
  assert.equal(edition.venue_url, "https://ccfddl.com/venues/ai/iclr-2027/");
  assert.equal(edition.website, "https://iclr.cc/Conferences/2027");
  const [deadline] = upcomingDeadlines(conferences, { now: Date.parse("2026-09-30T00:00:00Z"), days: 7 });
  assert.equal(deadline.venue_url, edition.venue_url);
});

test("omits citation URLs for invalid identities and years instead of guessing pages", () => {
  for (const sub of ["AI/../../", "", undefined]) {
    const conference = getConference([{ ...conferences[0], sub }], "ICLR");
    assert.equal(conference.series_url, null);
    assert.equal(conference.editions[0].venue_url, null);
  }
  for (const year of ["2027", 1899, 2201, undefined]) {
    const source = { ...conferences[0], confs: [{ ...conferences[0].confs[0], year }] };
    assert.equal(getConference([source], "ICLR").editions[0].venue_url, null);
  }
  const missingSlug = { ...conferences[0], title: "会议" };
  assert.equal(getConference([missingSlug], "会议").series_url, null);
  assert.equal(getConference([missingSlug], "会议").editions[0].venue_url, null);
});

const extendedCatalog = [
  {
    title: "FSE", conference_key: "SC/fse", sub: "SC", description: "Fast Software Encryption",
    rank: { ccf: "B", core: "B", thcpl: "B" },
    confs: [{ year: 2027, id: "crypto-fse27", timezone: "UTC+8", opening: "2027-01-10 09:00:00",
      timeline: [{ deadline: "2026-10-02 08:00:00" }] }],
  },
  {
    title: "FSE", conference_key: "SE/fse", sub: "SE", description: "Foundations of Software Engineering",
    rank: { ccf: "A", core: "A*", thcpl: "A" },
    confs: [
      { year: 2026, id: "fse26", timezone: "AoE", timeline: [{ deadline: "TBD" }] },
      { year: 2027, id: "fse27", timezone: "AoE", opening: "2027-01-10 09:00:00", timeline: [
        { abstract_deadline: "2026-10-01 23:59:59", deadline: "2026-10-02 23:59:59",
          rebuttal_deadline: "2026-10-04 23:59:59", decision_deadline: "TBD", comment: "Research track" },
        { deadline: "2026-10-05 23:59:59", comment: "Second round" },
      ] },
    ],
  },
  { title: "UNRANKED", sub: "MX", confs: [{ year: 2025, id: "unranked25", timezone: "UTC", timeline: [] }] },
];

test("filters CORE, THCPL and edition year while retaining namesake keys", () => {
  const results = searchConferences(extendedCatalog, { core_rank: "A*", thcpl_rank: "A", year: 2026 });
  assert.deepEqual(results.map((item) => item.conference_key), ["SE/fse"]);
  assert.equal(results[0].latest_edition, "fse26");
  assert.equal(results[0].series_url, "https://ccfddl.com/venues/se/fse/");
  assert.equal(results[0].venue_url, "https://ccfddl.com/venues/se/fse-2026/");
  assert.deepEqual(searchConferences(extendedCatalog, { ccf_rank: "N", core_rank: "N", thcpl_rank: "N" })
    .map((item) => item.title), ["UNRANKED"]);
  assert.equal(searchConferences(extendedCatalog, { query: "SE/fse" })[0].description, "Foundations of Software Engineering");
  assert.deepEqual(searchConferences(extendedCatalog, { year: 2040 }), []);
});

test("paginates matching conferences with complete counts and stable namesake ordering", () => {
  const first = searchConferencePage(extendedCatalog, { query: "FSE", limit: 1 });
  const second = searchConferencePage(extendedCatalog, { query: "FSE", limit: 1, offset: first.next_offset });
  assert.equal(first.total, 2);
  assert.equal(first.next_offset, 1);
  assert.equal(second.total, 2);
  assert.equal(second.next_offset, null);
  assert.deepEqual([first.results[0].conference_key, second.results[0].conference_key], ["SC/fse", "SE/fse"]);
  assert.deepEqual(searchConferencePage(extendedCatalog, { offset: 100 }).results, []);
});

test("asks callers to disambiguate namesakes instead of returning the first conference", () => {
  const ambiguous = getConference(extendedCatalog, "FSE 2027");
  assert.equal(ambiguous.ambiguous, true);
  assert.deepEqual(ambiguous.matches.map((item) => item.conference_key), ["SC/fse", "SE/fse"]);
  assert.deepEqual(ambiguous.matches.map((item) => item.venue_url), [
    "https://ccfddl.com/venues/sc/fse-2027/", "https://ccfddl.com/venues/se/fse-2027/",
  ]);
  assert.equal(getConference(extendedCatalog, "FSE", { category: "se" }).conference_key, "SE/fse");
  assert.equal(getConference(extendedCatalog, "se/FSE 2027").editions.length, 1);
  assert.equal(getConference(extendedCatalog, "crypto-fse27").conference_key, "SC/fse");
  assert.equal(getConference(extendedCatalog, "FSE 2027", { year: 2026 }), null);
  assert.equal(getConference(extendedCatalog, "fse27", { year: 2026 }), null);
});

test("returns explicit openings and localized known deadlines, preserving unknown dates", () => {
  const conference = getConference(extendedCatalog, "SE/fse", { display_timezone: "Asia/Shanghai" });
  const edition = conference.editions[0];
  assert.equal(edition.opening_utc, "2027-01-10T21:00:00.000Z");
  assert.equal(edition.opening_display_time, "2027-01-11 05:00:00");
  assert.equal(edition.deadlines[0].display_time, "2026-10-02 19:59:59");
  assert.equal(edition.deadlines[3].local_time, "TBD");
  assert.equal(edition.deadlines[3].utc_time, null);
  assert.equal(edition.deadlines[3].display_time, null);
  assert.equal(conference.editions[1].opening, null);
  assert.equal(conference.editions[1].opening_display_time, null);
  assert.equal(getConference(extendedCatalog, "SE/fse", { edition_limit: 1 }).editions.length, 1);
});

test("filters submission types and rankings before paginating future nodes", () => {
  const options = { now: Date.parse("2026-10-01T00:00:00Z"), days: 7, year: 2027,
    core_rank: "A*", thcpl_rank: "A", deadline_types: ["deadline"], limit: 1, display_timezone: "UTC" };
  const first = upcomingDeadlinePage(extendedCatalog, options);
  const second = upcomingDeadlinePage(extendedCatalog, { ...options, offset: first.next_offset });
  assert.equal(first.total, 2);
  assert.equal(first.results[0].kind, "deadline");
  assert.equal(first.results[0].display_time, "2026-10-03 11:59:59");
  assert.equal(first.results[0].note, "Research track");
  assert.equal(second.results[0].round, 2);
  assert.equal(second.next_offset, null);
  assert.equal(upcomingDeadlines(extendedCatalog, { ...options, year: 2026 }).length, 0);
});

test("only includes known conference openings when explicitly requested", () => {
  const options = { now: Date.parse("2027-01-10T00:00:00Z"), days: 2 };
  assert.deepEqual(upcomingDeadlines(extendedCatalog, options), []);
  const openings = upcomingDeadlines(extendedCatalog, { ...options, deadline_types: ["opening"] });
  assert.equal(openings.length, 2);
  assert.equal(openings[0].utc_time, "2027-01-10T01:00:00.000Z");
  assert.equal(openings[0].round, null);
});

test("returns declared opening provenance without inferring it from the clock hour", () => {
  const data = [{ title: "Marker", sub: "AI", confs: [
    { year: 2027, date: "Jan 10-12, 2027 (To be confirmed)", timezone: "UTC",
      opening: "2027-01-10 08:00:00", opening_is_derived: true, timeline: [] },
    { year: 2026, timezone: "UTC", opening: "2026-01-10 09:00:00", timeline: [] },
    { year: 2025, timezone: "UTC", opening: "2025-01-10 08:00:00", timeline: [] },
    { year: 2028, opening: null, opening_is_derived: true, timeline: [] },
    { year: 2029, timezone: "UTC", opening: "2029-01-10 08:00:00", opening_is_derived: "true", timeline: [] },
    { year: 2030, timezone: "UTC", opening: "2030-01-10 09:00:00", opening_is_derived: false, timeline: [] },
  ] }];
  const result = getConference(data, "Marker", { display_timezone: "Asia/Shanghai" });
  assert.deepEqual(result.editions.map((edition) => [edition.year, edition.opening_is_derived]), [
    [2030, false], [2029, null], [2028, null], [2027, true], [2026, null], [2025, null],
  ]);
  const upcoming = upcomingDeadlines(data, { now: Date.parse("2027-01-01T00:00:00Z"),
    days: 30, deadline_types: ["opening"], display_timezone: "Asia/Shanghai" });
  assert.equal(upcoming.length, 1);
  assert.equal(upcoming[0].opening_is_derived, true);
  assert.equal(upcoming[0].date, "Jan 10-12, 2027 (To be confirmed)");
  assert.equal(upcoming[0].display_time, "2027-01-10 16:00:00");
});

test("rejects impossible calendar dates instead of silently rolling them forward", () => {
  for (const raw of ["2026-02-30 12:00:00", "2026-02-29 12:00:00", "2026-04-31 12:00:00",
    "2026-13-01 12:00:00", "2026-01-01 24:00:00", "2026-01-01 12:60:00"]) {
    assert.equal(deadlineToUtc(raw, "AoE"), null, raw);
  }
  assert.equal(deadlineToUtc("2028-02-29 12:00:00", "UTC+8"), "2028-02-29T04:00:00.000Z");
  assert.equal(deadlineToUtc("2026-10-01 12:00:00", "UTC+15"), null);
});

test("does not guess a Pacific instant for skipped or repeated daylight-saving hours", () => {
  for (const raw of ["2026-03-08 02:00:00", "2026-03-08 02:59:59",
    "2026-11-01 01:00:00", "2026-11-01 01:59:59",
    "2027-03-14 02:30:00", "2027-11-07 01:30:00"]) {
    assert.equal(deadlineToUtc(raw, "PT"), null, raw);
  }
  for (const [raw, expected] of [
    ["2026-03-08 01:59:59", "2026-03-08T09:59:59.000Z"],
    ["2026-03-08 03:00:00", "2026-03-08T10:00:00.000Z"],
    ["2026-11-01 00:59:59", "2026-11-01T07:59:59.000Z"],
    ["2026-11-01 02:00:00", "2026-11-01T10:00:00.000Z"],
  ]) {
    assert.equal(deadlineToUtc(raw, "PT"), expected, raw);
  }
  // An explicit offset disambiguates the repeated local hour.
  assert.equal(deadlineToUtc("2026-11-01 01:30:00", "UTC-7"), "2026-11-01T08:30:00.000Z");
  assert.equal(deadlineToUtc("2026-11-01 01:30:00", "UTC-8"), "2026-11-01T09:30:00.000Z");
});

test("keeps ambiguous source times in details but excludes them from upcoming instants", () => {
  const data = [{ title: "Boundary", sub: "AI", confs: [{
    year: 2026, id: "boundary26", timezone: "PT", timeline: [
      { deadline: "2026-03-08 02:30:00", comment: "Spring gap" },
      { deadline: "2026-11-01 01:30:00", comment: "Autumn overlap" },
      { deadline: "2026-03-08 03:15:00", comment: "Unique instant" },
    ],
  }] }];
  const deadlines = getConference(data, "Boundary", { display_timezone: "Asia/Shanghai" }).editions[0].deadlines;
  assert.deepEqual(deadlines.slice(0, 2).map((event) => [event.local_time, event.utc_time, event.display_time]), [
    ["2026-03-08 02:30:00", null, null], ["2026-11-01 01:30:00", null, null],
  ]);
  assert.equal(deadlines[2].display_time, "2026-03-08 18:15:00");
  const upcoming = upcomingDeadlines(data, { now: Date.parse("2026-03-01T00:00:00Z"), days: 365 });
  assert.deepEqual(upcoming.map((event) => [event.local_time, event.utc_time, event.note]), [
    ["2026-03-08 03:15:00", "2026-03-08T10:15:00.000Z", "Unique instant"],
  ]);
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
  assert.equal(first.stale, false);
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
  assert.equal(firstResult, secondResult);
  assert.equal(firstResult.conferences, cached.conferences);
  assert.equal(firstResult.fetched_at, cached.fetched_at);
  assert.equal(firstResult.stale, true);
  assert.equal(cached.stale, false);

  for (const response of [new Response("offline", { status: 503 }), Response.json({ invalid: true })]) {
    const fallback = await loadCatalog(async () => response, expiredTime);
    assert.equal(fallback.stale, true);
    assert.equal(fallback.conferences, cached.conferences);
    assert.equal(fallback.fetched_at, cached.fetched_at);
  }

  let recoveryCalls = 0;
  const recovered = await loadCatalog(async () => {
    recoveryCalls++;
    return Response.json(conferences);
  }, expiredTime + 1000);
  assert.equal(recoveryCalls, 1);
  assert.notEqual(recovered, cached);
  assert.equal(recovered.fetched_at, new Date(expiredTime + 1000).toISOString());
  assert.equal(recovered.stale, false);
});

test("does not fabricate a cached catalog after a failed first load", async () => {
  const { loadCatalog: freshLoader } = await import("../src/mcp/catalog.js?cold-failure-test");
  await assert.rejects(freshLoader(async () => new Response("offline", { status: 503 })), /unavailable/);
  await assert.rejects(freshLoader(async () => Response.json({ invalid: true })), /invalid/);
  const loaded = await freshLoader(async () => Response.json(conferences));
  assert.equal(loaded.stale, false);
  assert.deepEqual(loaded.conferences, conferences);
});
