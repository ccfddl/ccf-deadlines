import assert from "node:assert/strict";
import test from "node:test";

import worker, {
  isValidConferenceKey,
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
