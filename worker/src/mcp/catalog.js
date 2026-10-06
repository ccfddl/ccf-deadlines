const SOURCE_URL = "https://ccfddl.com/conference/allconf.json";
const TTL_MS = 15 * 60 * 1000;
export const DEADLINE_FIELDS = ["abstract_deadline", "deadline", "rebuttal_deadline", "decision_deadline"];
export const EVENT_TYPES = [...DEADLINE_FIELDS, "opening"];

export const CATEGORIES = [
  ["DS", "Computer Architecture", "计算机体系结构"],
  ["NW", "Computer Networks", "计算机网络"],
  ["SC", "Network and System Security", "网络与信息安全"],
  ["SE", "Software Engineering", "软件工程"],
  ["DB", "Databases and Data Mining", "数据库与数据挖掘"],
  ["CT", "Computing Theory", "计算机科学理论"],
  ["CG", "Computer Graphics and Multimedia", "计算机图形学与多媒体"],
  ["AI", "Artificial Intelligence", "人工智能"],
  ["HI", "Human-Computer Interaction", "人机交互"],
  ["MX", "Interdisciplinary", "交叉学科"],
].map(([code, name_en, name_zh]) => ({ code, name_en, name_zh }));

let snapshot;
let expiresAt = 0;
let loading;

export async function loadCatalog(fetcher = fetch, now = Date.now()) {
  if (snapshot && now < expiresAt) return snapshot;
  if (loading) return loading;
  loading = (async () => {
    const response = await fetcher(SOURCE_URL, { signal: AbortSignal.timeout(10_000) });
    if (!response.ok) throw new Error("CCFDDL conference data is unavailable");
    const conferences = await response.json();
    if (!Array.isArray(conferences) || !conferences.every((item) =>
      item && typeof item.title === "string" && Array.isArray(item.confs))) {
      throw new Error("CCFDDL conference data is invalid");
    }
    snapshot = { conferences, source: SOURCE_URL, fetched_at: new Date(now).toISOString() };
    expiresAt = now + TTL_MS;
    return snapshot;
  })().catch((error) => {
    if (snapshot) return snapshot;
    throw error;
  }).finally(() => {
    loading = undefined;
  });
  return loading;
}

function pacificOffset(raw) {
  const approximateUtc = Date.parse(`${raw.replace(" ", "T")}Z`);
  if (!Number.isFinite(approximateUtc)) return null;
  const format = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", timeZoneName: "shortOffset",
  });
  let offset = -8;
  for (let attempt = 0; attempt < 2; attempt++) {
    const name = format.formatToParts(new Date(approximateUtc - offset * 3_600_000))
      .find((part) => part.type === "timeZoneName")?.value;
    const match = /^GMT([+-]\d{1,2})$/.exec(name ?? "");
    if (!match) return null;
    offset = Number(match[1]);
  }
  return offset;
}

export function deadlineToUtc(raw, timezone) {
  if (typeof raw !== "string" || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(raw)) return null;
  const offset = timezone === "AoE" ? -12
    : timezone === "PT" ? pacificOffset(raw)
    : timezone === "UTC" ? 0
    : /^UTC[+-]\d{1,2}$/.test(timezone ?? "") ? Number(timezone.slice(3)) : null;
  if (offset === null || offset < -12 || offset > 14) return null;
  const local = Date.parse(`${raw.replace(" ", "T")}Z`);
  // Date.parse normalizes impossible dates such as February 30.
  if (!Number.isFinite(local) || new Date(local).toISOString().slice(0, 19) !== raw.replace(" ", "T")) return null;
  const utc = new Date(local - offset * 3_600_000);
  return utc.toISOString();
}

function editionSummary(conference, edition) {
  return {
    conference_key: conferenceKey(conference),
    conference: conference.title,
    edition: edition.id,
    year: edition.year,
    category: conference.sub,
    rank: conference.rank ?? {},
    website: edition.link ?? null,
    place: edition.place ?? null,
    date: edition.date ?? null,
    timezone: edition.timezone ?? null,
    opening: edition.opening ?? null,
    opening_utc: deadlineToUtc(edition.opening, edition.timezone),
  };
}

export function conferenceKey(conference) {
  return conference.conference_key ?? `${conference.sub}/${conference.title.toLowerCase()}`;
}

function matchesFilters(conference, { category, ccf_rank, core_rank, thcpl_rank }) {
  const same = (value, requested) => !requested || (value ?? "N").toUpperCase() === requested.toUpperCase();
  return same(conference.sub, category) && same(conference.rank?.ccf, ccf_rank)
    && same(conference.rank?.core, core_rank) && same(conference.rank?.thcpl, thcpl_rank);
}

function conferenceSummary(conference, year) {
  return {
    conference_key: conferenceKey(conference),
    title: conference.title,
    description: conference.description ?? null,
    category: conference.sub ?? null,
    rank: conference.rank ?? {},
    latest_edition: [...conference.confs].filter((edition) => !year || edition.year === year)
      .sort((a, b) => b.year - a.year)[0]?.id ?? null,
  };
}

function page(items, { limit = 20, offset = 0 }) {
  const results = items.slice(offset, offset + limit);
  return { results, total: items.length, offset, limit,
    next_offset: offset + results.length < items.length ? offset + results.length : null };
}

export function searchConferencePage(conferences, options = {}) {
  const { query = "", year } = options;
  const needle = query.trim().toLowerCase();
  const matches = conferences.filter((conference) =>
    (!needle || `${conference.title} ${conference.description ?? ""} ${conferenceKey(conference)}`.toLowerCase().includes(needle))
    && matchesFilters(conference, options)
    && (!year || conference.confs.some((edition) => edition.year === year)))
    .sort((a, b) => a.title.localeCompare(b.title) || conferenceKey(a).localeCompare(conferenceKey(b)))
    .map((conference) => conferenceSummary(conference, year));
  return page(matches, options);
}

export function searchConferences(conferences, options = {}) {
  return searchConferencePage(conferences, options).results;
}

function displayTime(utcTime, timezone) {
  if (!utcTime) return null;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(utcTime));
  const value = (type) => parts.find((part) => part.type === type).value;
  return `${value("year")}-${value("month")}-${value("day")} ${value("hour")}:${value("minute")}:${value("second")}`;
}

function withDisplayTime(event, timezone) {
  return timezone ? { ...event, display_timezone: timezone, display_time: displayTime(event.utc_time, timezone) } : event;
}

function editionEvents(edition, includeOpening = false) {
  const events = (edition.timeline ?? []).flatMap((round, roundIndex) =>
    DEADLINE_FIELDS.filter((kind) => round[kind]).map((kind) => ({
      kind, round: roundIndex + 1, local_time: round[kind], timezone: edition.timezone,
      utc_time: deadlineToUtc(round[kind], edition.timezone), note: round.comment ?? null,
    })));
  if (includeOpening && edition.opening) events.push({
    kind: "opening", round: null, local_time: edition.opening, timezone: edition.timezone,
    utc_time: deadlineToUtc(edition.opening, edition.timezone), note: null,
  });
  return events;
}

export function resolveConference(conferences, nameOrId, options = {}) {
  const needle = nameOrId.trim().toLowerCase();
  const byYear = /^(.*?)\s+(\d{4})$/.exec(needle);
  const identifier = byYear ? byYear[1] : needle;
  const year = options.year ?? (byYear ? Number(byYear[2]) : undefined);
  if (byYear && options.year && options.year !== Number(byYear[2])) return null;
  const candidates = conferences.filter((item) => matchesFilters(item, options) &&
    (!year || item.confs.some((edition) => edition.year === year)) &&
    (item.title.toLowerCase() === identifier || conferenceKey(item).toLowerCase() === identifier
      || item.confs.some((edition) => edition.id?.toLowerCase() === needle && (!year || edition.year === year))));
  if (!candidates.length) return null;
  if (candidates.length > 1) return {
    ambiguous: true,
    matches: candidates.map((conference) => conferenceSummary(conference, year)),
  };
  return candidates[0];
}

export function getConference(conferences, nameOrId, options = {}) {
  const conference = resolveConference(conferences, nameOrId, options);
  if (!conference || conference.ambiguous) return conference;
  const needle = nameOrId.trim().toLowerCase();
  const byYear = /^(.*?)\s+(\d{4})$/.exec(needle);
  const identifier = byYear ? byYear[1] : needle;
  const year = options.year ?? (byYear ? Number(byYear[2]) : undefined);
  const selected = conference.confs.filter((edition) =>
    (!year || edition.year === year) &&
    (conference.title.toLowerCase() === identifier || conferenceKey(conference).toLowerCase() === identifier
      || edition.id?.toLowerCase() === needle));
  return {
    conference_key: conferenceKey(conference),
    title: conference.title,
    description: conference.description ?? null,
    category: conference.sub ?? null,
    rank: conference.rank ?? {},
    dblp: conference.dblp ?? null,
    editions: [...selected].sort((a, b) => b.year - a.year).slice(0, options.edition_limit ?? 6).map((edition) => ({
      ...editionSummary(conference, edition),
      deadlines: editionEvents(edition).map((event) => withDisplayTime(event, options.display_timezone)),
      ...(options.display_timezone ? {
        opening_display_time: displayTime(deadlineToUtc(edition.opening, edition.timezone), options.display_timezone),
        display_timezone: options.display_timezone,
      } : {}),
    })),
  };
}

export function upcomingDeadlinePage(conferences, options = {}) {
  const { days = 30, now = Date.now(), year, deadline_types = DEADLINE_FIELDS, display_timezone } = options;
  const until = now + days * 86_400_000;
  const results = [];
  for (const conference of conferences) {
    if (!matchesFilters(conference, options)) continue;
    for (const edition of conference.confs) {
      if (year && edition.year !== year) continue;
      for (const event of editionEvents(edition, deadline_types.includes("opening"))) {
        if (!deadline_types.includes(event.kind) || !event.utc_time) continue;
        const instant = Date.parse(event.utc_time);
        if (instant < now || instant > until) continue;
        results.push(withDisplayTime({ ...editionSummary(conference, edition), ...event }, display_timezone));
      }
    }
  }
  results.sort((a, b) => a.utc_time.localeCompare(b.utc_time)
    || a.conference_key.localeCompare(b.conference_key)
    || (a.edition ?? "").localeCompare(b.edition ?? "")
    || (a.round ?? 0) - (b.round ?? 0) || a.kind.localeCompare(b.kind));
  return page(results, options);
}

export function upcomingDeadlines(conferences, options = {}) {
  return upcomingDeadlinePage(conferences, options).results;
}
