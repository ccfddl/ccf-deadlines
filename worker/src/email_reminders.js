const REMINDER_DAYS = new Set([1, 7]);
const SEND_HOUR = 9;
const PAGE_SIZE = 100;

export function verifiedPrimaryEmail(addresses) {
  if (!Array.isArray(addresses)) return null;
  const primary = addresses.find((item) => item?.primary === true && item?.verified === true);
  return typeof primary?.email === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(primary.email)
    && primary.email.length <= 320
    ? primary.email
    : null;
}

export function validReminderTimezone(value) {
  if (typeof value !== "string" || value.length < 1 || value.length > 80) return false;
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: value });
    return true;
  } catch {
    return false;
  }
}

export function validReminderLanguage(value) {
  return value === "en" || value === "zh";
}

function zonedParts(timestamp, timeZone) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(timestamp));
  return Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
}

function dayNumber(parts) {
  return Math.floor(Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day)) / 86_400_000);
}

export function buildEmailDigest(events, starredIds, timezone, language, now) {
  const today = zonedParts(now, timezone);
  const matches = [];
  const seen = new Set();
  for (const event of events) {
    if (!starredIds.has(event.id) || typeof event.deadline_at !== "string") continue;
    const eventKey = event.uid ?? `${event.id}:${event.title}:${event.deadline_at}`;
    if (seen.has(eventKey)) continue;
    seen.add(eventKey);
    const deadline = Date.parse(event.deadline_at);
    if (!Number.isFinite(deadline)) continue;
    const local = event.all_day
      ? { year: event.deadline_at.slice(0, 4), month: event.deadline_at.slice(5, 7), day: event.deadline_at.slice(8, 10) }
      : zonedParts(deadline, timezone);
    const days = dayNumber(local) - dayNumber(today);
    if (!REMINDER_DAYS.has(days)) continue;
    matches.push({ ...event, days, local, deadline });
  }
  if (matches.length === 0) return null;
  matches.sort((left, right) => left.deadline - right.deadline || left.title.localeCompare(right.title));
  const date = `${today.year}/${today.month}/${today.day}`;
  const conferences = [...new Set(matches.map((event) =>
    typeof event.conference === "string" && event.conference.trim()
      ? event.conference.trim() : event.id.toUpperCase(),
  ))];
  const shown = conferences.slice(0, 3).join(language === "zh" ? "、" : ", ");
  const remaining = conferences.length - 3;
  const names = remaining > 0
    ? `${shown}${language === "zh" ? ` 等 ${remaining} 个会议` : ` +${remaining} more`}`
    : shown;
  const subject = language === "zh"
    ? `[CCFDDL] ${names} 截止日期提醒 · ${date}`
    : `[CCFDDL] ${names} Deadline reminders · ${date}`;
  const heading = language === "zh" ? `CCFDDL 截止日期提醒 · ${date}` : `CCFDDL deadline reminders · ${date}`;
  const lines = matches.map((event) => {
    const when = `${event.local.year}/${event.local.month}/${event.local.day}${event.all_day ? "" : ` ${event.local.hour}:${event.local.minute}`}`;
    const lead = language === "zh" ? `距截止 ${event.days} 天` : `${event.days} day${event.days === 1 ? "" : "s"} left`;
    return `${lead} · ${event.title} · ${when} (${timezone})\n${event.url ?? ""}`.trimEnd();
  });
  return {
    subject,
    text: `${heading}\n\n${lines.join("\n\n")}\n\n${language === "zh" ? "管理邮件提醒" : "Manage email reminders"}: https://ccfddl.com/`,
  };
}

export async function unsubscribeSignature(githubId, email, secret) {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const bytes = new Uint8Array(await crypto.subtle.sign(
    "HMAC", key, new TextEncoder().encode(`email-unsubscribe:v1:${githubId}:${email.toLowerCase()}`),
  ));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

export async function runScheduledEmailDigests(env, now = Date.now()) {
  if (!env.RESEND_API_KEY || !env.EMAIL_FROM) return { skipped: "Email sender is not configured" };
  let afterId = 0;
  let events;
  let sent = 0;
  let failed = 0;
  while (true) {
    const page = await env.DB.prepare(
      "SELECT github_id, email, timezone, language FROM email_reminders WHERE github_id > ? ORDER BY github_id LIMIT ?",
    ).bind(afterId, PAGE_SIZE).all();
    if (page.results.length === 0) break;
    for (const recipient of page.results) {
      afterId = recipient.github_id;
      try {
        const local = zonedParts(now, recipient.timezone);
        if (Number(local.hour) < SEND_HOUR) continue;
        const localDate = `${local.year}-${local.month}-${local.day}`;
        let job = await env.DB.prepare(
          "SELECT payload_json, status FROM email_digest_sends WHERE github_id = ? AND local_date = ?",
        ).bind(recipient.github_id, localDate).first();
        if (job?.status === "sent") continue;
        if (!job) {
          const stars = await env.DB.prepare(
            "SELECT conference_key FROM conference_stars WHERE github_id = ?",
          ).bind(recipient.github_id).all();
          if (stars.results.length === 0) continue;
          if (!events) {
            const response = await fetch(`${env.PUBLIC_ORIGIN}/conference/deadline_events.json`, {
              redirect: "manual", signal: AbortSignal.timeout(10_000),
            });
            if (!response.ok || response.status >= 300) throw new Error("Deadline index unavailable");
            events = await response.json();
            if (!Array.isArray(events)) throw new Error("Deadline index invalid");
          }
          const digest = buildEmailDigest(
            events, new Set(stars.results.map((row) => row.conference_key)),
            recipient.timezone, recipient.language, now,
          );
          if (!digest) continue;
          const token = await unsubscribeSignature(recipient.github_id, recipient.email, env.SESSION_SECRET);
          const unsubscribe = `${env.PUBLIC_ORIGIN}/api/email/unsubscribe?id=${recipient.github_id}&token=${token}`;
          const payload = {
            from: env.EMAIL_FROM,
            to: [recipient.email],
            subject: digest.subject,
            text: `${digest.text}\n${recipient.language === "zh" ? "取消订阅" : "Unsubscribe"}: ${unsubscribe}`,
          };
          await env.DB.prepare(
            "INSERT OR IGNORE INTO email_digest_sends (github_id, local_date, payload_json, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
          ).bind(recipient.github_id, localDate, JSON.stringify(payload), Math.floor(now / 1000)).run();
          job = await env.DB.prepare(
            "SELECT payload_json, status FROM email_digest_sends WHERE github_id = ? AND local_date = ?",
          ).bind(recipient.github_id, localDate).first();
        }
        if (!job || job.status === "sent") continue;
        const addressKey = await unsubscribeSignature(recipient.github_id, recipient.email, env.SESSION_SECRET);
        const response = await fetch("https://api.resend.com/emails", {
          method: "POST", redirect: "manual", signal: AbortSignal.timeout(10_000),
          headers: {
            Authorization: `Bearer ${env.RESEND_API_KEY}`,
            "Content-Type": "application/json",
            "Idempotency-Key": `ccfddl-digest-${recipient.github_id}-${localDate}-${addressKey.slice(0, 16)}`,
          },
          body: job.payload_json,
        });
        if (!response.ok) throw new Error(`Email provider returned ${response.status}`);
        const result = await response.json();
        if (typeof result.id !== "string") throw new Error("Email provider response invalid");
        await env.DB.prepare(
          "UPDATE email_digest_sends SET status = 'sent', provider_id = ?, sent_at = ? WHERE github_id = ? AND local_date = ?",
        ).bind(result.id, Math.floor(now / 1000), recipient.github_id, localDate).run();
        sent += 1;
      } catch (error) {
        failed += 1;
        console.error("Email reminder delivery failed", error?.message ?? "Error");
      }
    }
    if (page.results.length < PAGE_SIZE) break;
  }
  return { sent, failed };
}
