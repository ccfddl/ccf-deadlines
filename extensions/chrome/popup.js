const STORAGE_KEY = "deadlines";
const MS_PER_DAY = 24 * 60 * 60 * 1000;

const form = document.getElementById("deadline-form");
const titleInput = document.getElementById("title");
const dateInput = document.getElementById("date");
const timeInput = document.getElementById("time");
const listEl = document.getElementById("deadline-list");
const emptyEl = document.getElementById("empty-state");
const countEl = document.getElementById("count");
const loadCcfddlBtn = document.getElementById("load-ccfddl");
const ccfddlSearchInput = document.getElementById("ccfddl-search");
const ccfddlList = document.getElementById("ccfddl-list");
const ccfddlEmpty = document.getElementById("ccfddl-empty");

let ccfddlItems = [];

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

function parseIcsDate(value) {
  if (!value) return null;
  const sanitized = value.trim();
  const match = sanitized.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z?$/);
  if (!match) return null;

  const [, year, month, day, hour, minute, second] = match;
  const iso = `${year}-${month}-${day}T${hour}:${minute}:${second}${sanitized.endsWith("Z") ? "Z" : ""}`;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

function parseIcs(text) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const unfolded = [];
  lines.forEach((line) => {
    if (line.startsWith(" ") || line.startsWith("\t")) {
      const previous = unfolded.pop() ?? "";
      unfolded.push(previous + line.trim());
    } else {
      unfolded.push(line);
    }
  });

  const events = [];
  let current = null;
  unfolded.forEach((line) => {
    if (line === "BEGIN:VEVENT") {
      current = {};
      return;
    }
    if (line === "END:VEVENT") {
      if (current) events.push(current);
      current = null;
      return;
    }
    if (!current) return;

    const [rawKey, ...rest] = line.split(":");
    const key = rawKey.split(";")[0];
    const value = rest.join(":");
    if (key === "SUMMARY") current.summary = value;
    if (key === "DTSTART") current.start = value;
  });

  return events
    .map((event) => {
      const date = parseIcsDate(event.start);
      if (!event.summary || !date) return null;
      return {
        title: event.summary,
        datetime: date.toISOString(),
      };
    })
    .filter(Boolean);
}

function renderCcfddlList(items) {
  ccfddlList.innerHTML = "";

  if (items.length === 0) {
    ccfddlEmpty.style.display = "block";
    return;
  }

  ccfddlEmpty.style.display = "none";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "import-item";

    const header = document.createElement("div");
    header.className = "import-item-header";

    const title = document.createElement("span");
    title.className = "import-title";
    title.textContent = item.title;

    const addBtn = document.createElement("button");
    addBtn.className = "import-add";
    addBtn.textContent = "添加";
    addBtn.addEventListener("click", () => addImportedDeadline(item));

    header.append(title, addBtn);

    const meta = document.createElement("div");
    meta.className = "import-meta";
    meta.textContent = formatDate(item.datetime);

    li.append(header, meta);
    ccfddlList.appendChild(li);
  });
}

function filterCcfddlList() {
  const keyword = ccfddlSearchInput.value.trim().toLowerCase();
  if (!keyword) {
    renderCcfddlList(ccfddlItems);
    return;
  }
  const filtered = ccfddlItems.filter((item) =>
    item.title.toLowerCase().includes(keyword)
  );
  renderCcfddlList(filtered);
}

function addImportedDeadline(item) {
  chrome.storage.local.get({ [STORAGE_KEY]: [] }, (result) => {
    const existing = result[STORAGE_KEY];
    const exists = existing.some(
      (entry) => entry.title === item.title && entry.datetime === item.datetime
    );
    if (exists) return;
    const updated = [...existing, item];
    saveDeadlines(updated);
  });
}

async function loadCcfddlData() {
  loadCcfddlBtn.disabled = true;
  loadCcfddlBtn.textContent = "加载中...";
  try {
    const response = await fetch(
      "https://ccfddl.com/conference/deadlines_zh.ics"
    );
    if (!response.ok) throw new Error("加载失败");
    const text = await response.text();
    ccfddlItems = parseIcs(text);
    filterCcfddlList();
  } catch (error) {
    ccfddlEmpty.textContent = "加载失败，请稍后重试。";
    ccfddlEmpty.style.display = "block";
  } finally {
    loadCcfddlBtn.disabled = false;
    loadCcfddlBtn.textContent = "加载";
  }
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

loadCcfddlBtn.addEventListener("click", loadCcfddlData);
ccfddlSearchInput.addEventListener("input", filterCcfddlList);

loadDeadlines();
