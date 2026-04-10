const STORAGE_KEY = "deadlines";
const MS_PER_DAY = 24 * 60 * 60 * 1000;
const BRAND_COLOR = "#334155";
const ICON_STROKE = "#1f2937";

function createIconImageData(size) {
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  const strokeWidth = Math.max(1, size * 0.08);
  const radius = size / 2 - strokeWidth;

  ctx.strokeStyle = ICON_STROKE;
  ctx.lineWidth = strokeWidth;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  ctx.beginPath();
  ctx.arc(size / 2, size / 2, radius, 0, Math.PI * 2);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(size / 2, size / 2);
  ctx.lineTo(size / 2, size * 0.3);
  ctx.moveTo(size / 2, size / 2);
  ctx.lineTo(size * 0.68, size / 2);
  ctx.stroke();

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
  return Math.max(0, Math.floor(diff / MS_PER_DAY));
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
  chrome.alarms.create("badge-refresh", { periodInMinutes: 1 });
  updateBadge();
});

chrome.runtime.onStartup.addListener(() => {
  ensureActionIcon();
  chrome.alarms.create("badge-refresh", { periodInMinutes: 1 });
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
