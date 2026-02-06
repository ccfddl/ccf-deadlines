const STORAGE_KEY = "deadlines";
const MS_PER_DAY = 24 * 60 * 60 * 1000;

function toTimestamp(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.getTime();
}

function getSoonestDays(deadlines) {
  const now = Date.now();
  const upcoming = deadlines
    .map((item) => ({ ...item, ts: toTimestamp(item.datetime) }))
    .filter((item) => item.ts !== null && item.ts >= now)
    .sort((a, b) => a.ts - b.ts);

  if (upcoming.length === 0) {
    return null;
  }

  const diff = upcoming[0].ts - now;
  return Math.max(0, Math.ceil(diff / MS_PER_DAY));
}

function updateBadge() {
  chrome.storage.local.get({ [STORAGE_KEY]: [] }, (result) => {
    const daysLeft = getSoonestDays(result[STORAGE_KEY]);
    const text = daysLeft === null ? "" : `${daysLeft}`;
    chrome.action.setBadgeText({ text });
    chrome.action.setBadgeBackgroundColor({ color: "#2563eb" });
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("badge-refresh", { periodInMinutes: 60 });
  updateBadge();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("badge-refresh", { periodInMinutes: 60 });
  updateBadge();
});

chrome.alarms.onAlarm.addListener(() => {
  updateBadge();
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local") return;
  if (changes[STORAGE_KEY]) {
    updateBadge();
  }
});

updateBadge();
