import {
  runScheduledEmailDigests,
  unsubscribeSignature,
  validReminderLanguage,
  validReminderTimezone,
  verifiedPrimaryEmail,
} from "./email_reminders.js";

const OAUTH_COOKIE = "__Host-ccfddl_oauth";
const SESSION_COOKIE = "__Host-ccfddl_session";
const OAUTH_TTL_SECONDS = 10 * 60;
const SESSION_TTL_SECONDS = 30 * 24 * 60 * 60;
const MESSAGE_MAX_CHARACTERS = 500;
const MESSAGE_MAX_LINES = 8;
const MESSAGE_PAGE_SIZE = 50;
const MESSAGE_REPLY_PAGE_SIZE = 20;
const MESSAGE_DAILY_LIMIT = 10;
const MESSAGE_LIKES_WINDOW_SECONDS = 30 * 24 * 60 * 60;
const MAX_JSON_BYTES = 8 * 1024;

export default {
  async fetch(request, env) {
    let response;
    try {
      await enforceRateLimit(request, env);
      response = await route(request, env);
    } catch (error) {
      if (error instanceof HttpError) {
        response = json({ error: error.message, ...(error.code ? { code: error.code } : {}) }, error.status);
      } else {
        console.error("Worker request failed", error?.name ?? "Error");
        response = json({ error: "Internal server error" }, 500);
      }
    }
    response.headers.set("X-Content-Type-Options", "nosniff");
    response.headers.set("Referrer-Policy", "no-referrer");
    if (!response.headers.has("Content-Security-Policy")) {
      response.headers.set("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'");
    }
    if (response.status === 429) response.headers.set("Retry-After", "60");
    return response;
  },
  async scheduled(controller, env) {
    return runScheduledEmailDigests(env, controller.scheduledTime);
  },
};

async function route(request, env) {
  const url = new URL(request.url);

  if (request.method === "GET" && url.pathname === "/api/health") {
    return json({ ok: true });
  }
  if (request.method === "GET" && url.pathname === "/api/auth/github") {
    return beginGithubLogin(request, env, url);
  }
  if (request.method === "GET" && url.pathname === "/api/auth/github/callback") {
    return finishGithubLogin(request, env, url);
  }
  if (request.method === "POST" && url.pathname === "/api/auth/logout") {
    assertTrustedOrigin(request, env);
    return logout(request, env);
  }
  if (request.method === "GET" && url.pathname === "/api/bootstrap") {
    return bootstrap(request, env);
  }
  if (request.method === "GET" && url.pathname === "/api/calendar/favorites.ics") {
    return favoritesCalendar(url, env);
  }
  if (url.pathname === "/api/email/reminders") {
    if (request.method === "GET") return emailReminderSettings(request, env);
    if (request.method === "PUT") {
      assertTrustedOrigin(request, env);
      return updateEmailReminderSettings(request, env);
    }
    if (request.method === "DELETE") {
      assertTrustedOrigin(request, env);
      return deleteEmailReminderSettings(request, env);
    }
  }
  if (url.pathname === "/api/email/unsubscribe" && ["GET", "POST"].includes(request.method)) {
    return unsubscribeEmail(request, env, url);
  }
  if (request.method === "GET" && url.pathname === "/api/messages") {
    return listMessages(request, env, url);
  }
  const messageRepliesMatch = url.pathname.match(
    /^\/api\/messages\/(\d+)\/replies$/,
  );
  if (request.method === "GET" && messageRepliesMatch) {
    return listMessageReplies(request, env, url, Number(messageRepliesMatch[1]));
  }
  if (request.method === "POST" && url.pathname === "/api/messages") {
    assertTrustedOrigin(request, env);
    return createMessage(request, env);
  }
  const messageLikeMatch = url.pathname.match(/^\/api\/messages\/(\d+)\/like$/);
  if (
    messageLikeMatch &&
    (request.method === "PUT" || request.method === "DELETE")
  ) {
    assertTrustedOrigin(request, env);
    return mutateMessageLike(request, env, Number(messageLikeMatch[1]));
  }
  if (request.method === "DELETE" && url.pathname.startsWith("/api/messages/")) {
    assertTrustedOrigin(request, env);
    return deleteMessage(request, env, url);
  }
  if (
    (request.method === "PUT" || request.method === "DELETE") &&
    url.pathname.startsWith("/api/stars/")
  ) {
    assertTrustedOrigin(request, env);
    return mutateStar(request, env, url);
  }

  return json({ error: "Not found" }, 404);
}

async function beginGithubLogin(request, env, url) {
  requireConfiguration(env);
  const purpose = url.searchParams.get("purpose");
  if (purpose && purpose !== "email") throw new HttpError(400, "Invalid GitHub authorization purpose.");
  let emailRequest = null;
  if (purpose === "email") {
    if (!env.RESEND_API_KEY || !env.EMAIL_FROM) throw new HttpError(503, "Email reminders are unavailable.");
    const user = await authenticatedUser(request, env);
    if (!user) throw new HttpError(401, "GitHub sign-in is required.");
    const timezone = url.searchParams.get("timezone");
    const language = url.searchParams.get("language");
    if (!validReminderTimezone(timezone) || !validReminderLanguage(language)) {
      throw new HttpError(400, "Invalid email reminder settings.");
    }
    emailRequest = { requester_id: user.github_id, timezone, language };
  }
  const state = randomToken(24);
  const verifier = randomToken(48);
  const challenge = await sha256Base64Url(verifier);
  const returnTo = sanitizeReturnTo(url.searchParams.get("return_to"));
  const payload = await signPayload(
    JSON.stringify({ state, verifier, returnTo, issued_at: unixTime(), emailRequest }),
    env.SESSION_SECRET,
  );
  const callback = `${env.PUBLIC_ORIGIN}/api/auth/github/callback`;
  const authorize = new URL("https://github.com/login/oauth/authorize");
  authorize.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  authorize.searchParams.set("redirect_uri", callback);
  authorize.searchParams.set("state", state);
  authorize.searchParams.set("code_challenge", challenge);
  authorize.searchParams.set("code_challenge_method", "S256");
  if (emailRequest) authorize.searchParams.set("scope", "user:email");

  return redirect(authorize.toString(), [
    serializeCookie(OAUTH_COOKIE, payload, OAUTH_TTL_SECONDS, request),
  ]);
}

async function finishGithubLogin(request, env, url) {
  requireConfiguration(env);
  const signedPayload = parseCookies(request.headers.get("Cookie"))[cookieName(OAUTH_COOKIE, request)];
  const payload = signedPayload && signedPayload.length <= 4096
    ? await verifyPayload(signedPayload, env.SESSION_SECRET)
    : null;
  if (!payload) {
    return json({ error: "The GitHub login request has expired." }, 400);
  }

  const oauth = JSON.parse(payload);
  if (!isFreshOAuthPayload(oauth)) {
    return json({ error: "The GitHub login request has expired." }, 400);
  }
  const state = url.searchParams.get("state");
  const code = url.searchParams.get("code");
  if (!state || !safeEqual(state, oauth.state)) {
    return json({ error: "Invalid GitHub OAuth state." }, 400);
  }
  if (url.searchParams.get("error") === "access_denied" && oauth.emailRequest) {
    return redirect(emailReturnUrl(env, oauth.returnTo, "denied"), [
      serializeCookie(OAUTH_COOKIE, "", 0, request),
    ]);
  }
  if (!code) return json({ error: "Invalid GitHub OAuth state." }, 400);

  const tokenResponse = await githubLoginStep("token_request", () => fetchGithubWithoutRedirects("https://github.com/login/oauth/access_token", {
    method: "POST",
    signal: AbortSignal.timeout(10_000),
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": "ccfddl-api",
    },
    body: JSON.stringify({
      client_id: env.GITHUB_CLIENT_ID,
      client_secret: env.GITHUB_CLIENT_SECRET,
      code,
      redirect_uri: `${env.PUBLIC_ORIGIN}/api/auth/github/callback`,
      code_verifier: oauth.verifier,
    }),
  }));
  const token = await githubLoginStep("token_response", () => tokenResponse.json());
  if (!tokenResponse.ok || !token.access_token) {
    console.error("GitHub token exchange failed", token.error);
    return json({ error: "GitHub login failed." }, 502);
  }

  const userResponse = await githubLoginStep("profile_request", () => fetchGithubWithoutRedirects("https://api.github.com/user", {
    signal: AbortSignal.timeout(10_000),
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token.access_token}`,
      "User-Agent": "ccfddl-api",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  }));
  const githubUser = await githubLoginStep("profile_response", () => userResponse.json());
  if (!userResponse.ok || !Number.isInteger(githubUser.id)) {
    return json({ error: "Unable to read the GitHub profile." }, 502);
  }

  let reminderEmail = null;
  if (oauth.emailRequest) {
    const settings = oauth.emailRequest;
    if (githubUser.id !== settings.requester_id || !validReminderTimezone(settings.timezone)
      || !validReminderLanguage(settings.language)) {
      return redirect(emailReturnUrl(env, oauth.returnTo, "account_mismatch"), [
        serializeCookie(OAUTH_COOKIE, "", 0, request),
      ]);
    }
    const emailResponse = await githubLoginStep("email_request", () => fetchGithubWithoutRedirects(
      "https://api.github.com/user/emails?per_page=100", {
        signal: AbortSignal.timeout(10_000),
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${token.access_token}`,
          "User-Agent": "ccfddl-api",
          "X-GitHub-Api-Version": "2022-11-28",
        },
      },
    ));
    const addresses = emailResponse.ok
      ? await githubLoginStep("email_response", () => emailResponse.json()) : null;
    reminderEmail = verifiedPrimaryEmail(addresses);
    if (!reminderEmail) {
      return redirect(emailReturnUrl(env, oauth.returnTo, "email_unavailable"), [
        serializeCookie(OAUTH_COOKIE, "", 0, request),
      ]);
    }
  }

  const now = unixTime();
  const sessionToken = randomToken(32);
  const sessionHash = await sha256Hex(sessionToken);
  const statements = [
    env.DB.prepare("DELETE FROM sessions WHERE expires_at <= ?").bind(now),
    env.DB.prepare(
      `DELETE FROM sessions WHERE github_id = ? AND token_hash NOT IN (
         SELECT token_hash FROM sessions WHERE github_id = ?
         ORDER BY created_at DESC, token_hash LIMIT 19
       )`,
    ).bind(githubUser.id, githubUser.id),
    env.DB.prepare(
      `INSERT INTO users (github_id, login, avatar_url, profile_url, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(github_id) DO UPDATE SET
         login = excluded.login,
         avatar_url = excluded.avatar_url,
         profile_url = excluded.profile_url,
         updated_at = excluded.updated_at`,
    ).bind(
      githubUser.id,
      githubUser.login,
      githubUser.avatar_url,
      githubUser.html_url,
      now,
      now,
    ),
    env.DB.prepare(
      "INSERT INTO sessions (token_hash, github_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
    ).bind(sessionHash, githubUser.id, now + SESSION_TTL_SECONDS, now),
  ];
  if (reminderEmail) {
    statements.push(env.DB.prepare(
      "DELETE FROM email_digest_sends WHERE github_id = ? AND status = 'pending'",
    ).bind(githubUser.id));
    statements.push(env.DB.prepare(
      `INSERT INTO email_reminders (github_id, email, timezone, language, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(github_id) DO UPDATE SET
         email = excluded.email,
         timezone = excluded.timezone,
         language = excluded.language,
         updated_at = excluded.updated_at`,
    ).bind(githubUser.id, reminderEmail, oauth.emailRequest.timezone, oauth.emailRequest.language, now, now));
  }
  await githubLoginStep("session_storage", () => env.DB.batch(statements));

  return redirect(reminderEmail
    ? emailReturnUrl(env, oauth.returnTo, "enabled")
    : `${env.PUBLIC_ORIGIN}${sanitizeReturnTo(oauth.returnTo)}`, [
    serializeCookie(OAUTH_COOKIE, "", 0, request),
    serializeCookie(SESSION_COOKIE, sessionToken, SESSION_TTL_SECONDS, request),
  ]);
}

function emailReturnUrl(env, returnTo, status) {
  const destination = new URL(sanitizeReturnTo(returnTo), env.PUBLIC_ORIGIN);
  destination.searchParams.set("email_status", status);
  return destination.toString();
}

async function fetchGithubWithoutRedirects(url, options) {
  // workerd does not support redirect: "error". Manual mode preserves the
  // no-redirect policy without forwarding OAuth secrets to another endpoint.
  const response = await fetch(url, { ...options, redirect: "manual" });
  if (response.status >= 300 && response.status < 400) {
    await response.body?.cancel();
    throw new TypeError("GitHub redirect rejected");
  }
  return response;
}

async function githubLoginStep(stage, operation) {
  try {
    return await operation();
  } catch (error) {
    // Record the failing stage without OAuth codes, tokens, cookies, or secrets.
    const reason = error?.name === "TimeoutError" ? "timeout"
      : error?.name === "AbortError" ? "aborted"
      : error?.name === "SyntaxError" ? "invalid_json"
      : error?.name === "TypeError" && /redirect/i.test(error.message ?? "") ? "redirect_rejected"
      : error?.name === "TypeError" ? "network_error" : "failed";
    const code = `github_${stage}_${reason}`;
    console.error("GitHub login step failed", stage, code);
    const message = stage === "session_storage"
      ? "Unable to save the GitHub login session."
      : "Unable to contact GitHub or read its response. Please try signing in again.";
    throw new HttpError(stage === "session_storage" ? 500 : 502, message, code);
  }
}

async function bootstrap(request, env) {
  const user = await authenticatedUser(request, env);
  const countRows = await env.DB.prepare(
    "SELECT conference_key, COUNT(*) AS count FROM conference_stars GROUP BY conference_key",
  ).all();
  let starred = [];
  if (user) {
    const starredRows = await env.DB.prepare(
      "SELECT conference_key FROM conference_stars WHERE github_id = ?",
    )
      .bind(user.github_id)
      .all();
    starred = starredRows.results.map((row) => row.conference_key);
  }

  return json({
    user: user
      ? {
          login: user.login,
          avatar_url: user.avatar_url,
          profile_url: user.profile_url,
        }
      : null,
    counts: Object.fromEntries(
      countRows.results.map((row) => [row.conference_key, Number(row.count)]),
    ),
    starred,
  });
}

async function favoritesCalendar(url, env) {
  const ids = url.searchParams.getAll("id");
  const lang = url.searchParams.get("lang") ?? "en";
  if (ids.length === 0 || ids.length > 100 || !ids.every(isValidConferenceKey) || !["en", "zh"].includes(lang)) {
    throw new HttpError(400, "Select 1 to 100 valid conference editions.");
  }
  const sourceUrl = `${env.PUBLIC_ORIGIN}/conference/deadlines_${lang}.ics`;
  const source = await fetch(sourceUrl, { redirect: "manual" });
  if (!source.ok || source.status >= 300) {
    throw new HttpError(503, "Conference calendar is temporarily unavailable.");
  }
  const calendar = filterFavoritesCalendar(await source.text(), new Set(ids));
  return new Response(calendar, {
    headers: {
      "Content-Type": "text/calendar; charset=utf-8",
      "Content-Disposition": 'inline; filename="ccfddl-favorites.ics"',
      "Cache-Control": "public, max-age=3600",
    },
  });
}

async function emailReminderSettings(request, env) {
  const user = await authenticatedUser(request, env);
  if (!user) throw new HttpError(401, "GitHub sign-in is required.");
  const settings = await env.DB.prepare(
    "SELECT email, timezone, language, daily_enabled FROM email_reminders WHERE github_id = ?",
  ).bind(user.github_id).first();
  return json({
    available: Boolean(env.RESEND_API_KEY && env.EMAIL_FROM),
    enabled: Boolean(settings),
    email: settings?.email ?? null,
    timezone: settings?.timezone ?? null,
    language: settings?.language ?? null,
    daily_enabled: Boolean(settings?.daily_enabled),
    reminder_days: [7, 1],
    send_hour: 9,
  });
}

async function updateEmailReminderSettings(request, env) {
  const user = await authenticatedUser(request, env);
  if (!user) throw new HttpError(401, "GitHub sign-in is required.");
  const body = await readJsonBody(request);
  if (!validReminderTimezone(body?.timezone) || !validReminderLanguage(body?.language)
    || (body?.daily_enabled !== undefined && typeof body.daily_enabled !== "boolean")) {
    throw new HttpError(400, "Invalid email reminder settings.");
  }
  const dailyEnabled = body.daily_enabled === undefined ? null : Number(body.daily_enabled);
  const results = await env.DB.batch([
    env.DB.prepare(
      "UPDATE email_reminders SET timezone = ?, language = ?, daily_enabled = COALESCE(?, daily_enabled), updated_at = ? WHERE github_id = ?",
    ).bind(body.timezone, body.language, dailyEnabled, unixTime(), user.github_id),
    env.DB.prepare(
      "DELETE FROM email_digest_sends WHERE github_id = ? AND status = 'pending'",
    ).bind(user.github_id),
  ]);
  if (results[0].meta?.changes !== 1) throw new HttpError(404, "Enable email reminders first.");
  return emailReminderSettings(request, env);
}

async function deleteEmailReminderSettings(request, env) {
  const user = await authenticatedUser(request, env);
  if (!user) throw new HttpError(401, "GitHub sign-in is required.");
  await env.DB.prepare("DELETE FROM email_reminders WHERE github_id = ?").bind(user.github_id).run();
  return json({ enabled: false });
}

async function unsubscribeEmail(request, env, url) {
  const githubId = Number(url.searchParams.get("id"));
  const token = url.searchParams.get("token");
  if (!Number.isSafeInteger(githubId) || githubId <= 0 || !/^[A-Za-z0-9_-]{43}$/.test(token ?? "")) {
    throw new HttpError(404, "Subscription not found.");
  }
  const row = await env.DB.prepare("SELECT email FROM email_reminders WHERE github_id = ?")
    .bind(githubId).first();
  if (!row || !safeEqual(token, await unsubscribeSignature(githubId, row.email, env.SESSION_SECRET))) {
    throw new HttpError(404, "Subscription not found.");
  }
  if (request.method === "POST") {
    await env.DB.prepare("DELETE FROM email_reminders WHERE github_id = ?").bind(githubId).run();
  }
  const body = request.method === "POST"
    ? "<p>Email reminders are now off. / 邮件提醒已关闭。</p>"
    : `<p>Stop CCFDDL email reminders? / 关闭 CCFDDL 邮件提醒？</p>
       <form method="post" action="${url.pathname}${url.search}"><button type="submit">Unsubscribe / 取消订阅</button></form>`;
  return new Response(`<!doctype html><html><meta charset="utf-8"><title>CCFDDL email reminders</title><body>${body}</body></html>`, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
    },
  });
}

export function filterFavoritesCalendar(calendar, selectedIds) {
  const lines = calendar.split(/\r?\n/);
  if (lines[0] !== "BEGIN:VCALENDAR" || !lines.includes("END:VCALENDAR") || !calendar.includes("X-CCFDDL-ID:")) {
    throw new HttpError(503, "Conference calendar is invalid.");
  }
  const filtered = [];
  let event = null;
  for (const line of lines) {
    if (line === "BEGIN:VEVENT") {
      event = [line];
    } else if (event) {
      event.push(line);
      if (line === "END:VEVENT") {
        if (event.some((item) => item.startsWith("X-CCFDDL-ID:") && selectedIds.has(item.slice(12)))) {
          filtered.push(...event);
        }
        event = null;
      }
    } else {
      filtered.push(line);
    }
  }
  if (event) throw new HttpError(503, "Conference calendar is invalid.");
  return filtered.join("\r\n");
}

async function mutateStar(request, env, url) {
  const user = await authenticatedUser(request, env);
  if (!user) {
    return json({ error: "GitHub sign-in is required." }, 401);
  }

  let conferenceKey;
  try {
    conferenceKey = decodeURIComponent(url.pathname.slice("/api/stars/".length));
  } catch {
    return json({ error: "Invalid conference key." }, 400);
  }
  if (!isValidConferenceKey(conferenceKey)) {
    return json({ error: "Invalid conference key." }, 400);
  }

  if (request.method === "PUT") {
    await env.DB.prepare(
      "INSERT OR IGNORE INTO conference_stars (conference_key, github_id, created_at) VALUES (?, ?, ?)",
    )
      .bind(conferenceKey, user.github_id, unixTime())
      .run();
  } else {
    await env.DB.prepare(
      "DELETE FROM conference_stars WHERE conference_key = ? AND github_id = ?",
    )
      .bind(conferenceKey, user.github_id)
      .run();
  }

  const row = await env.DB.prepare(
    "SELECT COUNT(*) AS count FROM conference_stars WHERE conference_key = ?",
  )
    .bind(conferenceKey)
    .first();
  return json({
    count: Number(row?.count ?? 0),
    starred: request.method === "PUT",
  });
}

async function listMessages(request, env, url) {
  const sort = url.searchParams.get("sort") ?? "latest";
  if (!["latest", "likes", "mine"].includes(sort)) {
    throw new HttpError(400, "Invalid message sort.");
  }
  const offset = parseMessageOffset(url);

  const user = await authenticatedUser(request, env);
  if (offset > 0 && !user) {
    throw new HttpError(401, "GitHub sign-in is required to browse older messages.");
  }
  if (sort === "mine" && !user) {
    throw new HttpError(401, "GitHub sign-in is required to browse your messages.");
  }

  let statement = env.DB.prepare(
    `SELECT wall_messages.id, wall_messages.github_id, wall_messages.body,
            wall_messages.created_at, users.login, users.avatar_url, users.profile_url,
            (SELECT COUNT(*) FROM wall_message_likes
             WHERE wall_message_likes.message_id = wall_messages.id) AS like_count,
            EXISTS(SELECT 1 FROM wall_message_likes
                   WHERE wall_message_likes.message_id = wall_messages.id
                     AND wall_message_likes.github_id = ?) AS liked_by_me,
            (SELECT COUNT(*) FROM wall_messages AS replies
             WHERE replies.parent_id = wall_messages.id) AS reply_count
     FROM wall_messages
     JOIN users ON users.github_id = wall_messages.github_id
     WHERE wall_messages.parent_id IS NULL
     ${sort === "likes" ? "AND wall_messages.created_at >= ?" : ""}
     ${sort === "mine" ? "AND wall_messages.github_id = ?" : ""}
     ORDER BY ${sort === "likes" ? "like_count DESC," : ""} wall_messages.id DESC
     LIMIT ? OFFSET ?`,
  );
  if (sort === "mine") {
    statement = statement.bind(
      user.github_id,
      user.github_id,
      MESSAGE_PAGE_SIZE + 1,
      offset,
    );
  } else if (sort === "likes") {
    statement = statement.bind(
      user?.github_id ?? -1,
      messageLikesCutoff(),
      MESSAGE_PAGE_SIZE + 1,
      offset,
    );
  } else {
    statement = statement.bind(
      user?.github_id ?? -1,
      MESSAGE_PAGE_SIZE + 1,
      offset,
    );
  }
  const rows = await statement.all();
  const hasMore = rows.results.length > MESSAGE_PAGE_SIZE;
  const page = rows.results.slice(0, MESSAGE_PAGE_SIZE);

  return json({
    messages: page.map((row) => ({
      id: Number(row.id),
      body: row.body,
      created_at: Number(row.created_at),
      author: {
        login: row.login,
        avatar_url: row.avatar_url,
        profile_url: row.profile_url,
      },
      can_delete: Boolean(user && Number(row.github_id) === Number(user.github_id)),
      like_count: Number(row.like_count),
      liked_by_me: Boolean(Number(row.liked_by_me)),
      parent_id: null,
      reply_count: Number(row.reply_count),
    })),
    next_cursor: user && hasMore ? offset + MESSAGE_PAGE_SIZE : null,
  });
}

async function listMessageReplies(request, env, url, messageId) {
  if (!Number.isSafeInteger(messageId) || messageId < 1) {
    throw new HttpError(400, "Invalid message ID.");
  }
  const parent = await env.DB.prepare(
    "SELECT parent_id FROM wall_messages WHERE id = ?",
  )
    .bind(messageId)
    .first();
  if (!parent) {
    throw new HttpError(404, "Message not found.");
  }
  if (parent.parent_id !== null) {
    throw new HttpError(400, "Replies can only be listed for a top-level message.");
  }

  const offset = parseMessageOffset(url);
  const user = await authenticatedUser(request, env);
  if (offset > 0 && !user) {
    throw new HttpError(401, "GitHub sign-in is required to browse older replies.");
  }

  const rows = await env.DB.prepare(
    `SELECT wall_messages.id, wall_messages.github_id, wall_messages.body,
            wall_messages.created_at, users.login, users.avatar_url, users.profile_url,
            (SELECT COUNT(*) FROM wall_message_likes
             WHERE wall_message_likes.message_id = wall_messages.id) AS like_count,
            EXISTS(SELECT 1 FROM wall_message_likes
                   WHERE wall_message_likes.message_id = wall_messages.id
                     AND wall_message_likes.github_id = ?) AS liked_by_me
     FROM wall_messages
     JOIN users ON users.github_id = wall_messages.github_id
     WHERE wall_messages.parent_id = ?
     ORDER BY wall_messages.id DESC
     LIMIT ? OFFSET ?`,
  )
    .bind(
      user?.github_id ?? -1,
      messageId,
      MESSAGE_REPLY_PAGE_SIZE + 1,
      offset,
    )
    .all();
  const hasMore = rows.results.length > MESSAGE_REPLY_PAGE_SIZE;
  const page = rows.results.slice(0, MESSAGE_REPLY_PAGE_SIZE);

  return json({
    messages: page.map((row) => ({
      id: Number(row.id),
      body: row.body,
      created_at: Number(row.created_at),
      author: {
        login: row.login,
        avatar_url: row.avatar_url,
        profile_url: row.profile_url,
      },
      can_delete: Boolean(user && Number(row.github_id) === Number(user.github_id)),
      like_count: Number(row.like_count),
      liked_by_me: Boolean(Number(row.liked_by_me)),
      parent_id: messageId,
      reply_count: 0,
    })),
    next_cursor: user && hasMore ? offset + MESSAGE_REPLY_PAGE_SIZE : null,
  });
}

function parseMessageOffset(url) {
  const value = url.searchParams.get("offset");
  if (value === null) return 0;
  if (!/^\d+$/.test(value)) {
    throw new HttpError(400, "Invalid message cursor.");
  }
  const offset = Number(value);
  if (!Number.isSafeInteger(offset) || offset < 0) {
    throw new HttpError(400, "Invalid message cursor.");
  }
  return offset;
}

async function createMessage(request, env) {
  const user = await authenticatedUser(request, env);
  if (!user) {
    return json({ error: "GitHub sign-in is required." }, 401);
  }

  const payload = await readJsonBody(request);
  const body = normalizeWallMessage(payload?.body);
  if (!body) {
    throw new HttpError(
      400,
      `Messages must contain 1-${MESSAGE_MAX_CHARACTERS} characters and at most ${MESSAGE_MAX_LINES} lines.`,
    );
  }

  const parentId = payload?.parent_id ?? null;
  if (
    parentId !== null &&
    (!Number.isSafeInteger(parentId) || parentId < 1)
  ) {
    throw new HttpError(400, "Invalid parent message ID.");
  }
  if (parentId !== null) {
    const parent = await env.DB.prepare(
      "SELECT parent_id FROM wall_messages WHERE id = ?",
    )
      .bind(parentId)
      .first();
    if (!parent) {
      throw new HttpError(404, "Parent message not found.");
    }
    if (parent.parent_id !== null) {
      throw new HttpError(400, "Replies can only target a top-level message.");
    }
  }

  const now = unixTime();
  let result;
  try {
    // The database trigger reserves the quota and cooldown in the same transaction.
    result = await env.DB.prepare(
      "INSERT INTO wall_messages (github_id, body, created_at, parent_id) VALUES (?, ?, ?, ?)",
    )
      .bind(user.github_id, body, now, parentId)
      .run();
  } catch (error) {
    if (String(error.message).includes("wall_post_cooldown")) {
      throw new HttpError(429, "Please wait before posting another message.");
    }
    if (String(error.message).includes("wall_daily_limit")) {
      throw new HttpError(429, `Each GitHub account can post up to ${MESSAGE_DAILY_LIMIT} messages per UTC day.`);
    }
    throw error;
  }

  return json(
    {
      message: {
        id: Number(result.meta.last_row_id),
        body,
        created_at: now,
        author: {
          login: user.login,
          avatar_url: user.avatar_url,
          profile_url: user.profile_url,
        },
        can_delete: true,
        like_count: 0,
        liked_by_me: false,
        parent_id: parentId,
        reply_count: 0,
      },
    },
    201,
  );
}

async function mutateMessageLike(request, env, messageId) {
  if (!Number.isSafeInteger(messageId) || messageId < 1) {
    throw new HttpError(400, "Invalid message ID.");
  }
  const user = await authenticatedUser(request, env);
  if (!user) {
    throw new HttpError(401, "GitHub sign-in is required.");
  }

  const message = await env.DB.prepare(
    "SELECT github_id FROM wall_messages WHERE id = ?",
  )
    .bind(messageId)
    .first();
  if (!message) {
    throw new HttpError(404, "Message not found.");
  }

  if (request.method === "PUT") {
    await env.DB.prepare(
      "INSERT OR IGNORE INTO wall_message_likes (message_id, github_id, created_at) VALUES (?, ?, ?)",
    )
      .bind(messageId, user.github_id, unixTime())
      .run();
  } else {
    await env.DB.prepare(
      "DELETE FROM wall_message_likes WHERE message_id = ? AND github_id = ?",
    )
      .bind(messageId, user.github_id)
      .run();
  }

  const row = await env.DB.prepare(
    "SELECT COUNT(*) AS count FROM wall_message_likes WHERE message_id = ?",
  )
    .bind(messageId)
    .first();
  return json({
    count: Number(row?.count ?? 0),
    liked: request.method === "PUT",
  });
}

async function deleteMessage(request, env, url) {
  const user = await authenticatedUser(request, env);
  if (!user) {
    return json({ error: "GitHub sign-in is required." }, 401);
  }

  const rawId = url.pathname.slice("/api/messages/".length);
  if (!/^\d+$/.test(rawId)) {
    throw new HttpError(400, "Invalid message ID.");
  }
  const messageId = Number(rawId);
  if (!Number.isSafeInteger(messageId) || messageId < 1) {
    throw new HttpError(400, "Invalid message ID.");
  }

  const result = await env.DB.prepare(
    "DELETE FROM wall_messages WHERE id = ? AND github_id = ?",
  )
    .bind(messageId, user.github_id)
    .run();
  if (Number(result.meta.changes) === 0) {
    throw new HttpError(404, "Message not found.");
  }

  return new Response(null, {
    status: 204,
    headers: { "Cache-Control": "no-store" },
  });
}

async function logout(request, env) {
  const token = parseCookies(request.headers.get("Cookie"))[cookieName(SESSION_COOKIE, request)];
  if (token) {
    await env.DB.prepare("DELETE FROM sessions WHERE token_hash = ?")
      .bind(await sha256Hex(token))
      .run();
  }
  return new Response(null, {
    status: 204,
    headers: {
      "Set-Cookie": serializeCookie(SESSION_COOKIE, "", 0, request),
      "Cache-Control": "no-store",
    },
  });
}

async function authenticatedUser(request, env) {
  const token = parseCookies(request.headers.get("Cookie"))[cookieName(SESSION_COOKIE, request)];
  if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) return null;
  const user = await env.DB.prepare(
    `SELECT users.github_id, users.login, users.avatar_url, users.profile_url
     FROM sessions JOIN users ON users.github_id = sessions.github_id
     WHERE sessions.token_hash = ? AND sessions.expires_at > ?`,
  )
    .bind(await sha256Hex(token), unixTime())
    .first();
  if (user && ["POST", "PUT", "DELETE"].includes(request.method) && env.USER_WRITE_LIMITER) {
    const { success } = await env.USER_WRITE_LIMITER.limit({ key: String(user.github_id) });
    if (!success) throw new HttpError(429, "Too many requests. Please try again later.");
  }
  return user;
}

function requireConfiguration(env) {
  for (const key of [
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "SESSION_SECRET",
    "PUBLIC_ORIGIN",
  ]) {
    if (!env[key]) throw new Error(`Missing Worker configuration: ${key}`);
  }
  if (new TextEncoder().encode(env.SESSION_SECRET).length < 32) {
    throw new Error("SESSION_SECRET must contain at least 32 bytes.");
  }
  const origin = new URL(env.PUBLIC_ORIGIN);
  const localHttp = origin.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname);
  if (origin.origin !== env.PUBLIC_ORIGIN || (origin.protocol !== "https:" && !localHttp)) {
    throw new Error("PUBLIC_ORIGIN must be a valid origin.");
  }
}

function assertTrustedOrigin(request, env) {
  const origin = request.headers.get("Origin");
  const fetchSite = request.headers.get("Sec-Fetch-Site");
  if (origin !== env.PUBLIC_ORIGIN || (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none")) {
    throw new HttpError(403, "Untrusted request origin.");
  }
}

class HttpError extends Error {
  constructor(status, message, code = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function json(body, status = 200) {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}

function redirect(location, cookies = []) {
  const headers = new Headers({ Location: location, "Cache-Control": "no-store" });
  for (const cookie of cookies) headers.append("Set-Cookie", cookie);
  return new Response(null, { status: 302, headers });
}

function serializeCookie(name, value, maxAge, request) {
  const secure = new URL(request.url).protocol === "https:" ? "; Secure" : "";
  return `${cookieName(name, request)}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

function cookieName(name, request) {
  // The host prefix prevents a sibling subdomain from injecting login cookies.
  return new URL(request.url).protocol === "https:" ? name : name.replace(/^__Host-/, "");
}

export function parseCookies(header) {
  return Object.fromEntries(
    (header ?? "")
      .split(";")
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const separator = part.indexOf("=");
        return separator < 0
          ? [part, ""]
          : [part.slice(0, separator), part.slice(separator + 1)];
      }),
  );
}

export function sanitizeReturnTo(value) {
  return typeof value === "string" &&
    value.startsWith("/") &&
    !value.startsWith("//") &&
    !/[\\\u0000-\u0020\u007f]/.test(value) &&
    value.length <= 2048
    ? value
    : "/";
}

export function isFreshOAuthPayload(payload, now = unixTime()) {
  return payload && Number.isInteger(payload.issued_at)
    && payload.issued_at <= now + 30
    && now - payload.issued_at < OAUTH_TTL_SECONDS
    && typeof payload.state === "string" && /^[A-Za-z0-9_-]{32}$/.test(payload.state)
    && typeof payload.verifier === "string" && /^[A-Za-z0-9_-]{64}$/.test(payload.verifier);
}

async function enforceRateLimit(request, env) {
  const url = new URL(request.url);
  if (url.pathname === "/api/health") return;
  const ip = request.headers.get("CF-Connecting-IP");
  // CF-Connecting-IP is supplied by Cloudflare, not by a client on the deployed route.
  if (!ip) return;
  const limiter = url.pathname.startsWith("/api/auth/github") ? env.AUTH_RATE_LIMITER : env.API_RATE_LIMITER;
  if (limiter) {
    const { success } = await limiter.limit({ key: ip });
    if (!success) throw new HttpError(429, "Too many requests. Please try again later.");
  }
}

export async function readJsonBody(request) {
  if (request.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
    throw new HttpError(415, "Content-Type must be application/json.");
  }
  if (Number(request.headers.get("Content-Length")) > MAX_JSON_BYTES) {
    throw new HttpError(413, "Request body is too large.");
  }
  if (!request.body) throw new HttpError(400, "Invalid JSON body.");
  const reader = request.body.getReader();
  const chunks = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > MAX_JSON_BYTES) {
        await reader.cancel();
        throw new HttpError(413, "Request body is too large.");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    throw new HttpError(400, "Invalid JSON body.");
  }
}

export function isValidConferenceKey(value) {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= 100 &&
    /^[A-Za-z0-9][A-Za-z0-9._&+'-]*$/.test(value)
  );
}

export function normalizeWallMessage(value) {
  if (typeof value !== "string") return null;
  const message = value.replace(/\r\n?/g, "\n").trim();
  const characterCount = Array.from(message).length;
  const lineCount = message ? message.split("\n").length : 0;
  const hasControlCharacters = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(
    message,
  );
  return characterCount >= 1 &&
    characterCount <= MESSAGE_MAX_CHARACTERS &&
    lineCount <= MESSAGE_MAX_LINES &&
    !hasControlCharacters
    ? message
    : null;
}

export function utcDayStart(timestamp) {
  return timestamp - (timestamp % (24 * 60 * 60));
}

export function messageLikesCutoff(timestamp = unixTime()) {
  return timestamp - MESSAGE_LIKES_WINDOW_SECONDS;
}

async function signPayload(payload, secret) {
  const encoded = base64Url(new TextEncoder().encode(payload));
  const signature = await hmac(encoded, secret);
  return `${encoded}.${signature}`;
}

async function verifyPayload(value, secret) {
  const separator = value.lastIndexOf(".");
  if (separator < 1) return null;
  const encoded = value.slice(0, separator);
  const signature = value.slice(separator + 1);
  const expected = await hmac(encoded, secret);
  if (!safeEqual(signature, expected)) return null;
  try {
    return new TextDecoder().decode(base64UrlDecode(encoded));
  } catch {
    return null;
  }
}

async function hmac(value, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return base64Url(
    new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value))),
  );
}

async function sha256Hex(value) {
  const digest = new Uint8Array(
    await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)),
  );
  return [...digest].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function sha256Base64Url(value) {
  return base64Url(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)),
    ),
  );
}

function randomToken(size) {
  return base64Url(crypto.getRandomValues(new Uint8Array(size)));
}

function base64Url(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function base64UrlDecode(value) {
  const padded = value.replaceAll("-", "+").replaceAll("_", "/").padEnd(
    Math.ceil(value.length / 4) * 4,
    "=",
  );
  const binary = atob(padded);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function safeEqual(left, right) {
  if (typeof left !== "string" || typeof right !== "string" || left.length !== right.length) {
    return false;
  }
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function unixTime() {
  return Math.floor(Date.now() / 1000);
}
