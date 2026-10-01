/* Shared controls for the crawlable conference directory and edition pages. */
(() => {
  const directory = Boolean(document.querySelector('.directory-section'));
  const params = new URLSearchParams(location.search);
  const filterKeys = ['categories', 'ccf', 'core', 'thcpl', 'q', 'tz'];
  const hasUrlFilters = filterKeys.some((key) => params.has(key));
  const categories = [...document.querySelectorAll('[data-category]')]
    .filter((node) => node.closest('.category-filter-grid'));
  const categoryValues = new Set(categories.map((node) => node.dataset.category));
  const rankValues = {
    ccf: new Set(['A', 'B', 'C', 'N']),
    core: new Set(['A*', 'A', 'B', 'C', 'N']),
    thcpl: new Set(['A', 'B', 'N']),
  };
  function stored(key) {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  }

  function store(key, value) {
    try { localStorage.setItem(key, value); } catch (_) { /* storage can be unavailable */ }
  }

  function selection(key, allowed) {
    const values = (params.get(key) || '').split(',');
    const selected = new Set(values.filter((value) => allowed.has(value)));
    if (key !== 'categories' && selected.has('N') && selected.size > 1) selected.delete('N');
    if (key === 'categories' && selected.size === allowed.size) selected.clear();
    return selected;
  }

  const state = {
    categories: selection('categories', categoryValues),
    ccf: selection('ccf', rankValues.ccf),
    core: selection('core', rankValues.core),
    thcpl: selection('thcpl', rankValues.thcpl),
    q: params.get('q') || '',
    tz: hasUrlFilters ? params.get('tz') : stored('display_timezone'),
  };

  const timezoneSelect = document.getElementById('display-timezone');
  const clock = document.getElementById('display-clock');
  const search = document.getElementById('conference-search');
  const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const fallbackZones = [
    'UTC', 'Pacific/Honolulu', 'America/Los_Angeles', 'America/Denver',
    'America/Chicago', 'America/New_York', 'America/Sao_Paulo',
    'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Africa/Cairo',
    'Asia/Dubai', 'Asia/Kolkata', 'Asia/Bangkok', 'Asia/Shanghai',
    'Asia/Tokyo', 'Australia/Sydney', 'Pacific/Auckland',
  ];
  const availableZones = typeof Intl.supportedValuesOf === 'function'
    ? Intl.supportedValuesOf('timeZone') : fallbackZones;
  const zones = [...new Set([browserTimezone, 'UTC', ...availableZones])];
  for (const zone of zones) timezoneSelect.add(new Option(zone, zone));
  if (!zones.includes(state.tz)) state.tz = browserTimezone;
  timezoneSelect.value = state.tz;
  if (search) search.value = state.q;
  let clockFormatter;

  function configureClock() {
    timezoneSelect.style.width = `${Math.min(state.tz.length + 0.5, 24)}ch`;
    clockFormatter = new Intl.DateTimeFormat('en-GB', {
      timeZone: state.tz, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
    });
  }

  function renderClock() {
    const now = new Date();
    const parts = Object.fromEntries(clockFormatter.formatToParts(now).map((part) => [part.type, part.value]));
    clock.textContent = `${parts.year}/${parts.month}/${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
    clock.dateTime = now.toISOString();
  }

  configureClock();
  renderClock();
  setInterval(renderClock, 1000);

  function queryUrl(path = location.pathname) {
    const url = new URL(path, location.origin);
    const output = new URLSearchParams();
    for (const key of ['categories', 'ccf', 'core', 'thcpl']) {
      if (state[key].size) output.set(key, [...state[key]].sort().join(','));
    }
    if (state.q.trim()) output.set('q', state.q.trim());
    if (state.tz) output.set('tz', state.tz);
    url.search = output.toString();
    return url.pathname + url.search;
  }

  function persist() {
    store('display_timezone', state.tz);
  }

  function refreshControls() {
    for (const link of categories) {
      link.classList.toggle('is-selected', directory && state.categories.has(link.dataset.category));
    }
    for (const details of document.querySelectorAll('.rank-filter')) {
      const key = details.dataset.rankKey;
      const inputs = [...details.querySelectorAll('.rank-option input')];
      for (const input of inputs) {
        input.checked = state[key].has(input.value);
      }
      const labels = inputs.filter((input) => input.checked)
        .map((input) => input.value === 'N' ? 'Non' : input.value);
      const title = key.toUpperCase();
      details.querySelector('.rank-summary-text').textContent = labels.length === 0 ? title
        : labels.length === 1 ? `${title} ${labels[0]}`
          : labels.length === 2 ? `${title} ${labels.join(',')}`
            : `${title} ${labels[0]},${labels[1]}+${labels.length - 2}`;
      details.classList.toggle('is-active', labels.length > 0);
      details.querySelector('.rank-clear').disabled = labels.length === 0;
    }
  }

  function filterDirectory() {
    if (!directory) return;
    const needle = state.q.trim().toLocaleLowerCase();
    let matches = 0;
    for (const section of document.querySelectorAll('.directory-section')) {
      let sectionMatches = 0;
      for (const row of section.querySelectorAll('li[data-category]')) {
        const visible = (!state.categories.size || state.categories.has(row.dataset.category))
          && ['ccf', 'core', 'thcpl'].every((key) => !state[key].size || state[key].has(row.dataset[key]))
          && (!needle || row.dataset.search.toLocaleLowerCase().includes(needle));
        row.hidden = !visible;
        if (visible) { matches++; sectionMatches++; }
      }
      section.hidden = sectionMatches === 0;
    }
    document.getElementById('directory-empty').hidden = matches !== 0;
  }

  function updateDirectory() {
    refreshControls();
    filterDirectory();
    persist();
    history.replaceState(null, '', queryUrl() + location.hash);
  }

  for (const link of categories) {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const category = link.dataset.category;
      if (directory) {
        if (state.categories.has(category)) state.categories.delete(category);
        else state.categories.add(category);
        updateDirectory();
      } else {
        state.categories = new Set([category]);
        persist();
        location.assign(queryUrl('/conferences/'));
      }
    });
  }

  if (search) {
    search.addEventListener('input', () => {
      state.q = search.value;
      updateDirectory();
    });
  }

  for (const details of document.querySelectorAll('.rank-filter')) {
    const key = details.dataset.rankKey;
    details.addEventListener('toggle', () => {
      if (details.open) {
        for (const other of document.querySelectorAll('.rank-filter')) {
          if (other !== details) other.open = false;
        }
      }
    });
    details.querySelector('.rank-clear').addEventListener('click', () => {
      state[key].clear();
      updateDirectory();
    });
    details.addEventListener('change', (event) => {
      const value = event.target.value;
      if (event.target.checked) {
        if (value === 'N') state[key].clear();
        else state[key].delete('N');
        state[key].add(value);
      } else state[key].delete(value);
      if (directory) updateDirectory();
      else {
        persist();
        location.assign(queryUrl('/conferences/'));
      }
    });
  }
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.rank-filter')) {
      for (const details of document.querySelectorAll('.rank-filter')) details.open = false;
    }
  });

  function zoneOffsetMinutes(zone, timestamp) {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
    }).formatToParts(new Date(timestamp));
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    const zoneTimestamp = Date.UTC(+values.year, +values.month - 1, +values.day,
      +values.hour, +values.minute, +values.second);
    return Math.round((zoneTimestamp - timestamp) / 60000);
  }

  function deadlineInstant(raw, sourceTimezone) {
    const match = /^(\d{4})-(\d{2})-(\d{2})(?: (\d{2}):(\d{2})(?::(\d{2}))?)?$/.exec(raw);
    if (!match) return null;
    const naive = Date.UTC(+match[1], +match[2] - 1, +match[3],
      +(match[4] || 23), +(match[5] || 59), +(match[6] || (match[4] ? 0 : 59)));
    let offset = 0;
    if (sourceTimezone === 'AoE') offset = -720;
    else if (sourceTimezone === 'PT') {
      offset = zoneOffsetMinutes('America/Los_Angeles', naive);
      offset = zoneOffsetMinutes('America/Los_Angeles', naive - offset * 60000);
    } else {
      const zone = /^UTC(?:([+-])(\d{1,2})(?::(\d{2}))?)?$/.exec(sourceTimezone);
      if (!zone) return null;
      if (zone[1]) offset = (zone[1] === '+' ? 1 : -1) * (+zone[2] * 60 + +(zone[3] || 0));
    }
    return new Date(naive - offset * 60000);
  }

  function renderDeadlineTimes() {
    for (const time of document.querySelectorAll('.deadline-time[data-raw]')) {
      const instant = deadlineInstant(time.dataset.raw, time.dataset.sourceTz);
      if (!instant || Number.isNaN(instant.getTime())) continue;
      const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: state.tz, year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
      }).formatToParts(instant);
      const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
      time.textContent = `${values.hour}:${values.minute}, ${values.month} ${values.day}, ${values.year} · ${state.tz}`;
      time.dateTime = instant.toISOString();
    }
  }

  const detailRows = [...document.querySelectorAll('.detail-card .conference-detail-deadline[data-raw]')]
    .map((row) => ({ row, instant: deadlineInstant(row.dataset.raw, row.dataset.sourceTz) }))
    .filter((item) => item.instant && !Number.isNaN(item.instant.getTime()))
    .sort((a, b) => a.instant - b.instant);

  function setupDetailCalendars() {
    const card = document.querySelector('.detail-card');
    const googleButton = document.getElementById('google-calendar-button');
    const icloudLink = document.getElementById('icloud-calendar-link');
    if (!card || !googleButton || !icloudLink) return;
    if (!detailRows.length) {
      googleButton.hidden = true;
      icloudLink.hidden = true;
      return;
    }
    const menu = document.getElementById('google-calendar-events');
    const calendarStamp = (date) => date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
    const eventName = (item) => `${card.dataset.conferenceName} ${card.dataset.conferenceYear} ${item.row.querySelector('.conference-detail-deadline-name').firstChild.textContent.trim()}`;
    const description = (item) => [item.row.dataset.comment, card.dataset.conferenceDescription, card.dataset.conferenceWebsite]
      .filter((part) => part && part.trim()).join('\n');
    const icalEscape = (value) => value.replace(/\\/g, '\\\\').replace(/\r?\n/g, '\\n').replace(/,/g, '\\,').replace(/;/g, '\\;');
    const ical = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//CCFDDL//Conference Deadlines//EN', 'CALSCALE:GREGORIAN'];
    const stamp = calendarStamp(new Date());
    for (const [index, item] of detailRows.entries()) {
      const start = calendarStamp(item.instant);
      const end = calendarStamp(new Date(item.instant.getTime() + 60000));
      const title = eventName(item);
      const params = new URLSearchParams({
        action: 'TEMPLATE', text: title, dates: `${start}/${end}`,
        details: description(item), location: card.dataset.conferencePlace,
      });
      const link = document.createElement('a');
      link.href = `https://calendar.google.com/calendar/render?${params}`;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = item.row.querySelector('.conference-detail-deadline-name').firstChild.textContent.trim();
      menu.appendChild(link);
      ical.push('BEGIN:VEVENT',
        `UID:${card.dataset.conferenceId}-${index}@ccfddl.com`, `DTSTAMP:${stamp}`,
        `DTSTART:${start}`, `DTEND:${end}`, `SUMMARY:${icalEscape(title)}`,
        `DESCRIPTION:${icalEscape(description(item))}`,
        `LOCATION:${icalEscape(card.dataset.conferencePlace)}`, 'END:VEVENT');
    }
    ical.push('END:VCALENDAR');
    icloudLink.href = `data:text/calendar;charset=utf-8,${encodeURIComponent(ical.join('\r\n') + '\r\n')}`;
    googleButton.addEventListener('click', () => {
      menu.hidden = !menu.hidden;
      googleButton.setAttribute('aria-expanded', String(!menu.hidden));
    });
  }

  function deadlineUrgency(remaining) {
    if (remaining < 3 * 86400000) return 'countdown-urgent';
    if (remaining < 7 * 86400000) return 'countdown-warning';
    return 'countdown-normal';
  }

  function renderDetail() {
    const nextPanel = document.getElementById('conference-next-deadline');
    if (!nextPanel) return;
    const now = Date.now();
    const next = detailRows.find((item) => item.instant.getTime() > now);
    const remaining = next ? next.instant.getTime() - now : 0;
    if (next) {
      const days = Math.floor(remaining / 86400000);
      const hours = Math.floor(remaining / 3600000) % 24;
      const minutes = Math.floor(remaining / 60000) % 60;
      const seconds = Math.floor(remaining / 1000) % 60;
      nextPanel.className = deadlineUrgency(remaining);
      nextPanel.innerHTML = `<span class="countdown-detailed-value">${days}d ${String(hours).padStart(2, '0')}h ${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s</span>`;
    } else {
      nextPanel.className = '';
      nextPanel.textContent = detailRows.length ? 'Passed' : 'TBD';
    }
    for (const item of detailRows) {
      const isNext = item === next;
      const passed = item.instant.getTime() <= now;
      item.row.classList.toggle('is-next', isNext);
      item.row.classList.toggle('is-passed', passed);
      const name = item.row.querySelector('.conference-detail-deadline-name');
      let badge = name.querySelector('small');
      if (isNext && !badge) {
        badge = document.createElement('small');
        badge.textContent = 'NEXT';
        name.appendChild(badge);
      } else if (!isNext && badge) badge.remove();
      const status = item.row.querySelector('.conference-detail-deadline-status');
      const left = item.instant.getTime() - now;
      status.className = `conference-detail-deadline-status ${passed ? '' : deadlineUrgency(left)}`;
      if (passed) status.textContent = 'passed';
      else if (left < 86400000) {
        const hours = Math.floor(left / 3600000);
        const minutes = Math.floor(left / 60000) % 60;
        status.textContent = hours ? `in ${String(hours).padStart(2, '0')}h ${String(minutes).padStart(2, '0')}m` : `in ${String(minutes).padStart(2, '0')}m`;
      } else {
        const days = Math.floor(left / 86400000);
        status.textContent = days === 1 ? '1 day' : `${days} days`;
      }
    }

    const timeline = document.getElementById('conference-deadline-timeline');
    if (!timeline || !detailRows.length) return;
    timeline.hidden = false;
    const first = detailRows[0].instant.getTime();
    const last = detailRows[detailRows.length - 1].instant.getTime();
    const start = Math.min(now, first) - 7 * 86400000;
    const end = last + 7 * 86400000;
    const span = Math.max(end - start, 1);
    const markers = timeline.querySelector('.conference-detail-timeline-markers');
    markers.replaceChildren();
    for (const item of detailRows) {
      const marker = document.createElement('span');
      marker.className = `conference-detail-timeline-marker${item.row.dataset.deadlineType === 'abstract_deadline' ? ' is-abstract' : ''}${item.instant.getTime() <= now ? ' is-passed' : ''}`;
      marker.style.left = `${Math.max(0.5, Math.min(99.5, 100 * (item.instant.getTime() - start) / span))}%`;
      marker.title = item.row.querySelector('.conference-detail-deadline-name').firstChild.textContent.trim();
      markers.appendChild(marker);
    }
    const nowMarker = document.createElement('span');
    nowMarker.className = 'conference-detail-timeline-marker is-now';
    nowMarker.style.left = `${Math.max(0.5, Math.min(99.5, 100 * (now - start) / span))}%`;
    markers.appendChild(nowMarker);
    const formatter = new Intl.DateTimeFormat('en-US', { timeZone: state.tz, month: 'short', day: 'numeric', year: 'numeric' });
    const labels = timeline.querySelectorAll('.conference-detail-timeline-range span');
    labels[0].textContent = formatter.format(Math.min(now, first));
    labels[1].textContent = formatter.format(Math.max(now, last));
  }

  timezoneSelect.addEventListener('change', () => {
    state.tz = timezoneSelect.value;
    configureClock();
    renderClock();
    persist();
    renderDeadlineTimes();
    renderDetail();
    if (directory) updateDirectory();
    else {
      const url = new URL(location.href);
      url.searchParams.set('tz', state.tz);
      history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
  });

  function updateLanguage() {
    const english = document.documentElement.lang === 'en';
    for (const clear of document.querySelectorAll('.rank-clear')) {
      clear.textContent = english ? 'Clear' : '清空';
    }
    if (directory) document.getElementById('directory-empty').textContent = english
      ? 'No matching conferences.' : '没有匹配的会议。';
  }
  document.addEventListener('static-language-change', updateLanguage);
  updateLanguage();
  refreshControls();
  filterDirectory();
  renderDeadlineTimes();
  renderDetail();
  setupDetailCalendars();
  if (detailRows.length) setInterval(renderDetail, 1000);
})();
