import { conferenceKey, resolveConference } from "./catalog.js";

export const ACCEPTANCE_SOURCE = "https://ccfddl.com/conference/allacc.json";
const TTL_MS = 15 * 60 * 1000;
let snapshot;
let expiresAt = 0;
let loading;

// An independent cache keeps an acceptance-data outage from breaking deadlines.
export async function loadAcceptanceCatalog(fetcher = fetch, now = Date.now()) {
  if (snapshot && now < expiresAt) return snapshot;
  if (loading) return loading;
  loading = (async () => {
    const response = await fetcher(ACCEPTANCE_SOURCE, { signal: AbortSignal.timeout(10_000) });
    if (!response.ok) throw new Error("CCFDDL acceptance data is unavailable");
    const acceptances = await response.json();
    if (!Array.isArray(acceptances) || !acceptances.every((item) =>
      item && typeof item.title === "string" && Array.isArray(item.accept_rates))) {
      throw new Error("CCFDDL acceptance data is invalid");
    }
    snapshot = { acceptances, source: ACCEPTANCE_SOURCE, fetched_at: new Date(now).toISOString() };
    expiresAt = now + TTL_MS;
    return snapshot;
  })().catch((error) => {
    if (snapshot) return snapshot;
    throw error;
  }).finally(() => { loading = undefined; });
  return loading;
}

function normalizeRecord(record) {
  const count = (value) => Number.isSafeInteger(value) && value >= 0 ? value : null;
  const submitted = count(record.submitted);
  const accepted = count(record.accepted);
  const countedRate = submitted > 0 && accepted !== null && accepted <= submitted ? accepted / submitted : null;
  const publishedRate = typeof record.rate === "number" && Number.isFinite(record.rate)
    && record.rate >= 0 && record.rate <= 1 ? record.rate : null;
  const rate = publishedRate ?? countedRate;
  const issues = [];
  if (submitted !== null && accepted !== null && accepted > submitted) issues.push("accepted_exceeds_submitted");
  if (publishedRate !== null && countedRate !== null && Math.abs(publishedRate - countedRate) > 0.0001) {
    issues.push("rate_disagrees_with_counts");
  }
  return {
    year: record.year, submitted, accepted, rate,
    rate_percent: rate === null ? null : Math.round(rate * 10_000) / 100,
    label: record.str ?? record.srt ?? null,
    source: record.source ?? null,
    ...(issues.length ? { data_issues: issues } : {}),
  };
}

export function createAcceptanceIndex(conferences, acceptanceCatalog) {
  if (!acceptanceCatalog) return { source: ACCEPTANCE_SOURCE, fetched_at: null, lookup: () => ({ status: "unavailable", records: [] }) };
  const byTitle = new Map();
  for (const conference of conferences) {
    const title = conference.title.toLowerCase();
    byTitle.set(title, (byTitle.get(title) ?? 0) + 1);
  }
  const rows = new Map();
  for (const row of acceptanceCatalog.acceptances) {
    const title = row.title.toLowerCase();
    if (!rows.has(title)) rows.set(title, []);
    rows.get(title).push(row);
  }
  const entries = new Map(conferences.map((conference) => {
    let ambiguous = false;
    const records = (rows.get(conference.title.toLowerCase()) ?? []).flatMap((row) => {
      if (row.conference_key) {
        if (row.conference_key.toLowerCase() !== conferenceKey(conference).toLowerCase()) return [];
      } else if (row.sub) {
        if (row.sub.toUpperCase() !== conference.sub?.toUpperCase()) return [];
      } else if (byTitle.get(conference.title.toLowerCase()) > 1) {
        ambiguous = true;
        return [];
      }
      return row.accept_rates.filter((record) => Number.isInteger(record?.year)
        && record.year >= 1900 && record.year <= 2200).map(normalizeRecord);
    }).sort((a, b) => b.year - a.year);
    return [conferenceKey(conference), {
      status: records.length ? "available" : ambiguous ? "ambiguous" : "missing",
      records,
    }];
  }));
  return { source: acceptanceCatalog.source, fetched_at: acceptanceCatalog.fetched_at,
    lookup: (key) => entries.get(key) ?? { status: "missing", records: [] } };
}

function paginate(records, { limit = 20, offset = 0 } = {}) {
  const results = records.slice(offset, offset + limit);
  return { results, total: records.length, offset, limit,
    next_offset: offset + results.length < records.length ? offset + results.length : null };
}

export function getAcceptanceRates(conferences, index, nameOrId, options = {}) {
  const namedYear = /^(.*?)\s+(\d{4})$/.exec(nameOrId.trim());
  const conference = resolveConference(conferences, namedYear ? namedYear[1] : nameOrId, { category: options.category });
  if (!conference) return { conference: null, status: "not_found", ...paginate([], options) };
  if (conference.ambiguous) return { conference, status: "ambiguous", ...paginate([], options) };
  const stats = index.lookup(conferenceKey(conference));
  const idEdition = conference.confs.find((edition) => edition.id?.toLowerCase() === nameOrId.trim().toLowerCase());
  const year = options.year ?? (namedYear ? Number(namedYear[2]) : idEdition?.year);
  // Do not silently override the edition encoded in a name or ID.
  const conflictingYear = options.year && ((namedYear && Number(namedYear[2]) !== options.year)
    || (idEdition && idEdition.year !== options.year));
  const records = conflictingYear ? [] : stats.records.filter((record) =>
    (!year || record.year === year) && (!options.from_year || record.year >= options.from_year)
    && (!options.to_year || record.year <= options.to_year));
  return {
    conference: { conference_key: conferenceKey(conference), title: conference.title,
      category: conference.sub ?? null, rank: conference.rank ?? {} },
    status: stats.status === "available" && !records.length ? "missing" : stats.status,
    ...paginate(records, options),
  };
}

export function enrichAcceptance(data, index, conferences, options = {}) {
  const latest = (key, year) => index.lookup(key).records.find((record) => !year || record.year <= year) ?? null;
  if (data.results) return { ...data, results: data.results.map((item) => {
    const conference = conferences.find((row) => conferenceKey(row) === item.conference_key);
    const year = item.year ?? options.year ?? Math.max(...(conference?.confs ?? []).map((edition) => edition.year));
    return { ...item, acceptance_status: index.lookup(item.conference_key).status,
      latest_acceptance_rate: latest(item.conference_key, year) };
  }) };
  if (!data.conference || data.conference.ambiguous) return data;
  const conference = data.conference;
  const stats = index.lookup(conference.conference_key);
  return { ...data, conference: { ...conference, acceptance_status: stats.status,
    acceptance_rates: stats.records.slice(0, 10),
    acceptance_rates_total: stats.records.length,
    editions: conference.editions.map((edition) => ({ ...edition,
      acceptance_rate: stats.records.find((record) => record.year === edition.year) ?? null,
      recent_acceptance_rates: stats.records.filter((record) => record.year <= edition.year).slice(0, 2),
    })),
  } };
}
