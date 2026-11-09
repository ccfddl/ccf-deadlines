import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import worker from "../src/index.js";

const DAY = 24 * 60 * 60;
const TTL = 30 * DAY;
const NOW = 1_800_000_000;
const TOKEN = "a".repeat(43);
const TOKEN_HASH = createHash("sha256").update(TOKEN).digest("hex");
const ORIGIN = "https://ccfddl.com";

// Execute the Worker's actual SQL rather than interpreting it as test fixtures.
function fixture(t, { expiresAt = NOW + DAY, createdAt = NOW - 29 * DAY } = {}) {
  const database = new DatabaseSync(":memory:");
  t.after(() => database.close());
  const clock = { now: NOW };
  t.mock.method(Date, "now", () => clock.now * 1000);
  database.exec(`
    PRAGMA foreign_keys = ON;
    CREATE TABLE users (
      github_id INTEGER PRIMARY KEY, login TEXT NOT NULL, avatar_url TEXT NOT NULL,
      profile_url TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
    );
    CREATE TABLE sessions (
      token_hash TEXT PRIMARY KEY, github_id INTEGER NOT NULL, expires_at INTEGER NOT NULL,
      created_at INTEGER NOT NULL, FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
    );
    CREATE TABLE email_reminders (
      github_id INTEGER PRIMARY KEY, email TEXT NOT NULL, timezone TEXT NOT NULL,
      language TEXT NOT NULL, daily_enabled INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
      FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
    );
  `);
  database.prepare("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)")
    .run(42, "reader", "https://example.org/avatar.png", "https://github.com/reader", createdAt, NOW);
  database.prepare("INSERT INTO sessions VALUES (?, ?, ?, ?)").run(TOKEN_HASH, 42, expiresAt, createdAt);
  database.prepare("INSERT INTO email_reminders VALUES (?, ?, ?, ?, ?, ?, ?)")
    .run(42, "reader@example.org", "Asia/Shanghai", "zh", 1, NOW, NOW);

  const hooks = {};
  const renewalWrites = [];
  const DB = {
    prepare(sql) {
      const statement = database.prepare(sql);
      function bound(parameters) {
        return {
          bind(...values) { return bound(values); },
          async first(column) {
            await hooks.beforeFirst?.(sql, parameters);
            const result = statement.get(...parameters);
            return column ? result?.[column] ?? null : result ?? null;
          },
          async all() { return { results: statement.all(...parameters), success: true }; },
          async run() {
            const renewal = /^\s*UPDATE\s+sessions\s+SET\s+expires_at\b/i.test(sql);
            if (renewal) await hooks.beforeRenewal?.();
            const result = statement.run(...parameters);
            const changes = Number(result.changes);
            if (renewal) renewalWrites.push(changes);
            return { success: true, meta: { changes } };
          },
        };
      }
      return bound([]);
    },
  };
  const env = {
    DB, PUBLIC_ORIGIN: ORIGIN, GITHUB_CLIENT_ID: "test-client", GITHUB_CLIENT_SECRET: "test-secret",
    SESSION_SECRET: "s".repeat(32), RESEND_API_KEY: "test-sender", EMAIL_FROM: "reminders@example.org",
  };
  return {
    database, clock, hooks, renewalWrites, env,
    session: () => database.prepare("SELECT * FROM sessions WHERE token_hash = ?").get(TOKEN_HASH),
    fetch: (request = authenticatedRequest()) => worker.fetch(request, env),
  };
}

function authenticatedRequest(path = "/api/email/reminders", { token = TOKEN, method = "GET", body } = {}) {
  const headers = new Headers({ Origin: ORIGIN });
  if (token !== null) headers.set("Cookie", `__Host-ccfddl_session=${token}`);
  if (body !== undefined) headers.set("Content-Type", "application/json");
  return new Request(ORIGIN + path, { method, headers, body });
}

function assertRenewalCookie(response) {
  const cookie = response.headers.get("Set-Cookie");
  assert.ok(cookie);
  assert.equal(cookie.split(";")[0], `__Host-ccfddl_session=${TOKEN}`);
  for (const attribute of ["Path=/", "HttpOnly", "SameSite=Lax", `Max-Age=${TTL}`, "Secure"]) {
    assert.ok(cookie.split(";").map((part) => part.trim()).includes(attribute), attribute);
  }
  assert.doesNotMatch(cookie, /(?:^|;)\s*Domain=/i);
}

const SETTINGS = {
  available: true, enabled: true, email: "reader@example.org", timezone: "Asia/Shanghai",
  language: "zh", daily_enabled: true, reminder_days: [7, 1], send_hour: 9,
};

test("successful reminder requests renew an old 30-day session without exposing session fields", async (t) => {
  const state = fixture(t);
  const response = await state.fetch();
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), SETTINGS);
  assertRenewalCookie(response);
  assert.equal(state.session().expires_at, NOW + TTL);
  assert.equal(state.session().created_at, NOW - 29 * DAY);
  assert.deepEqual(state.renewalWrites, [1]);
});

test("renewal starts at exactly 24 hours and does not repeat within the same day", async (t) => {
  const state = fixture(t, { expiresAt: NOW + TTL - DAY + 1, createdAt: NOW - DAY + 1 });
  const request = authenticatedRequest();
  const fresh = await state.fetch(request);
  assert.equal(fresh.status, 200);
  assert.equal(fresh.headers.get("Set-Cookie"), null);
  assert.deepEqual(state.renewalWrites, []);

  state.clock.now++;
  assertRenewalCookie(await state.fetch(request));
  const renewedExpiry = state.session().expires_at;
  state.clock.now += DAY - 1;
  const sameDay = await state.fetch(request);
  assert.equal(sameDay.status, 200);
  assert.equal(sameDay.headers.get("Set-Cookie"), null);
  assert.equal(state.session().expires_at, renewedExpiry);
  assert.deepEqual(state.renewalWrites, [1]);

  state.clock.now++;
  assertRenewalCookie(await state.fetch(request));
  assert.equal(state.session().expires_at, state.clock.now + TTL);
  assert.deepEqual(state.renewalWrites, [1, 1]);
});

test("an active session created more than 180 days ago can keep renewing", async (t) => {
  const createdAt = NOW - 400 * DAY;
  const state = fixture(t, { createdAt });
  const response = await state.fetch();
  assert.equal(response.status, 200);
  assertRenewalCookie(response);
  assert.equal(state.session().expires_at, NOW + TTL);
  assert.equal(state.session().created_at, createdAt);
});

test("expired, absent and invalid sessions are not revived", async (t) => {
  for (const scenario of ["expired", "expiry boundary", "missing cookie", "invalid token", "unknown token", "deleted session"]) {
    await t.test(scenario, async (t) => {
      const expiresAt = scenario === "expired" ? NOW - 1 : scenario === "expiry boundary" ? NOW : NOW + DAY;
      const state = fixture(t, { expiresAt });
      if (scenario === "deleted session") state.database.prepare("DELETE FROM sessions").run();
      const token = scenario === "missing cookie" ? null : scenario === "invalid token" ? "malformed"
        : scenario === "unknown token" ? "b".repeat(43) : TOKEN;
      const response = await state.fetch(authenticatedRequest(undefined, { token }));
      assert.equal(response.status, 401);
      assert.equal(response.headers.get("Set-Cookie"), null);
      assert.equal(state.session()?.expires_at, scenario === "deleted session" ? undefined : expiresAt);
      assert.deepEqual(state.renewalWrites, []);
    });
  }
});

test("logout deletes the session and clears its cookie without renewing it", async (t) => {
  const state = fixture(t);
  const response = await state.fetch(authenticatedRequest("/api/auth/logout", { method: "POST" }));
  assert.equal(response.status, 204);
  assert.equal(state.session(), undefined);
  assert.match(response.headers.get("Set-Cookie"), /__Host-ccfddl_session=;.*Max-Age=0/);
  assert.deepEqual(state.renewalWrites, []);
  assert.equal((await state.fetch()).status, 401);
});

test("email OAuth authorization does not renew the existing login session", async (t) => {
  const state = fixture(t);
  const response = await state.fetch(authenticatedRequest(
    "/api/auth/github?purpose=email&timezone=UTC&language=en",
  ));
  assert.equal(response.status, 302);
  assert.match(response.headers.get("Set-Cookie"), /^__Host-ccfddl_oauth=/);
  assert.doesNotMatch(response.headers.get("Set-Cookie"), /__Host-ccfddl_session=/);
  assert.equal(state.session().expires_at, NOW + DAY);
  assert.deepEqual(state.renewalWrites, []);
});

test("failed authenticated operations do not extend the session", async (t) => {
  for (const failure of ["validation", "database"]) {
    await t.test(failure, async (t) => {
      const state = fixture(t);
      t.mock.method(console, "error", () => {});
      if (failure === "database") {
        state.hooks.beforeFirst = (sql) => {
          if (sql.includes("FROM email_reminders")) throw new Error("Settings unavailable");
        };
      }
      const request = failure === "validation" ? authenticatedRequest(undefined, {
        method: "PUT", body: JSON.stringify({ timezone: "Invalid/Timezone", language: "en" }),
      }) : authenticatedRequest();
      const response = await state.fetch(request);
      assert.equal(response.status, failure === "validation" ? 400 : 500);
      assert.equal(response.headers.get("Set-Cookie"), null);
      assert.equal(state.session().expires_at, NOW + DAY);
      assert.deepEqual(state.renewalWrites, []);
    });
  }
});

test("a failed renewal write preserves the completed operation and original expiry", async (t) => {
  const state = fixture(t);
  let attempted = false;
  state.hooks.beforeRenewal = () => { attempted = true; throw new Error("Renewal unavailable"); };
  t.mock.method(console, "error", () => {});
  const response = await state.fetch();
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), SETTINGS);
  assert.ok(attempted);
  assert.equal(response.headers.get("Set-Cookie"), null);
  assert.equal(state.session().expires_at, NOW + DAY);
});

test("conditional renewal cannot overwrite concurrent revocation, expiry or renewal", async (t) => {
  for (const change of ["revocation", "expiry", "renewal"]) {
    await t.test(change, async (t) => {
      const state = fixture(t);
      state.hooks.beforeRenewal = () => {
        if (change === "revocation") state.database.prepare("DELETE FROM sessions WHERE token_hash = ?").run(TOKEN_HASH);
        else state.database.prepare("UPDATE sessions SET expires_at = ? WHERE token_hash = ?")
          .run(change === "expiry" ? NOW : NOW + TTL, TOKEN_HASH);
      };
      const response = await state.fetch();
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("Set-Cookie"), null);
      assert.deepEqual(state.renewalWrites, [0]);
      assert.equal(state.session()?.expires_at, change === "revocation" ? undefined : change === "expiry" ? NOW : NOW + TTL);
    });
  }
});

test("a session expiring during a successful handler is not extended", async (t) => {
  const state = fixture(t, { expiresAt: NOW + 1 });
  state.hooks.beforeFirst = (sql) => {
    if (sql.includes("FROM email_reminders")) state.clock.now += 2;
  };
  const response = await state.fetch();
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Set-Cookie"), null);
  assert.equal(state.session().expires_at, NOW + 1);
  assert.deepEqual(state.renewalWrites, [0]);
});

test("concurrent successful requests send only one renewal cookie", async (t) => {
  const state = fixture(t);
  const responses = await Promise.all([state.fetch(), state.fetch()]);
  assert.ok(responses.every((response) => response.status === 200));
  assert.equal(responses.filter((response) => response.headers.has("Set-Cookie")).length, 1);
  assert.equal(state.session().expires_at, NOW + TTL);
  assert.equal(state.renewalWrites.filter((changes) => changes === 1).length, 1);
});

test("bootstrap renews a reused Request independently and returns only public user fields", async (t) => {
  const state = fixture(t);
  state.database.exec(`
    CREATE TABLE conference_stars (conference_key TEXT, github_id INTEGER);
    CREATE TABLE conference_star_counts (conference_key TEXT, star_count INTEGER);
  `);
  const request = authenticatedRequest("/api/bootstrap");
  for (const renew of [true, false]) {
    const response = await state.fetch(request);
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), {
      user: { login: "reader", avatar_url: "https://example.org/avatar.png", profile_url: "https://github.com/reader" },
      counts: {}, starred: [],
    });
    if (renew) assertRenewalCookie(response);
    else assert.equal(response.headers.get("Set-Cookie"), null);
  }
  assert.deepEqual(state.renewalWrites, [1]);
});
