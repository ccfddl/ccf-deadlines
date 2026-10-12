import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("./seo_page_controls.js", import.meta.url), "utf8");

function render(entries) {
  const times = entries.map(([raw, timezone, datetime = ""]) => ({
    dataset: { raw, sourceTz: timezone }, textContent: `${raw} · ${timezone}`, dateTime: datetime,
  }));
  const rows = times.map((time, index) => ({
    dataset: time.dataset,
    querySelector: () => ({ firstChild: { textContent: `Deadline ${index + 1}` } }),
  }));
  const handlers = {};
  const select = { style: {}, add() {}, addEventListener: (name, callback) => { handlers[name] = callback; } };
  const clock = {};
  const button = { hidden: false, addEventListener() {} };
  const calendar = { hidden: false, href: "" };
  const links = [];
  const menu = { appendChild: (link) => links.push(link) };
  const card = { dataset: {
    conferenceName: "Fixture", conferenceYear: "2027", conferenceId: "fixture27",
    conferenceDescription: "Date conversion fixture", conferenceWebsite: "https://example.com",
    conferencePlace: "Test location",
  } };
  const elements = {
    "display-timezone": select, "display-clock": clock,
    "google-calendar-button": button, "icloud-calendar-link": calendar,
    "google-calendar-events": menu,
  };
  let updatedUrl;
  vm.runInNewContext(source, {
    Intl, Date, URL, URLSearchParams,
    Option: class { constructor(label, value) { this.label = label; this.value = value; } },
    localStorage: { getItem: () => null, setItem() {} }, setInterval: () => 0,
    location: { search: "?tz=UTC", href: "https://ccfddl.com/venues/ai/fixture-2027/?tz=UTC#conference-overview" },
    history: { replaceState: (_state, _unused, url) => { updatedUrl = url; } },
    document: {
      getElementById: (id) => elements[id] ?? null,
      querySelector: (selector) => selector === ".detail-card" ? card : null,
      querySelectorAll: (selector) => selector === ".deadline-time[data-raw]" ? times : rows,
      createElement: () => ({}),
    },
  });
  return { times, links, button, calendar,
    changeTimezone(value) { select.value = value; handlers.change(); return updatedUrl; },
  };
}

test("converts unique source instants without changing their datetime precision", () => {
  const page = render([
    ["2026-03-08 01:59:59", "PT", "2026-03-08T01:59:59-08:00"],
    ["2026-03-08 03:00:00", "PT", "2026-03-08T03:00:00-07:00"],
    ["2026-11-01 00:59:59", "PT", "2026-11-01T00:59:59-07:00"],
    ["2026-11-01 02:00:00", "PT", "2026-11-01T02:00:00-08:00"],
    ["2026-11-01 01:30:00", "UTC-7"], ["2026-11-01 01:30:00", "UTC-8"],
    ["2027-01-01 23:59:59", "AoE"], ["2027-01-01", "UTC", "2027-01-01"],
  ]);
  assert.deepEqual(page.times.map((time) => time.textContent), [
    "09:59, Mar 8, 2026 · UTC", "10:00, Mar 8, 2026 · UTC",
    "07:59, Nov 1, 2026 · UTC", "10:00, Nov 1, 2026 · UTC",
    "08:30, Nov 1, 2026 · UTC", "09:30, Nov 1, 2026 · UTC",
    "11:59, Jan 2, 2027 · UTC", "23:59, Jan 1, 2027 · UTC",
  ]);
  const datetimes = page.times.map((time) => time.dateTime);
  assert.equal(page.links.length, 8);
  const url = page.changeTimezone("Asia/Shanghai");
  assert.ok(page.times.every((time) => time.textContent.endsWith("· Asia/Shanghai")));
  assert.deepEqual(page.times.map((time) => time.dateTime), datetimes);
  assert.ok(url.endsWith("#conference-overview"));
});

test("retains skipped and repeated Pacific times without inventing calendar events", () => {
  const entries = [
    ["2026-03-08 02:00:00", "PT"], ["2026-03-08 02:59:59", "PT"],
    ["2026-11-01 01:00:00", "PT"], ["2026-11-01 01:59:59", "PT"],
    ["2027-03-14 02:30:00", "PT"], ["2027-11-07 01:30:00", "PT"],
  ];
  const page = render(entries);
  const original = entries.map(([raw, zone]) => `${raw} · ${zone}`);
  assert.deepEqual(page.times.map((time) => time.textContent), original);
  page.changeTimezone("America/New_York");
  assert.deepEqual(page.times.map((time) => time.textContent), original);
  assert.ok(page.times.every((time) => time.dateTime === ""));
  assert.equal(page.links.length, 0);
  assert.equal(page.button.hidden, true);
  assert.equal(page.calendar.hidden, true);
});

test("does not normalize invalid dates, clock fields or timezone offsets", () => {
  const entries = [
    ["2026-02-30 12:00:00", "UTC"], ["2026-02-29", "AoE"],
    ["2026-04-31 12:00:00", "PT"], ["2026-01-01 24:00:00", "UTC"],
    ["2026-01-01 12:60:00", "UTC"], ["2026-01-01 12:00:60", "UTC"],
    ["2026-01-01 12:00:00", "UTC+24"], ["2026-01-01 12:00:00", "UTC-99"],
    ["2026-01-01 12:00:00", "UTC+05:60"], ["TBD", "PT"],
  ];
  const page = render(entries);
  assert.deepEqual(page.times.map((time) => time.textContent), entries.map(([raw, zone]) => `${raw} · ${zone}`));
  assert.equal(page.links.length, 0);
  assert.equal(page.calendar.href, "");
});

test("calendar exports include only uniquely determined deadline instants", () => {
  const page = render([
    ["2026-03-08 02:30:00", "PT"], ["2026-11-01 01:30:00", "PT"],
    ["2026-03-08 03:00:00", "PT"], ["2026-11-01 01:30:00", "UTC-8"],
  ]);
  assert.equal(page.links.length, 2);
  assert.deepEqual(page.links.map((link) => new URL(link.href).searchParams.get("dates")), [
    "20260308T100000Z/20260308T100100Z", "20261101T093000Z/20261101T093100Z",
  ]);
  const ical = decodeURIComponent(page.calendar.href.slice(page.calendar.href.indexOf(",") + 1));
  assert.equal(ical.match(/BEGIN:VEVENT/g)?.length, 2);
  assert.ok(ical.includes("DTSTART:20260308T100000Z"));
  assert.ok(ical.includes("DTSTART:20261101T093000Z"));
  assert.ok(!ical.includes("Deadline 1") && !ical.includes("Deadline 2"));
});
