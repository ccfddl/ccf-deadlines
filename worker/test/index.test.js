import assert from "node:assert/strict";
import test from "node:test";

import worker, {
  isValidConferenceKey,
  messageLikesCutoff,
  normalizeWallMessage,
  parseCookies,
  sanitizeReturnTo,
  utcDayStart,
} from "../src/index.js";

test("limits the most-liked view to messages from the last 30 days", () => {
  const now = 2_000_000_000;
  assert.equal(messageLikesCutoff(now), now - 30 * 24 * 60 * 60);
});

test("accepts conference edition ids used by the dataset", () => {
  assert.equal(isValidConferenceKey("iclr27"), true);
  assert.equal(isValidConferenceKey("ifip119'27"), true);
  assert.equal(isValidConferenceKey("ih&mmsec26"), true);
});

test("rejects malformed conference keys", () => {
  assert.equal(isValidConferenceKey(""), false);
  assert.equal(isValidConferenceKey("../iclr27"), false);
  assert.equal(isValidConferenceKey("iclr/27"), false);
});

test("only accepts local OAuth return paths", () => {
  assert.equal(sanitizeReturnTo("/conference?rank=A"), "/conference?rank=A");
  assert.equal(sanitizeReturnTo("https://example.com"), "/");
  assert.equal(sanitizeReturnTo("//example.com"), "/");
});

test("parses cookie values containing equals signs", () => {
  assert.deepEqual(parseCookies("session=abc==; theme=light"), {
    session: "abc==",
    theme: "light",
  });
});

test("normalizes valid wall messages", () => {
  assert.equal(normalizeWallMessage("  hello\r\nworld  "), "hello\nworld");
  assert.equal(normalizeWallMessage("你好 🌊"), "你好 🌊");
  assert.equal(normalizeWallMessage("a".repeat(500)), "a".repeat(500));
});

test("rejects invalid wall messages", () => {
  assert.equal(normalizeWallMessage("   "), null);
  assert.equal(normalizeWallMessage("a".repeat(501)), null);
  assert.equal(normalizeWallMessage("1\n2\n3\n4\n5\n6\n7\n8\n9"), null);
  assert.equal(normalizeWallMessage("hello\u0000world"), null);
});

test("calculates UTC day boundaries for daily posting limits", () => {
  assert.equal(utcDayStart(0), 0);
  assert.equal(utcDayStart(86_399), 0);
  assert.equal(utcDayStart(86_400), 86_400);
  assert.equal(utcDayStart(100_000), 86_400);
});

test("serves a health response without database access", async () => {
  const response = await worker.fetch(new Request("https://ccfddl.com/api/health"), {});
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true });
});

test("rejects cross-origin favorite mutations", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/stars/iclr27", {
      method: "PUT",
      headers: { Origin: "https://example.com" },
    }),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 403);
});

test("rejects cross-origin wall message mutations", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages", {
      method: "POST",
      headers: { Origin: "https://example.com" },
    }),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 403);
});

test("requires GitHub sign-in to post wall messages", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: "https://ccfddl.com",
      },
      body: JSON.stringify({ body: "hello" }),
    }),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 401);
});

test("requires GitHub sign-in to browse older wall messages", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages?offset=50"),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 401);
});

test("rejects malformed wall message cursors", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages?offset=not-a-number"),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 400);
});

test("requires GitHub sign-in to browse personal wall messages", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages?sort=mine"),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 401);
});

test("rejects invalid wall message sorting", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages?sort=oldest"),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 400);
});

test("requires GitHub sign-in to like wall messages", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages/1/like", {
      method: "PUT",
      headers: { Origin: "https://ccfddl.com" },
    }),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 401);
});

test("rejects cross-origin wall message likes", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages/1/like", {
      method: "PUT",
      headers: { Origin: "https://example.com" },
    }),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 403);
});

test("rejects invalid wall message reply targets", async () => {
  const response = await worker.fetch(
    new Request("https://ccfddl.com/api/messages/0/replies"),
    { PUBLIC_ORIGIN: "https://ccfddl.com" },
  );
  assert.equal(response.status, 400);
});
