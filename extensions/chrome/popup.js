const STORAGE_KEY = "deadlines";
const MS_PER_DAY = 24 * 60 * 60 * 1000;

const form = document.getElementById("deadline-form");
const titleInput = document.getElementById("title");
const dateInput = document.getElementById("date");
const timeInput = document.getElementById("time");
const listEl = document.getElementById("deadline-list");
const emptyEl = document.getElementById("empty-state");
const countEl = document.getElementById("count");

function toTimestamp(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.getTime();
}

function daysLeft(datetime) {
  const ts = toTimestamp(datetime);
  if (ts === null) return null;
  const diff = ts - Date.now();
  return Math.ceil(diff / MS_PER_DAY);
}

function formatDate(datetime) {
  const date = new Date(datetime);
  if (Number.isNaN(date.getTime())) return "无效日期";
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function render(deadlines) {
  listEl.innerHTML = "";
  const sorted = [...deadlines].sort((a, b) => {
    return toTimestamp(a.datetime) - toTimestamp(b.datetime);
  });

  if (sorted.length === 0) {
    emptyEl.style.display = "block";
    countEl.textContent = "";
    return;
  }

  emptyEl.style.display = "none";
  countEl.textContent = `${sorted.length} 项`;

  sorted.forEach((item, index) => {
    const li = document.createElement("li");
    li.className = "item";

    const header = document.createElement("div");
    header.className = "item-header";

    const title = document.createElement("span");
    title.className = "item-title";
    title.textContent = item.title;

    const del = document.createElement("button");
    del.className = "delete-btn";
    del.textContent = "删除";
    del.addEventListener("click", () => removeDeadline(index));

    header.append(title, del);

    const meta = document.createElement("div");
    meta.className = "item-meta";

    const date = document.createElement("span");
    date.textContent = formatDate(item.datetime);

    const remaining = document.createElement("span");
    const remainingDays = daysLeft(item.datetime);
    remaining.textContent = remainingDays === null ? "" : `剩余 ${remainingDays} 天`;

    meta.append(date, remaining);

    li.append(header, meta);
    listEl.appendChild(li);
  });
}

function loadDeadlines() {
  chrome.storage.local.get({ [STORAGE_KEY]: [] }, (result) => {
    render(result[STORAGE_KEY]);
  });
}

function saveDeadlines(deadlines) {
  chrome.storage.local.set({ [STORAGE_KEY]: deadlines }, () => {
    render(deadlines);
  });
}

function removeDeadline(index) {
  chrome.storage.local.get({ [STORAGE_KEY]: [] }, (result) => {
    const updated = result[STORAGE_KEY].filter((_, idx) => idx !== index);
    saveDeadlines(updated);
  });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = titleInput.value.trim();
  const date = dateInput.value;
  const time = timeInput.value || "23:59";

  if (!title || !date) return;

  const datetime = new Date(`${date}T${time}`);
  if (Number.isNaN(datetime.getTime())) return;

  chrome.storage.local.get({ [STORAGE_KEY]: [] }, (result) => {
    const updated = [
      ...result[STORAGE_KEY],
      {
        title,
        datetime: datetime.toISOString(),
      },
    ];
    saveDeadlines(updated);
    form.reset();
    timeInput.value = "23:59";
  });
});

loadDeadlines();
