import assert from "node:assert/strict";
import test from "node:test";
import worker from "../src/index.js";

import {
  buildEmailDigest,
  renderEmailDigestHtml,
  runScheduledEmailDigests,
  validReminderTimezone,
  verifiedPrimaryEmail,
  unsubscribeSignature,
} from "../src/email_reminders.js";

test("uses only the verified primary GitHub address", () => {
  assert.equal(verifiedPrimaryEmail([
    { email: "other@example.com", verified: true, primary: false },
    { email: "main@example.com", verified: true, primary: true },
  ]), "main@example.com");
  assert.equal(verifiedPrimaryEmail([{ email: "main@example.com", verified: false, primary: true }]), null);
  assert.equal(validReminderTimezone("Asia/Shanghai"), true);
  assert.equal(validReminderTimezone("Bad/Timezone"), false);
});

test("requests user:email only for an explicit signed-in reminder opt-in", async () => {
  const env = {
    PUBLIC_ORIGIN: "https://ccfddl.com", SESSION_SECRET: "s".repeat(32),
    GITHUB_CLIENT_ID: "client", GITHUB_CLIENT_SECRET: "secret",
    RESEND_API_KEY: "sender", EMAIL_FROM: "reminders@example.com",
    DB: { prepare() { return { bind() { return { async first() { return { github_id: 42 }; } }; } }; } },
  };
  const base = "https://ccfddl.com/api/auth/github";
  const normal = await worker.fetch(new Request(base), env);
  assert.equal(new URL(normal.headers.get("Location")).searchParams.has("scope"), false);
  const consent = await worker.fetch(new Request(`${base}?purpose=email&timezone=Asia%2FShanghai&language=zh`, {
    headers: { Cookie: `__Host-ccfddl_session=${"a".repeat(43)}` },
  }), env);
  assert.equal(consent.status, 302);
  assert.equal(new URL(consent.headers.get("Location")).searchParams.get("scope"), "user:email");
  const anonymous = await worker.fetch(new Request(`${base}?purpose=email&timezone=UTC&language=en`), env);
  assert.equal(anonymous.status, 401);
});

test("email authorization stores the verified address and discards the GitHub token", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url) => {
    if (url.includes("access_token")) return Response.json({ access_token: "sensitive-oauth-token" });
    if (url.includes("/user/emails")) return Response.json([
      { email: "unverified@example.com", primary: false, verified: false },
      { email: "verified@example.com", primary: true, verified: true },
    ]);
    if (url.endsWith("/user")) return Response.json({
      id: 42, login: "reader", avatar_url: "https://example.com/avatar", html_url: "https://github.com/reader",
    });
    throw new Error(url);
  };
  let statements;
  const env = {
    PUBLIC_ORIGIN: "https://ccfddl.com", SESSION_SECRET: "s".repeat(32),
    GITHUB_CLIENT_ID: "client", GITHUB_CLIENT_SECRET: "secret",
    RESEND_API_KEY: "sender", EMAIL_FROM: "reminders@example.com",
    DB: {
      prepare(sql) { return {
        bind(...parameters) { return { sql, parameters, async first() { return { github_id: 42 }; } }; },
      }; },
      async batch(values) { statements = values; },
    },
  };
  const cookie = `__Host-ccfddl_session=${"a".repeat(43)}`;
  const start = await worker.fetch(new Request(
    "https://ccfddl.com/api/auth/github?purpose=email&timezone=Asia%2FShanghai&language=zh&return_to=%2F%3Femail_reminders%3D1",
    { headers: { Cookie: cookie } },
  ), env);
  const state = new URL(start.headers.get("Location")).searchParams.get("state");
  const oauthCookie = start.headers.get("Set-Cookie").split(";")[0];
  const response = await worker.fetch(new Request(
    `https://ccfddl.com/api/auth/github/callback?code=code&state=${state}`,
    { headers: { Cookie: oauthCookie } },
  ), env);
  assert.equal(response.status, 302);
  assert.equal(response.headers.get("Location"), "https://ccfddl.com/?email_reminders=1&email_status=enabled");
  assert.equal(statements.length, 6);
  assert.deepEqual(statements[5].parameters.slice(0, 4), [42, "verified@example.com", "Asia/Shanghai", "zh"]);
  assert.doesNotMatch(JSON.stringify(statements), /sensitive-oauth-token/);
});

test("changing reminder settings clears pending digests in the same D1 batch", async () => {
  let statements;
  const env = {
    PUBLIC_ORIGIN: "https://ccfddl.com",
    DB: {
      prepare(sql) { return {
        bind(...parameters) { return {
          sql, parameters,
          async first() {
            if (sql.includes("FROM sessions")) return { github_id: 42 };
            if (sql.includes("FROM email_reminders")) {
              return { email: "reader@example.com", timezone: "Europe/Paris", language: "en" };
            }
            throw new Error(sql);
          },
        }; },
      }; },
      async batch(values) {
        statements = values;
        return [{ meta: { changes: 1 } }, { meta: { changes: 1 } }];
      },
    },
  };
  const response = await worker.fetch(new Request("https://ccfddl.com/api/email/reminders", {
    method: "PUT",
    headers: {
      Origin: "https://ccfddl.com",
      Cookie: `__Host-ccfddl_session=${"a".repeat(43)}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ timezone: "Europe/Paris", language: "en" }),
  }), env);
  assert.equal(response.status, 200);
  assert.equal(statements.length, 2);
  assert.match(statements[0].sql, /UPDATE email_reminders SET timezone/);
  assert.deepEqual(statements[0].parameters.slice(0, 2), ["Europe/Paris", "en"]);
  assert.match(statements[1].sql, /DELETE FROM email_digest_sends WHERE github_id = \? AND status = 'pending'/);
  assert.deepEqual(statements[1].parameters, [42]);
});

test("signed unsubscribe link requires a POST to remove the reminder", async () => {
  let deleted = false;
  const secret = "s".repeat(32);
  const token = await unsubscribeSignature(42, "reader@example.com", secret);
  const env = {
    SESSION_SECRET: secret,
    DB: { prepare(sql) { return { bind() { return {
      async first() { return { email: "reader@example.com" }; },
      async run() { assert.match(sql, /DELETE FROM email_reminders/); deleted = true; },
    }; } }; } },
  };
  const url = `https://ccfddl.com/api/email/unsubscribe?id=42&token=${token}`;
  const page = await worker.fetch(new Request(url), env);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /<form method="post"/);
  assert.equal(deleted, false);
  const invalid = await worker.fetch(new Request(`${url}x`, { method: "POST" }), env);
  assert.equal(invalid.status, 404);
  assert.equal(deleted, false);
  const confirmed = await worker.fetch(new Request(url, { method: "POST" }), env);
  assert.equal(confirmed.status, 200);
  assert.equal(deleted, true);
});

test("combines the 7-day and 1-day events in the recipient's local calendar day", () => {
  const events = [
    { id: "iclr27", conference: "ICLR 2027", title: "ICLR Paper Submission", deadline_at: "2026-10-04T16:30:00Z", url: "https://iclr.cc/" },
    { id: "cvpr27", conference: "CVPR 2027", title: "CVPR Abstract Submission", deadline_at: "2026-09-28T16:30:00Z", url: "https://cvpr.thecvf.com/" },
    { id: "other27", title: "Other Deadline", deadline_at: "2026-09-28T16:30:00Z" },
  ];
  const now = Date.parse("2026-09-28T01:00:00Z"); // 09:00 in Shanghai.
  const digest = buildEmailDigest(events, new Set(["iclr27", "cvpr27"]), "Asia/Shanghai", "zh", now);
  assert.equal(digest.subject, "[ccf-deadlines] CVPR 2027、ICLR 2027 截止日期提醒");
  assert.match(digest.text, /距截止 7 天.*ICLR/);
  assert.match(digest.text, /距截止 1 天.*CVPR/);
  assert.doesNotMatch(digest.text, /Other Deadline/);
  assert.doesNotMatch(digest.text, /你好|你收藏的会议/);
  const english = buildEmailDigest(events, new Set(["cvpr27"]), "Asia/Shanghai", "en", now);
  assert.equal(english.subject, "[ccf-deadlines] CVPR 2027 Deadline reminders");
  assert.doesNotMatch(english.text, /Hello|The following deadlines/);
  const englishHtml = renderEmailDigestHtml(english, "en",
    "https://ccfddl.com/unsubscribe", "https://ccfddl.com");
  assert.match(englishHtml, /Email preferences/);
  assert.match(englishHtml, /Good luck with your submissions!<br>The CCFDDL maintainer team/);
  assert.doesNotMatch(englishHtml, /Hello|The following deadlines/);
  assert.equal(buildEmailDigest(events, new Set(["iclr27"]), "UTC", "en", now), null);
});

test("limits conference names in a combined subject", () => {
  const events = ["A", "B", "C", "D"].map((name) => ({
    id: name.toLowerCase(), conference: `${name} 2027`, title: `${name} Deadline`,
    deadline_at: "2026-10-05T00:00:00Z",
  }));
  const digest = buildEmailDigest(events, new Set(events.map((event) => event.id)),
    "Asia/Shanghai", "zh", Date.parse("2026-09-28T01:00:00Z"));
  assert.equal(digest.subject, "[ccf-deadlines] A 2027、B 2027、C 2027 等 1 个会议 截止日期提醒");
  assert.match(digest.text, /D Deadline/);
});

test("HTML reminder uses the card layout and escapes conference content", () => {
  const digest = buildEmailDigest([{
    id: "ecir27", conference: "ECIR 2027", title: "ECIR <2027> Paper Submission",
    deadline_at: "2026-10-05T00:00:00Z", url: "javascript:alert(1)",
  }], new Set(["ecir27"]), "Asia/Shanghai", "zh", Date.parse("2026-09-28T01:00:00Z"));
  assert.equal(digest.subject, "[ccf-deadlines] ECIR 2027 截止日期提醒");
  const html = renderEmailDigestHtml(digest, "zh",
    "https://ccfddl.com/api/email/unsubscribe?id=1&token=abc", "https://ccfddl.com");
  assert.match(html, /background:#f2f2f2/);
  assert.match(html, /border-top:3px solid #d44f3f/);
  assert.match(html, /截稿时间提醒/);
  assert.match(html, /ECIR &lt;2027&gt; Paper Submission/);
  assert.match(html, /祝投稿顺利！<br>The CCFDDL maintainer team/);
  assert.match(html, /@CCFDDL<\/span>&nbsp;·&nbsp;\s*<a href="https:\/\/ccfddl\.com\/api\/email\/unsubscribe/);
  assert.doesNotMatch(html, /你好|你收藏的会议/);
  assert.doesNotMatch(html, /<2027>|javascript:alert/);
  assert.match(html, /unsubscribe\?id=1&amp;token=abc/);
  assert.match(html, /\?email_reminders=1/);
});

test("cron sends one digest and does not send it again on a later tick", async (t) => {
  const originalFetch = globalThis.fetch;
  const sends = new Map();
  const outgoing = [];
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("deadline_events.json")) return Response.json([
      { id: "iclr27", title: "ICLR Deadline", deadline_at: "2026-10-05T00:00:00Z", url: "https://iclr.cc/" },
      { id: "cvpr27", title: "CVPR Deadline", deadline_at: "2026-09-29T00:00:00Z", url: "https://cvpr.thecvf.com/" },
    ]);
    assert.equal(url, "https://api.resend.com/emails");
    outgoing.push({ headers: options.headers, body: JSON.parse(options.body) });
    return Response.json({ id: "email-1" });
  };
  const env = {
    PUBLIC_ORIGIN: "https://ccfddl.com", SESSION_SECRET: "s".repeat(32),
    RESEND_API_KEY: "test", EMAIL_FROM: "CCFDDL <reminders@example.com>",
    DB: { prepare(sql) { return { bind(...args) { return {
      async all() {
        if (sql.includes("FROM email_reminders")) return { results: [{ github_id: 1, email: "reader@example.com", timezone: "Asia/Shanghai", language: "en" }] };
        if (sql.includes("FROM conference_stars")) return { results: [{ conference_key: "iclr27" }, { conference_key: "cvpr27" }] };
        throw new Error(sql);
      },
      async first() { return sends.get(`${args[0]}:${args[1]}`) ?? null; },
      async run() {
        const key = `${args[0]}:${args[1]}`;
        if (sql.includes("INSERT OR IGNORE")) sends.set(key, { payload_json: args[2], status: "pending" });
        else if (sql.includes("UPDATE email_digest_sends")) sends.set(`${args[2]}:${args[3]}`, { ...sends.get(`${args[2]}:${args[3]}`), status: "sent" });
        else throw new Error(sql);
      },
    }; } }; } },
  };
  const atNine = Date.parse("2026-09-28T01:00:00Z");
  assert.deepEqual(await runScheduledEmailDigests(env, atNine - 15 * 60_000), { sent: 0, failed: 0 });
  assert.deepEqual(await runScheduledEmailDigests(env, atNine), { sent: 1, failed: 0 });
  assert.equal(outgoing.length, 1);
  assert.match(outgoing[0].body.text, /ICLR Deadline/);
  assert.match(outgoing[0].body.text, /CVPR Deadline/);
  assert.match(outgoing[0].body.text, /api\/email\/unsubscribe/);
  assert.match(outgoing[0].body.html, /ICLR Deadline/);
  assert.match(outgoing[0].body.html, /CVPR Deadline/);
  assert.match(outgoing[0].body.html, /href="https:\/\/iclr\.cc\/"/);
  assert.match(outgoing[0].body.html, /api\/email\/unsubscribe/);
  assert.deepEqual(await runScheduledEmailDigests(env, atNine + 15 * 60_000), { sent: 0, failed: 0 });
  assert.equal(outgoing.length, 1);
});
