import assert from "node:assert/strict";
import test from "node:test";
import { buildEmailDigest } from "../src/email_reminders.js";

const event = { id: "test27", title: "Test paper", precision: "date", deadline_date: "2027-02-28",
  deadline_at: null, all_day: true, timezone: "Unknown", url: "https://example.org" };
const favorites = new Set([event.id]);

test("date-only reminders preserve date and uncertainty without a user-zone clock", () => {
  const digest = buildEmailDigest([event], favorites, "Asia/Tokyo", "en", Date.parse("2027-03-01T11:59:59Z"), { daily: true });
  assert.equal(digest.items.length, 1);
  assert.match(digest.items[0].when, /2027\/02\/28 · time unknown/);
  assert.equal(digest.items[0].timezone, "timezone unknown");
  assert.equal(digest.items[0].lead, "Due today");
  assert.equal(buildEmailDigest([event], favorites, "Asia/Tokyo", "en", Date.parse("2027-03-01T12:00:00Z"), { daily: true }), null);
});

test("source-known dates use source calendar days and reject malformed dates", () => {
  const known = { ...event, timezone: "UTC+8" };
  assert.ok(buildEmailDigest([known], favorites, "America/Los_Angeles", "en", Date.parse("2027-02-28T15:59:59Z"), { daily: true }));
  assert.equal(buildEmailDigest([known], favorites, "America/Los_Angeles", "en", Date.parse("2027-02-28T16:00:00Z"), { daily: true }), null);
  for (const deadline_date of ["2027-02-29", "2028-02-30", "2028-2-29", "TBD"]) {
    assert.equal(buildEmailDigest([{ ...event, deadline_date }], favorites, "UTC", "en", Date.parse("2027-02-28T12:00:00Z"), { daily: true }), null);
  }
  assert.ok(buildEmailDigest([{ ...event, deadline_date: "2028-02-29" }], favorites, "UTC", "en", Date.parse("2028-02-29T12:00:00Z"), { daily: true }));
});

test("mixed precision reminders include later nodes and retain exact-time rendering", () => {
  const precise = { ...event, uid: "precise", precision: "datetime", deadline_date: null,
    deadline_at: "2027-03-02T12:00:00Z", all_day: false, timezone: "UTC" };
  const digest = buildEmailDigest([event, precise], favorites, "UTC", "en", Date.parse("2027-03-01T12:00:00Z"), { daily: true });
  assert.equal(digest.items.length, 1);
  assert.equal(digest.items[0].when, "2027/03/02 12:00");
});

test("mixed-source date ordering follows internal lower bounds, not invented clocks", () => {
  const known = { ...event, uid: "known", title: "Known date", deadline_date: "2028-03-01", timezone: "UTC+8" };
  const unknown = { ...known, uid: "unknown", title: "Unknown date", timezone: "Unknown" };
  const precise = { ...known, uid: "precise", title: "Precise", precision: "datetime", all_day: false,
    deadline_date: null, deadline_at: "2028-02-29T18:00:00Z", timezone: "UTC" };
  const digest = buildEmailDigest([known, precise, unknown], favorites, "UTC", "en", Date.parse("2028-02-28T12:00:00Z"), { daily: true });
  assert.deepEqual(digest.items.map((item) => item.title), ["Unknown date", "Known date", "Precise"]);
  assert.equal(buildEmailDigest([{ ...precise, timezone: "Unknown" }], favorites, "UTC", "en", Date.parse("2028-02-28T12:00:00Z"), { daily: true }), null);
});
