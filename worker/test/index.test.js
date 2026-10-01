import assert from "node:assert/strict";
import test from "node:test";

import worker, {
  filterFavoritesCalendar,
  isValidConferenceKey,
  isFreshOAuthPayload,
  messageLikesCutoff,
  normalizeWallMessage,
  parseCookies,
  readJsonBody,
  sanitizeReturnTo,
  utcDayStart,
} from "../src/index.js";

test("filters a live calendar to selected conference editions", () => {
  const calendar = [
    "BEGIN:VCALENDAR", "VERSION:2.0", "BEGIN:VTIMEZONE", "TZID:UTC+00:00", "END:VTIMEZONE",
    "BEGIN:VEVENT", "UID:iclr", "X-CCFDDL-ID:iclr27", "SUMMARY:ICLR", "END:VEVENT",
    "BEGIN:VEVENT", "UID:cvpr", "X-CCFDDL-ID:cvpr27", "SUMMARY:CVPR", "END:VEVENT",
    "END:VCALENDAR", "",
  ].join("\r\n");
  const filtered = filterFavoritesCalendar(calendar, new Set(["cvpr27"]));
  assert.match(filtered, /UID:cvpr/);
  assert.doesNotMatch(filtered, /UID:iclr/);
  assert.match(filtered, /TZID:UTC\+00:00/);
});

test("rejects a calendar from before edition markers were deployed", () => {
  assert.throws(
    () => filterFavoritesCalendar("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n", new Set(["iclr27"])),
    /Conference calendar is invalid/,
  );
});

test("rejects invalid batch subscription selections before fetching the calendar", async () => {
  for (const query of ["", "?id=../iclr27", "?id=iclr27&lang=invalid"]) {
    const response = await worker.fetch(
      new Request(`https://ccfddl.com/api/calendar/favorites.ics${query}`),
      { PUBLIC_ORIGIN: "https://ccfddl.com" },
    );
    assert.equal(response.status, 400);
  }
});

test("serves one public calendar feed for multiple selected editions", async () => {
  const originalFetch = globalThis.fetch;
  const source = [
    "BEGIN:VCALENDAR", "VERSION:2.0",
    "BEGIN:VEVENT", "UID:iclr", "X-CCFDDL-ID:iclr27", "END:VEVENT",
    "BEGIN:VEVENT", "UID:cvpr", "X-CCFDDL-ID:cvpr27", "END:VEVENT",
    "BEGIN:VEVENT", "UID:vldb", "X-CCFDDL-ID:vldb27", "END:VEVENT",
    "END:VCALENDAR", "",
  ].join("\r\n");
  try {
    globalThis.fetch = async (url) => {
      assert.equal(url, "https://ccfddl.com/conference/deadlines_en.ics");
      return new Response(source);
    };
    const response = await worker.fetch(
      new Request("https://ccfddl.com/api/calendar/favorites.ics?lang=en&id=iclr27&id=cvpr27"),
      { PUBLIC_ORIGIN: "https://ccfddl.com" },
    );
    assert.equal(response.status, 200);
    assert.match(response.headers.get("Content-Type"), /text\/calendar/);
    const body = await response.text();
    assert.match(body, /UID:iclr/);
    assert.match(body, /UID:cvpr/);
    assert.doesNotMatch(body, /UID:vldb/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("caches guest star counts and reads fresh totals for signed-in users", async (t) => {
  const originalCaches = globalThis.caches;
  const entries = new Map();
  globalThis.caches = { default: {
    async match(key) { return entries.get(key.url)?.clone(); },
    async put(key, response) { entries.set(key.url, response.clone()); },
  } };
  t.after(() => { globalThis.caches = originalCaches; });

  let count = 4;
  let countReads = 0;
  const env = {
    PUBLIC_ORIGIN: "https://ccfddl.com",
    DB: { prepare(sql) { return {
      async all() {
        if (sql.includes("FROM conference_star_counts")) {
          countReads++;
          return { results: [{ conference_key: "iclr27", star_count: count }] };
        }
        throw new Error(sql);
      },
      bind(...parameters) { return {
      async all() {
        if (sql.includes("FROM conference_stars WHERE github_id")) {
          return { results: [{ conference_key: "iclr27" }] };
        }
        throw new Error(sql);
      },
      async first() {
        if (sql.includes("FROM sessions JOIN users")) {
          return { github_id: 42, login: "reader", avatar_url: "", profile_url: "" };
        }
        if (sql.includes("FROM conference_star_counts")) {
          assert.deepEqual(parameters, ["iclr27"]);
          return { star_count: count };
        }
        throw new Error(sql);
      },
      async run() {
        if (sql.includes("INSERT OR IGNORE INTO conference_stars")) {
          count++;
          return { meta: { changes: 1 } };
        }
        throw new Error(sql);
      },
    }; } }; } },
  };
  const bootstrap = () => worker.fetch(new Request("https://ccfddl.com/api/bootstrap"), env);
  assert.deepEqual((await (await bootstrap()).json()).counts, { iclr27: 4 });
  assert.deepEqual((await (await bootstrap()).json()).counts, { iclr27: 4 });
  assert.equal(countReads, 1);
  assert.equal(entries.values().next().value.headers.get("Cache-Control"), "public, max-age=300");

  const star = await worker.fetch(new Request("https://ccfddl.com/api/stars/iclr27", {
    method: "PUT",
    headers: {
      Origin: "https://ccfddl.com",
      Cookie: `__Host-ccfddl_session=${"a".repeat(43)}`,
    },
  }), env);
  assert.equal(star.status, 200);
  assert.equal((await star.json()).count, 5);
  assert.deepEqual((await (await bootstrap()).json()).counts, { iclr27: 4 });
  assert.equal(countReads, 1);
  const signedIn = await worker.fetch(new Request("https://ccfddl.com/api/bootstrap", {
    headers: { Cookie: `__Host-ccfddl_session=${"a".repeat(43)}` },
  }), env);
  assert.deepEqual((await signedIn.json()).counts, { iclr27: 5 });
  assert.equal(countReads, 2);
});

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

test("rejects backslash and control-character OAuth redirect paths", () => {
  for (const path of ["/\\evil.example", "/path\n", "/path\r", "/ path"]) {
    assert.equal(sanitizeReturnTo(path), "/");
  }
});

test("rejects mutations without Origin or with cross-site fetch metadata", async () => {
  for (const headers of [{}, { Origin: "https://ccfddl.com", "Sec-Fetch-Site": "cross-site" }]) {
    const response = await worker.fetch(new Request("https://ccfddl.com/api/auth/logout", {
      method: "POST", headers,
    }), { PUBLIC_ORIGIN: "https://ccfddl.com" });
    assert.equal(response.status, 403);
  }
});

test("adds protective headers to successful and error responses", async () => {
  for (const path of ["health", "not-found"]) {
    const response = await worker.fetch(new Request(`https://ccfddl.com/api/${path}`), {});
    assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
    assert.equal(response.headers.get("Referrer-Policy"), "no-referrer");
    assert.match(response.headers.get("Content-Security-Policy"), /frame-ancestors 'none'/);
  }
});

test("rate limits API requests before accessing the database", async () => {
  let calls = 0;
  const response = await worker.fetch(new Request("https://ccfddl.com/api/bootstrap", {
    headers: { "CF-Connecting-IP": "192.0.2.1" },
  }), { API_RATE_LIMITER: { async limit({ key }) {
    assert.equal(key, "192.0.2.1"); calls++; return { success: false };
  } } });
  assert.equal(calls, 1);
  assert.equal(response.status, 429);
  assert.equal(response.headers.get("Retry-After"), "60");
});

test("uses a separate login limiter", async () => {
  const response = await worker.fetch(new Request("https://ccfddl.com/api/auth/github", {
    headers: { "CF-Connecting-IP": "192.0.2.1" },
  }), { AUTH_RATE_LIMITER: { async limit() { return { success: false }; } } });
  assert.equal(response.status, 429);
});

test("rejects message offsets outside the safe integer range", async () => {
  const response = await worker.fetch(new Request("https://ccfddl.com/api/messages?offset=9007199254740992"), {});
  assert.equal(response.status, 400);
});

test("expires OAuth state on the server and rejects malformed payloads", () => {
  const payload = { state: "a".repeat(32), verifier: "b".repeat(64), issued_at: 1000 };
  assert.equal(isFreshOAuthPayload(payload, 1599), true);
  assert.equal(isFreshOAuthPayload(payload, 1600), false);
  assert.equal(isFreshOAuthPayload({ ...payload, issued_at: 2000 }, 1000), false);
  assert.equal(isFreshOAuthPayload({ ...payload, issued_at: undefined }, 1000), false);
  assert.equal(isFreshOAuthPayload({ ...payload, state: 1 }, 1000), false);
});

test("requires JSON content type and validates body size independently of Content-Length", async () => {
  await assert.rejects(readJsonBody(new Request("https://ccfddl.com/api/messages", {
    method: "POST", body: "{}",
  })), (error) => error.status === 415);
  await assert.rejects(readJsonBody(new Request("https://ccfddl.com/api/messages", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "x".repeat(8193),
  })), (error) => error.status === 413);
  await assert.rejects(readJsonBody(new Request("https://ccfddl.com/api/messages", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: "{bad json",
  })), (error) => error.status === 400);
  assert.deepEqual(await readJsonBody(new Request("https://ccfddl.com/api/messages", {
    method: "POST", headers: { "Content-Type": "application/json; charset=utf-8" }, body: '{"body":"你好"}',
  })), { body: "你好" });
});

test("cancels an oversized streamed body with a forged Content-Length", async () => {
  let cancelled = false;
  const stream = new ReadableStream({
    start(controller) { controller.enqueue(new Uint8Array(8193)); },
    cancel() { cancelled = true; },
  });
  await assert.rejects(readJsonBody(new Request("https://ccfddl.com/api/messages", {
    method: "POST", duplex: "half", body: stream,
    headers: { "Content-Type": "application/json", "Content-Length": "1" },
  })), (error) => error.status === 413);
  assert.equal(cancelled, true);
});

test("issues host-bound HTTPS OAuth cookies and supports local HTTP", async () => {
  for (const origin of ["https://ccfddl.com", "http://localhost:8787"]) {
    const response = await worker.fetch(new Request(`${origin}/api/auth/github?return_to=%2Fconference`), {
      PUBLIC_ORIGIN: origin, GITHUB_CLIENT_ID: "test-client", GITHUB_CLIENT_SECRET: "test-secret",
      SESSION_SECRET: "s".repeat(32),
    });
    assert.equal(response.status, 302);
    const cookie = response.headers.get("Set-Cookie");
    assert.match(cookie, /HttpOnly; SameSite=Lax/);
    assert.match(cookie, /Path=\//);
    if (origin.startsWith("https")) {
      assert.match(cookie, /^__Host-ccfddl_oauth=/);
      assert.match(cookie, /; Secure$/);
    } else {
      assert.match(cookie, /^ccfddl_oauth=/);
      assert.doesNotMatch(cookie, /; Secure/);
    }
    const location = new URL(response.headers.get("Location"));
    assert.equal(location.searchParams.get("code_challenge_method"), "S256");
    assert.equal(location.searchParams.get("redirect_uri"), `${origin}/api/auth/github/callback`);
  }
});

test("rejects a weak signing secret before beginning OAuth", async () => {
  const response = await worker.fetch(new Request("https://ccfddl.com/api/auth/github"), {
    PUBLIC_ORIGIN: "https://ccfddl.com", GITHUB_CLIENT_ID: "test-client",
    GITHUB_CLIENT_SECRET: "test-secret", SESSION_SECRET: "short",
  });
  assert.equal(response.status, 500);
  assert.deepEqual(await response.json(), { error: "Internal server error" });
});

test("completes OAuth and identifies upstream versus session-storage failures safely", async (t) => {
  let failure = null;
  const logs = [];
  t.mock.method(console, "error", (...args) => logs.push(args));
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(options.redirect, "manual");
    if (failure === "network") throw new TypeError("sensitive upstream details");
    if (failure === "json") return new Response("not JSON");
    if (failure === "redirect" || (failure === "profile_redirect" && url.includes("api.github.com"))) {
      return new Response(null, { status: 307, headers: { Location: "https://example.com/collect" } });
    }
    return Response.json(url.includes("access_token")
      ? { access_token: "private-access-token" }
      : { id: 1, login: "test-user", avatar_url: "https://example.com/avatar", html_url: "https://github.com/test-user" });
  });
  const env = {
    PUBLIC_ORIGIN: "https://ccfddl.com", GITHUB_CLIENT_ID: "test-client",
    GITHUB_CLIENT_SECRET: "private-client-secret", SESSION_SECRET: "s".repeat(32),
    DB: {
      prepare(sql) { return { bind(...parameters) { return { sql, parameters }; } }; },
      async batch(statements) {
        if (failure === "database") throw new Error("private database details");
        assert.equal(statements.length, 4);
      },
    },
  };
  const start = await worker.fetch(new Request(`${env.PUBLIC_ORIGIN}/api/auth/github`), env);
  const state = new URL(start.headers.get("Location")).searchParams.get("state");
  const cookie = start.headers.get("Set-Cookie").split(";")[0];
  for (const mode of [null, "network", "json", "redirect", "profile_redirect", "database"]) {
    failure = mode;
    const response = await worker.fetch(new Request(
      `${env.PUBLIC_ORIGIN}/api/auth/github/callback?code=private-code&state=${state}`,
      { headers: { Cookie: cookie } },
    ), env);
    if (mode === null) {
      assert.equal(response.status, 302);
      assert.equal(response.headers.get("Location"), `${env.PUBLIC_ORIGIN}/`);
      assert.match(response.headers.get("Set-Cookie"), /__Host-ccfddl_session=/);
    } else {
      assert.equal(response.status, mode === "database" ? 500 : 502);
      const body = await response.json();
      assert.match(body.error, mode === "database" ? /save.*session/ : /contact GitHub/);
      assert.equal(body.code, {
        network: "github_token_request_network_error",
        json: "github_token_response_invalid_json",
        redirect: "github_token_request_redirect_rejected",
        profile_redirect: "github_profile_request_redirect_rejected",
        database: "github_session_storage_failed",
      }[mode]);
    }
  }
  assert.deepEqual(logs.map((entry) => entry[1]), ["token_request", "token_response", "token_request", "profile_request", "session_storage"]);
  assert.doesNotMatch(JSON.stringify(logs), /private|sensitive/);
});
