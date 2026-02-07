const STORAGE_KEY = "deadlines";
const MS_PER_DAY = 24 * 60 * 60 * 1000;
const BRAND_COLOR = "#2563eb";

function createIconImageData(size) {
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  ctx.fillStyle = BRAND_COLOR;
  ctx.fillRect(0, 0, size, size);

  const padding = size * 0.18;
  const calendarWidth = size - padding * 2;
  const calendarHeight = size - padding * 2;
  const radius = size * 0.12;

  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(padding, padding, calendarWidth, calendarHeight, radius);
  } else {
    ctx.rect(padding, padding, calendarWidth, calendarHeight);
  }
  ctx.fill();

  ctx.fillStyle = BRAND_COLOR;
  const headerHeight = calendarHeight * 0.28;
  ctx.fillRect(padding, padding, calendarWidth, headerHeight);

  ctx.fillStyle = "#ffffff";
  const dotRadius = size * 0.06;
  ctx.beginPath();
  ctx.arc(size * 0.42, padding + headerHeight + calendarHeight * 0.28, dotRadius, 0, Math.PI * 2);
  ctx.arc(size * 0.62, padding + headerHeight + calendarHeight * 0.28, dotRadius, 0, Math.PI * 2);
  ctx.fill();

  return ctx.getImageData(0, 0, size, size);
}

function ensureActionIcon() {
  const sizes = [16, 32, 48, 128];
  const imageData = {};
  sizes.forEach((size) => {
    const data = createIconImageData(size);
    if (data) {
      imageData[size] = data;
    }
  });

  if (Object.keys(imageData).length > 0) {
    chrome.action.setIcon({ imageData });
  }
}

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
    chrome.action.setBadgeBackgroundColor({ color: BRAND_COLOR });
  });
}

chrome.runtime.onInstalled.addListener(() => {
  ensureActionIcon();
  chrome.alarms.create("badge-refresh", { periodInMinutes: 60 });
  updateBadge();
});

chrome.runtime.onStartup.addListener(() => {
  ensureActionIcon();
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

ensureActionIcon();
updateBadge();
