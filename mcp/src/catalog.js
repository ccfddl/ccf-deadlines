const SOURCE_URL = "https://ccfddl.com/conference/allconf.json";
const TTL_MS = 15 * 60 * 1000;
const DEADLINE_FIELDS = ["abstract_deadline", "deadline", "rebuttal_deadline", "decision_deadline"];

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
  })();
  try {
    return await loading;
  } catch (error) {
    if (snapshot) return snapshot;
    throw error;
  } finally {
    loading = undefined;
  }
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
  if (!Number.isFinite(local)) return null;
  const utc = new Date(local - offset * 3_600_000);
  return utc.toISOString();
}

function editionSummary(conference, edition) {
  return {
    conference: conference.title,
    edition: edition.id,
    year: edition.year,
    category: conference.sub,
    rank: conference.rank ?? {},
    website: edition.link ?? null,
    place: edition.place ?? null,
    date: edition.date ?? null,
    timezone: edition.timezone ?? null,
  };
}

export function searchConferences(conferences, { query = "", category, ccf_rank, limit = 20 }) {
  const needle = query.trim().toLowerCase();
  return conferences.filter((conference) =>
    (!needle || `${conference.title} ${conference.description ?? ""}`.toLowerCase().includes(needle)) &&
    (!category || conference.sub?.toUpperCase() === category.toUpperCase()) &&
    (!ccf_rank || conference.rank?.ccf?.toUpperCase() === ccf_rank.toUpperCase()))
    .sort((a, b) => a.title.localeCompare(b.title))
    .slice(0, limit)
    .map((conference) => ({
      title: conference.title,
      description: conference.description ?? null,
      category: conference.sub ?? null,
      rank: conference.rank ?? {},
      latest_edition: [...conference.confs].sort((a, b) => b.year - a.year)[0]?.id ?? null,
    }));
}

export function getConference(conferences, nameOrId) {
  const needle = nameOrId.trim().toLowerCase();
  const byYear = /^(.*?)\s+(20\d{2})$/.exec(needle);
  const conference = conferences.find((item) =>
    item.title.toLowerCase() === needle || item.confs.some((edition) => edition.id?.toLowerCase() === needle) ||
    (byYear && item.title.toLowerCase() === byYear[1] && item.confs.some((edition) => edition.year === Number(byYear[2]))));
  if (!conference) return null;
  const selected = conference.confs.filter((edition) =>
    (!byYear || edition.year === Number(byYear[2])) &&
    (itemTitleMatches(conference.title, needle, byYear) || edition.id?.toLowerCase() === needle));
  return {
    title: conference.title,
    description: conference.description ?? null,
    category: conference.sub ?? null,
    rank: conference.rank ?? {},
    editions: [...selected].sort((a, b) => b.year - a.year).slice(0, 6).map((edition) => ({
      ...editionSummary(conference, edition),
      deadlines: (edition.timeline ?? []).flatMap((round, roundIndex) =>
        DEADLINE_FIELDS.filter((kind) => round[kind]).map((kind) => ({
          kind,
          round: roundIndex + 1,
          local_time: round[kind],
          timezone: edition.timezone,
          utc_time: deadlineToUtc(round[kind], edition.timezone),
          note: round.comment ?? null,
        }))),
    })),
  };
}

function itemTitleMatches(title, needle, byYear) {
  return title.toLowerCase() === (byYear ? byYear[1] : needle);
}

export function upcomingDeadlines(conferences, {
  days = 30, category, ccf_rank, limit = 20, now = Date.now(),
}) {
  const until = now + days * 86_400_000;
  const results = [];
  for (const conference of conferences) {
    if (category && conference.sub?.toUpperCase() !== category.toUpperCase()) continue;
    if (ccf_rank && conference.rank?.ccf?.toUpperCase() !== ccf_rank.toUpperCase()) continue;
    for (const edition of conference.confs) {
      for (const [index, round] of (edition.timeline ?? []).entries()) {
        for (const kind of DEADLINE_FIELDS) {
          const raw = round[kind];
          const utcTime = deadlineToUtc(raw, edition.timezone);
          const instant = utcTime && Date.parse(utcTime);
          if (instant === null || instant < now || instant > until) continue;
          results.push({
            ...editionSummary(conference, edition),
            kind,
            round: index + 1,
            local_time: raw,
            utc_time: utcTime,
            note: round.comment ?? null,
          });
        }
      }
    }
  }
  return results.sort((a, b) => a.utc_time.localeCompare(b.utc_time)).slice(0, limit);
}
