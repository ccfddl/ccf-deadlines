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
const langToggle = document.getElementById("lang-toggle");

let ccfddlItems = [];
let currentLang = "zh";
const LANG_STORAGE_KEY = "language";

const translations = {
  zh: {
    title: "CCF DDL Tracker",
    subtitle_zh: "添加你正在赶的截止日期，徽标显示最近的剩余天数。",
    subtitle_en: "",
    open: "打开 CCFDDL",
    add_section: "新增截止日期",
    title_label: "标题",
    title_placeholder: "例如：ACL 2025",
    date_label: "日期",
    time_label: "时间",
    add_button: "添加",
    import_section: "从 CCFDDL 导入",
    load_button: "加载",
    loading: "加载中...",
    search_label: "搜索会议",
    search_placeholder: "例如：ICML / SIGMOD",
    import_empty: "点击“加载”获取最新会议列表。",
    import_hint:
      "优先使用 GitHub 仓库的最新会议信息，失败时再回退到 CCFDDL ICS。",
    my_section: "我的 DDL",
    empty_state: "还没有添加任何截止日期。",
    add_item: "添加",
    delete_item: "删除",
    remaining: (days) => `剩余 ${days} 天`,
    load_failed: "加载失败，请稍后重试。",
  },
  en: {
    title: "CCF DDL Tracker",
    subtitle_zh: "",
    subtitle_en: "Track deadlines and show the nearest days left.",
    open: "Open CCFDDL",
    add_section: "Add DDL",
    title_label: "Title",
    title_placeholder: "e.g., ACL 2025",
    date_label: "Date",
    time_label: "Time",
    add_button: "Add",
    import_section: "Import from CCFDDL",
    load_button: "Load",
    loading: "Loading...",
    search_label: "Search",
    search_placeholder: "e.g., ICML / SIGMOD",
    import_empty: "Click “Load” to fetch the latest conference list.",
    import_hint:
      "Prefer GitHub repository data, with an ICS fallback if needed.",
    my_section: "My DDLs",
    empty_state: "No deadlines yet.",
    add_item: "Add",
    delete_item: "Delete",
    remaining: (days) => `${days} days left`,
    load_failed: "Failed to load. Please try again.",
  },
};

function t(key, fallback = "") {
  const entry = translations[currentLang]?.[key];
  if (typeof entry === "function") return entry;
  return entry ?? fallback;
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const value = t(key, el.textContent);
    el.textContent = value;
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    el.setAttribute("placeholder", t(key, el.getAttribute("placeholder") || ""));
  });

  if (langToggle) {
    langToggle.textContent = currentLang === "zh" ? "EN" : "中文";
  }
}

function setLanguage(lang) {
  currentLang = lang;
  applyTranslations();
  chrome.storage.local.set({ [LANG_STORAGE_KEY]: currentLang });
  renderCcfddlList(ccfddlItems);
  loadDeadlines();
}

function normalizeText(value) {
  return value
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

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
  const locale = currentLang === "en" ? "en-US" : "zh-CN";
  return date.toLocaleString(locale, {
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
  const dateTimeMatch =
    sanitized.match(
      /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})(Z|[+-]\d{4})?$/
    );
  if (dateTimeMatch) {
    const [, year, month, day, hour, minute, second, tz] = dateTimeMatch;
    const offset = tz && tz !== "Z" ? `${tz.slice(0, 3)}:${tz.slice(3)}` : "";
    const suffix = tz === "Z" ? "Z" : offset;
    const iso = `${year}-${month}-${day}T${hour}:${minute}:${second}${suffix}`;
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  const dateOnlyMatch = sanitized.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch;
    const date = new Date(`${year}-${month}-${day}T23:59:59`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  const parsed = new Date(sanitized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
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

function parseTimezoneOffset(timezone) {
  if (!timezone) return 0;
  const normalized = timezone.trim();
  if (normalized.toUpperCase() === "AOE") return -12;
  const match = normalized.match(/UTC([+-]\d{1,2})/i);
  if (!match) return 0;
  return Number.parseInt(match[1], 10);
}

function parseDeadlineWithTimezone(deadline, timezone) {
  if (!deadline || deadline.toUpperCase() === "TBD") return null;
  const [datePart, timePart] = deadline.split(" ");
  if (!datePart || !timePart) return null;
  const [year, month, day] = datePart.split("-").map((value) => Number(value));
  const [hour, minute, second] = timePart.split(":").map((value) => Number(value));
  if ([year, month, day, hour, minute, second].some((value) => Number.isNaN(value))) {
    return null;
  }
  const offsetHours = parseTimezoneOffset(timezone);
  const utcMs = Date.UTC(year, month - 1, day, hour, minute, second) - offsetHours * 3600 * 1000;
  return new Date(utcMs).toISOString();
}

function parseAllConfYaml(text) {
  const items = [];
  let current = null;
  let currentTimezone = null;
  let currentYear = null;
  let pendingDeadline = null;
  let pendingComment = null;

  const flushPending = () => {
    if (!pendingDeadline || !current) return;
    const iso = parseDeadlineWithTimezone(pendingDeadline, currentTimezone);
    if (!iso) return;
    const suffix = pendingComment ? ` (${pendingComment})` : "";
    const title = currentYear ? `${current.title} ${currentYear}${suffix}` : `${current.title}${suffix}`;
    items.push({ title, datetime: iso });
    pendingDeadline = null;
    pendingComment = null;
  };

  text.split(/\r?\n/).forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) return;

    if (trimmed.startsWith("- title:")) {
      flushPending();
      const title = trimmed.replace("- title:", "").trim().replace(/^['"]|['"]$/g, "");
      current = { title };
      currentTimezone = null;
      currentYear = null;
      return;
    }

    if (!current) return;

    if (trimmed.startsWith("year:")) {
      currentYear = trimmed.replace("year:", "").trim();
      return;
    }

    if (trimmed.startsWith("timezone:")) {
      currentTimezone = trimmed.replace("timezone:", "").trim();
      return;
    }

    if (trimmed.startsWith("- deadline:") || trimmed.startsWith("deadline:")) {
      flushPending();
      pendingDeadline = trimmed.replace("- deadline:", "").replace("deadline:", "").trim();
      pendingDeadline = pendingDeadline.replace(/^['"]|['"]$/g, "");
      return;
    }

    if (trimmed.startsWith("- abstract_deadline:") || trimmed.startsWith("abstract_deadline:")) {
      flushPending();
      pendingDeadline = trimmed
        .replace("- abstract_deadline:", "")
        .replace("abstract_deadline:", "")
        .trim();
      pendingDeadline = pendingDeadline.replace(/^['"]|['"]$/g, "");
      pendingComment = pendingComment ? pendingComment : "abstract";
      return;
    }

    if (trimmed.startsWith("comment:")) {
      pendingComment = trimmed.replace("comment:", "").trim().replace(/^['"]|['"]$/g, "");
      return;
    }
  });

  flushPending();
  return items;
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
    addBtn.textContent = t("add_item", "添加");
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
  const normalizedKeyword = normalizeText(keyword);
  const filtered = ccfddlItems.filter((item) => {
    const title = item.title.toLowerCase();
    return (
      title.includes(keyword) ||
      normalizeText(title).includes(normalizedKeyword)
    );
  });
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

function mergeCcfddlItems(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = `${item.title}__${item.datetime}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

async function loadCcfddlData() {
  loadCcfddlBtn.disabled = true;
  loadCcfddlBtn.textContent = t("loading", "加载中...");
  try {
    const repoResponse = await fetch(
      "https://ccfddl.github.io/conference/allconf.yml"
    );
    if (repoResponse.ok) {
      const repoText = await repoResponse.text();
      const now = Date.now();
      const parsed = parseAllConfYaml(repoText);
      ccfddlItems = mergeCcfddlItems(parsed)
        .filter((item) => toTimestamp(item.datetime) >= now)
        .sort((a, b) => toTimestamp(a.datetime) - toTimestamp(b.datetime));
      filterCcfddlList();
      return;
    }

    const [zhResponse, enResponse] = await Promise.all([
      fetch("https://ccfddl.com/conference/deadlines_zh.ics"),
      fetch("https://ccfddl.com/conference/deadlines_en.ics"),
    ]);
    const responses = [zhResponse, enResponse].filter((res) => res.ok);
    if (responses.length === 0) throw new Error("加载失败");
    const texts = await Promise.all(responses.map((res) => res.text()));
    const now = Date.now();
    const parsed = texts.flatMap((text) => parseIcs(text));
    ccfddlItems = mergeCcfddlItems(parsed)
      .filter((item) => toTimestamp(item.datetime) >= now)
      .sort((a, b) => toTimestamp(a.datetime) - toTimestamp(b.datetime));
    filterCcfddlList();
  } catch (error) {
    ccfddlEmpty.textContent = t("load_failed", "加载失败，请稍后重试。");
    ccfddlEmpty.style.display = "block";
  } finally {
    loadCcfddlBtn.disabled = false;
    loadCcfddlBtn.textContent = t("load_button", "加载");
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
  countEl.textContent = currentLang === "zh" ? `${sorted.length} 项` : `${sorted.length}`;

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
    del.textContent = t("delete_item", "删除");
    del.addEventListener("click", () => removeDeadline(index));

    header.append(title, del);

    const meta = document.createElement("div");
    meta.className = "item-meta";

    const date = document.createElement("span");
    date.textContent = formatDate(item.datetime);

    const remaining = document.createElement("span");
    const remainingDays = daysLeft(item.datetime);
    if (remainingDays === null) {
      remaining.textContent = "";
    } else {
      const remainingText = t("remaining", (days) => `剩余 ${days} 天`);
      remaining.textContent = remainingText(remainingDays);
    }

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

langToggle.addEventListener("click", () => {
  const next = currentLang === "zh" ? "en" : "zh";
  setLanguage(next);
});

chrome.storage.local.get({ [LANG_STORAGE_KEY]: "zh" }, (result) => {
  currentLang = result[LANG_STORAGE_KEY] || "zh";
  applyTranslations();
  renderCcfddlList(ccfddlItems);
  loadDeadlines();
});

loadCcfddlBtn.addEventListener("click", loadCcfddlData);
ccfddlSearchInput.addEventListener("input", filterCcfddlList);
