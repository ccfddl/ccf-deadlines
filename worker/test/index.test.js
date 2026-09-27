import assert from "node:assert/strict";
import test from "node:test";

import worker, {
  isValidConferenceKey,
  normalizeWallMessage,
  parseCookies,
  sanitizeReturnTo,
} from "../src/index.js";

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
