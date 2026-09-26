const OAUTH_COOKIE = "ccfddl_oauth";
const SESSION_COOKIE = "ccfddl_session";
const OAUTH_TTL_SECONDS = 10 * 60;
const SESSION_TTL_SECONDS = 30 * 24 * 60 * 60;

export default {
  async fetch(request, env) {
    try {
      return await route(request, env);
    } catch (error) {
      if (error instanceof HttpError) {
        return json({ error: error.message }, error.status);
      }
      console.error(error);
      return json({ error: "Internal server error" }, 500);
    }
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
  const state = randomToken(24);
  const verifier = randomToken(48);
  const challenge = await sha256Base64Url(verifier);
  const returnTo = sanitizeReturnTo(url.searchParams.get("return_to"));
  const payload = await signPayload(
    JSON.stringify({ state, verifier, returnTo }),
    env.SESSION_SECRET,
  );
  const callback = `${env.PUBLIC_ORIGIN}/api/auth/github/callback`;
  const authorize = new URL("https://github.com/login/oauth/authorize");
  authorize.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  authorize.searchParams.set("redirect_uri", callback);
  authorize.searchParams.set("state", state);
  authorize.searchParams.set("code_challenge", challenge);
  authorize.searchParams.set("code_challenge_method", "S256");

  return redirect(authorize.toString(), [
    serializeCookie(OAUTH_COOKIE, payload, OAUTH_TTL_SECONDS, request),
  ]);
}

async function finishGithubLogin(request, env, url) {
  requireConfiguration(env);
  const signedPayload = parseCookies(request.headers.get("Cookie"))[OAUTH_COOKIE];
  const payload = signedPayload
    ? await verifyPayload(signedPayload, env.SESSION_SECRET)
    : null;
  if (!payload) {
    return json({ error: "The GitHub login request has expired." }, 400);
  }

  const oauth = JSON.parse(payload);
  const state = url.searchParams.get("state");
  const code = url.searchParams.get("code");
  if (!code || !state || !safeEqual(state, oauth.state)) {
    return json({ error: "Invalid GitHub OAuth state." }, 400);
  }

  const tokenResponse = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
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
  });
  const token = await tokenResponse.json();
  if (!tokenResponse.ok || !token.access_token) {
    console.error("GitHub token exchange failed", token.error);
    return json({ error: "GitHub login failed." }, 502);
  }

  const userResponse = await fetch("https://api.github.com/user", {
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token.access_token}`,
      "User-Agent": "ccfddl-api",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  const githubUser = await userResponse.json();
  if (!userResponse.ok || !Number.isInteger(githubUser.id)) {
    return json({ error: "Unable to read the GitHub profile." }, 502);
  }

  const now = unixTime();
  const sessionToken = randomToken(32);
  const sessionHash = await sha256Hex(sessionToken);
  await env.DB.batch([
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
  ]);

  return redirect(`${env.PUBLIC_ORIGIN}${sanitizeReturnTo(oauth.returnTo)}`, [
    serializeCookie(OAUTH_COOKIE, "", 0, request),
    serializeCookie(SESSION_COOKIE, sessionToken, SESSION_TTL_SECONDS, request),
  ]);
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

async function logout(request, env) {
  const token = parseCookies(request.headers.get("Cookie"))[SESSION_COOKIE];
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
  const token = parseCookies(request.headers.get("Cookie"))[SESSION_COOKIE];
  if (!token) return null;
  return env.DB.prepare(
    `SELECT users.github_id, users.login, users.avatar_url, users.profile_url
     FROM sessions JOIN users ON users.github_id = sessions.github_id
     WHERE sessions.token_hash = ? AND sessions.expires_at > ?`,
  )
    .bind(await sha256Hex(token), unixTime())
    .first();
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
}

function assertTrustedOrigin(request, env) {
  const origin = request.headers.get("Origin");
  if (origin && origin !== env.PUBLIC_ORIGIN) {
    throw new HttpError(403, "Untrusted request origin.");
  }
}

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
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
  return `${name}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`;
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
    value.length <= 2048
    ? value
    : "/";
}

export function isValidConferenceKey(value) {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= 100 &&
    /^[A-Za-z0-9][A-Za-z0-9._&+'-]*$/.test(value)
  );
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
