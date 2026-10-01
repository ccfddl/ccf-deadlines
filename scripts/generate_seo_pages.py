#!/usr/bin/env python3
"""Generate crawlable conference pages from the same data used by the app."""

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, tostring

import yaml


ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://ccfddl.com"
KNOWN_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}(?::\d{2})?)?$")
CATEGORY_EN_BY_SUB = {
    "DS": "Computer Architecture",
    "NW": "Network System",
    "SC": "Network and System Security",
    "SE": "Software Engineering",
    "DB": "Database",
    "CT": "Computing Theory",
    "CG": "Graphics",
    "AI": "Artificial Intelligence",
    "HI": "Computer-Human Interaction",
    "MX": "Interdiscipline",
}


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def edition_path(conference: dict, edition: dict) -> str:
    if not re.fullmatch(r"[A-Za-z0-9]+", str(conference["sub"])):
        raise ValueError(f"Invalid conference category: {conference['sub']}")
    if not isinstance(edition["year"], int) or not 1900 <= edition["year"] <= 2200:
        raise ValueError(f"Invalid conference year: {edition['year']}")
    slug = slugify(conference["title"]) or slugify(edition["id"])
    return f"/conferences/{conference['sub'].lower()}/{slug}-{edition['year']}/"


def safe_link(url: str) -> str | None:
    parsed = urlparse(url)
    return url if parsed.scheme in ("http", "https") and parsed.netloc else None


def text(value: object) -> str:
    return escape(str(value or ""), quote=True)


def format_deadline(value: object, timezone: str) -> str:
    raw = str(value or "").strip()
    if not KNOWN_DATE.fullmatch(raw):
        return "Not listed"
    when = datetime.strptime(raw[:10], "%Y-%m-%d")
    shown = f"{raw[11:16] if len(raw) > 10 else '23:59'}, "
    shown += f"{when:%b} {when.day}, {when.year}"
    return f'<time class="deadline-time" data-raw="{text(raw)}" data-source-tz="{text(timezone)}" title="Original: {text(raw)} {text(timezone)}">{text(shown)} · {text(timezone)}</time>'


def category_links(categories: dict[str, str], active_sub: str = "") -> str:
    return "".join(
        f'<a href="/conferences/?categories={text(sub)}"{(" aria-current=\"page\"" if sub == active_sub else "")}'
        f' data-category="{text(sub)}" data-zh="{text(name)}" data-en="{text(CATEGORY_EN_BY_SUB.get(sub, name))}">{text(name)}</a>'
        for sub, name in categories.items()
    )


def rank_filter(key: str, label: str, values: tuple[str, ...]) -> str:
    options = "".join(
        f'<label class="rank-option"><input type="checkbox" value="{text(value)}"><span>{text(f"Non-{label}" if value == "N" else f"{label} {value}")}</span></label>'
        for value in values
    )
    panel_width = {"ccf": 180, "core": 188, "thcpl": 196}[key]
    return (
        f'<details class="rank-filter" data-rank-key="{key}" style="--rank-panel-width:{panel_width}px">'
        f'<summary><span class="rank-summary-text">{label}</span><span class="rank-arrow" aria-hidden="true">▾</span></summary>'
        f'<div class="rank-menu"><div class="rank-menu-header"><span>{label}</span>'
        f'<button class="rank-clear" type="button" disabled>清空</button></div>'
        f'<div class="rank-menu-options">{options}</div></div></details>'
    )


def layout(title: str, description: str, canonical: str, body: str, navigation: str = "", breadcrumb: str = "", detail_page: bool = False) -> str:
    language_row = '' if detail_page else '<div class="language-row"><span id="language-zh">中文</span><button class="language-switch" id="language-switch" type="button" role="switch" aria-label="Switch language" aria-checked="false"><span></span></button><span id="language-en">English</span></div>'
    clock_control = (
        '<div class="toolbar-clock"><time class="toolbar-clock-value" id="display-clock">—</time>'
        '<span class="toolbar-timezone"><span>(</span><label class="toolbar-timezone-picker">'
        '<select id="display-timezone" aria-label="Select display timezone"><option value="UTC">UTC</option></select>'
        '<span class="toolbar-timezone-arrow" aria-hidden="true">⌄</span></label><span> time)</span></span></div>'
    )
    filters = (
        f'<div class="directory-toolbar detail-toolbar">{clock_control}</div>'
        if detail_page else f'''<nav class="category-filter-grid" aria-label="Conference categories">{navigation}</nav>
      <div class="directory-toolbar">
        {clock_control}
        <label class="toolbar-search-wrap"><span class="toolbar-search"><span class="toolbar-search-prefix"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span><input id="conference-search" type="text" placeholder="search conference" aria-label="Search conferences" autocomplete="off"></span></label>
        <div class="toolbar-ranks" role="group" aria-label="Conference rankings">{rank_filter('ccf', 'CCF', ('A', 'B', 'C', 'N'))}{rank_filter('core', 'CORE', ('A*', 'A', 'B', 'C', 'N'))}{rank_filter('thcpl', 'THCPL', ('A', 'B', 'N'))}</div>
      </div>'''
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{text(title)}</title>
  <meta name="description" content="{text(description)}">
  <link rel="canonical" href="{text(canonical)}">
  <link rel="icon" href="/favicon.ico">
  <link rel="stylesheet" href="/conferences/style.css">
</head>
<body>
  <div class="home">
    <header class="site-header">
      <div class="header-main"><a class="title" href="{BASE_URL}/"><span>CCFDDL&nbsp;Open&nbsp;</span><span class="title-accent">Deadlines</span></a><div class="header-github"><a class="github-star-link" href="https://github.com/ccfddl/ccf-deadlines" target="_blank" rel="noopener noreferrer" aria-label="Star ccfddl/ccf-deadlines on GitHub"><svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.62 7.62 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg><span>Star</span><span class="github-star-count" id="github-star-count" hidden></span></a></div><div class="header-auth" id="github-auth"><a class="github-login-button" id="github-login-link" href="{BASE_URL}/api/auth/github?return_to=%2F"><svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.62 7.62 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg><span data-zh="使用 GitHub 登录" data-en="Sign in with GitHub">使用 GitHub 登录</span></a></div></div>
      <div class="el-row subtitle">Worldwide Conference Deadline Countdowns. Preview in <a href="{BASE_URL}/?view=table">tabular form</a>.</div>
      <div class="el-row subtitle">*Disclaimer: The data provided by ccfddl is agenticly collected and for reference purposes only.</div>
      {breadcrumb}
      {language_row}
      {filters}
    </header>
    <main>{body}</main>
    <footer class="footer"><div class="footer-text"><span class="footer-credit">Maintained by @ccfddl. If you find it useful, star or follow <a href="https://github.com/ccfddl" target="_blank" rel="noopener noreferrer">@ccfddl</a> on Github.</span></div></footer>
  </div>
  <script>(function(){{
    var toggle=document.getElementById('language-switch');
    function setLanguage(english){{
      document.documentElement.lang=english?'en':'zh-CN';
      if(toggle){{
        toggle.setAttribute('aria-checked',english?'true':'false');
        document.getElementById('language-zh').classList.toggle('is-active',!english);
        document.getElementById('language-en').classList.toggle('is-active',english);
      }}
      document.querySelectorAll('[data-en][data-zh]').forEach(function(node){{node.textContent=english?node.dataset.en:node.dataset.zh;}});
    }}
    var stored;try{{stored=localStorage.getItem('language_preference');}}catch(error){{}}
    setLanguage(stored==='en'||(stored!=='zh'&&!navigator.language.toLowerCase().startsWith('zh')));
    document.dispatchEvent(new CustomEvent('static-language-change'));
    if(toggle)toggle.addEventListener('click',function(){{var english=toggle.getAttribute('aria-checked')!=='true';setLanguage(english);document.dispatchEvent(new CustomEvent('static-language-change'));try{{localStorage.setItem('language_preference',english?'en':'zh');}}catch(error){{}}}});
    var starCount=document.getElementById('github-star-count');
    function showStarCount(value){{if(Number.isFinite(value)){{starCount.textContent=new Intl.NumberFormat('en-US').format(value);starCount.hidden=false;}}}}
    var cachedStars=0;
    try{{cachedStars=Number(localStorage.getItem('github_star_count'));if(cachedStars>0)showStarCount(cachedStars);}}catch(error){{}}
    var updatedAt=0;
    try{{updatedAt=Number(localStorage.getItem('github_star_count_updated_at'));}}catch(error){{}}
    if(!updatedAt||Date.now()-updatedAt>21600000){{setTimeout(function(){{
      fetch('https://api.github.com/repos/ccfddl/ccf-deadlines').then(function(response){{if(!response.ok)throw new Error('GitHub unavailable');return response.json();}}).then(function(data){{
        if(Number.isInteger(data.stargazers_count)){{showStarCount(data.stargazers_count);try{{localStorage.setItem('github_star_count',String(data.stargazers_count));localStorage.setItem('github_star_count_updated_at',String(Date.now()));}}catch(error){{}}}}
      }}).catch(function(){{}});
    }},2000);}}
    if(location.origin==='{BASE_URL}'){{
      document.getElementById('github-login-link').href='/api/auth/github?return_to='+encodeURIComponent(location.pathname+location.search+location.hash);
      fetch('/api/bootstrap',{{credentials:'same-origin'}}).then(function(response){{if(!response.ok)throw new Error('Login check failed');return response.json();}}).then(function(data){{
        var conferenceStar=document.querySelector('.conference-detail-star-count');
        if(conferenceStar&&data.counts&&typeof data.counts[conferenceStar.dataset.conferenceKey]==='number'){{conferenceStar.querySelector('.conference-detail-star-number').textContent=String(data.counts[conferenceStar.dataset.conferenceKey]);}}
        if(!data.user)return;
        var auth=document.getElementById('github-auth');
        var details=document.createElement('details');details.className='github-account-menu';
        var summary=document.createElement('summary');summary.className='github-account-trigger';
        if(typeof data.user.avatar_url==='string'&&data.user.avatar_url.startsWith('https://')){{var avatar=document.createElement('img');avatar.src=data.user.avatar_url;avatar.alt='';summary.appendChild(avatar);}}
        var name=document.createElement('span');name.className='github-account-name';name.textContent=data.user.login;summary.appendChild(name);
        var options=document.createElement('div');options.className='github-account-options';
        var main=document.createElement('a');main.href='{BASE_URL}/';main.textContent='Main site';options.appendChild(main);
        var signout=document.createElement('button');signout.type='button';signout.dataset.zh='退出';signout.dataset.en='Sign out';
        signout.addEventListener('click',function(){{fetch('/api/auth/logout',{{method:'POST',credentials:'same-origin'}}).then(function(response){{if(response.ok)location.reload();else signout.textContent='Retry sign out';}}).catch(function(){{signout.textContent='Retry sign out';}});}});
        options.appendChild(signout);details.append(summary,options);auth.replaceChildren(details);
        setLanguage(document.documentElement.lang==='en');
      }}).catch(function(){{}});
    }}
  }})();</script>
  <script src="/conferences/controls.js" defer></script>
</body>
</html>
"""


def deadline_rows(edition: dict) -> str:
    labels = (
        ("abstract_deadline", "Abstract Submission Deadline"),
        ("deadline", "Paper Submission Deadline"),
        ("rebuttal_deadline", "Rebuttal Submission"),
        ("decision_deadline", "Final Decisions"),
    )
    rows = []
    timeline = edition.get("timeline", [])
    timezone = edition.get("timezone", "")
    for round_number, point in enumerate(timeline, start=1):
        for field, label in labels:
            if not point.get(field):
                continue
            raw = str(point[field]).strip()
            if not KNOWN_DATE.fullmatch(raw):
                continue
            heading = f"Round {round_number} {label}" if len(timeline) > 1 else label
            row = (
                f'<div class="conference-detail-deadline" data-raw="{text(raw)}" data-source-tz="{text(timezone)}" data-deadline-type="{text(field)}" data-comment="{text(point.get("comment", ""))}"><div class="conference-detail-deadline-main">'
                f'<div class="conference-detail-deadline-name">{text(heading)}</div>'
                f'<div class="conference-detail-deadline-date">{format_deadline(point[field], timezone)}</div>'
                f'</div><span class="conference-detail-deadline-status" aria-live="off"></span></div>'
            )
            rows.append((raw, row))
    return "".join(row for _, row in sorted(rows, key=lambda entry: entry[0])) or '<div class="conference-detail-deadline">Dates to be announced</div>'


def edition_page(conference: dict, edition: dict, categories: dict[str, str], acceptances: dict[str, list[dict]]) -> str:
    name, year = conference["title"], edition["year"]
    path = edition_path(conference, edition)
    canonical = BASE_URL + path
    known = [str(point.get("deadline")) for point in edition.get("timeline", []) if KNOWN_DATE.fullmatch(str(point.get("deadline", "")))]
    all_known = [
        str(point[field])
        for point in edition.get("timeline", [])
        for field in ("abstract_deadline", "deadline", "rebuttal_deadline", "decision_deadline")
        if KNOWN_DATE.fullmatch(str(point.get(field, "")))
    ]
    deadline_summary = f"paper deadline {min(known)[:16]} {edition.get('timezone', '')}" if known else "paper deadline not listed"
    description = f"{name} {year}: {deadline_summary}; {edition.get('date') or 'conference dates not listed'}; {edition.get('place') or 'location not listed'}. Deadlines and past editions on CCFDDL."
    title = f"{name} {year} Deadline and Conference Dates | CCFDDL"
    category = categories.get(conference["sub"], conference["sub"])
    ranks = conference.get("rank") or {}
    rank_tags = "".join(
        f'<span>{label} {text(ranks[key])}</span>' if ranks.get(key) else f'<span>Non-{label}</span>'
        for key, label in (("ccf", "CCF"), ("core", "CORE"), ("thcpl", "THCPL"))
    )
    official = safe_link(str(edition.get("link") or ""))
    official_link = f'<a class="conference-detail-website" href="{text(official)}" target="_blank" rel="noopener noreferrer">Visit website ↗</a>' if official else ""
    calendar_actions = ""
    if all_known:
        calendar_actions = (
            '<button class="conference-detail-calendar-link" id="google-calendar-button" type="button" aria-expanded="false">'
            '<img src="https://ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_31_2x.png" alt="">'
            '<span>Google Calendar</span></button>'
            f'<a class="conference-detail-calendar-link" id="icloud-calendar-link" download="{text(slugify(name))}-{year}.ics">'
            '<img src="https://help.apple.com/assets/61526E8E1494760B754BD308/61526E8F1494760B754BD30F/zh_CN/2162f7d3de310d2b3503c0bbebdc3d56.png" alt="">'
            '<span>iCloud Calendar</span></a>'
        )
    other_editions = sorted((item for item in conference["confs"] if item["year"] != year), key=lambda item: item["year"], reverse=True)
    history = "".join(f'<li><a href="{text(edition_path(conference, item))}">{text(name)} {item["year"]}</a></li>' for item in other_editions)
    notes = list(dict.fromkeys(str(point["comment"]).strip() for point in edition.get("timeline", []) if point.get("comment")))
    note = f'<div class="conference-detail-note">NOTE: {text(" · ".join(notes))}</div>' if notes else ""
    upcoming = [value for value in all_known if value[:10] >= datetime.now().date().isoformat()]
    next_deadline = min(upcoming) if upcoming else None
    next_display = format_deadline(next_deadline, edition.get("timezone", "")) if next_deadline else "Passed" if all_known else "TBD"
    next_panel = f'<div class="conference-detail-next"><span class="conference-detail-label">NEXT DEADLINE IN</span><strong id="conference-next-deadline" aria-live="off">{next_display}</strong></div>'
    recent_rates = sorted(
        (rate for rate in acceptances.get(name, []) if rate.get("year", 0) <= year),
        key=lambda rate: rate["year"],
        reverse=True,
    )[:2]
    acceptance = f'<div class="conference-detail-acceptance">Acc. Rate: {text("  ·  ".join(rate.get("str", "") for rate in recent_rates))}</div>' if recent_rates else ""
    dblp = safe_link(f'https://dblp.org/db/conf/{conference.get("dblp", "")}') if conference.get("dblp") else None
    dblp_link = f' <a class="conference-detail-dblp" href="{text(dblp)}" target="_blank" rel="noopener noreferrer" title="View on DBLP" aria-label="View conference on DBLP"><img src="https://dblp.org/img/favicon.ico" alt=""></a>' if dblp else ""
    body = f"""
    <article class="detail-card" data-conference-name="{text(name)}" data-conference-year="{year}" data-conference-place="{text(edition.get('place') or '')}" data-conference-description="{text(conference.get('description') or name)}" data-conference-website="{text(official or '')}" data-conference-id="{text(edition.get('id', ''))}">
      <h1 class="conference-detail-title"><span class="conference-detail-title-text">{text(name)} {year}</span><span class="conference-detail-star-count" data-conference-key="{text(edition.get('id', ''))}" title="GitHub user favorites" aria-label="GitHub user favorites"><svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" aria-hidden="true"><path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 13.187l-4.389 2.256z"/></svg><span class="conference-detail-star-number">0</span></span></h1>
      <div class="detail-content">
      <div class="conference-detail-description">{text(conference.get('description') or name)}{dblp_link}</div>
      {acceptance}
      <div class="conference-detail-section"><span class="conference-detail-label">DATES</span><div>{text(edition.get('date') or 'Not listed')}</div></div>
      <div class="conference-detail-section"><span class="conference-detail-label">VENUE</span><div>{text(edition.get('place') or 'Not listed')}</div></div>
      {note}
      {next_panel}
      <div class="conference-detail-section"><h2 class="conference-detail-label">IMPORTANT DEADLINES</h2><div class="conference-detail-timeline" id="conference-deadline-timeline" hidden><div class="conference-detail-timeline-track"><div class="conference-detail-timeline-line"></div><div class="conference-detail-timeline-markers"></div></div><div class="conference-detail-timeline-range"><span></span><span></span></div></div>{deadline_rows(edition)}</div>
      <div class="conference-detail-tags">{rank_tags}<span data-zh="{text(category)}" data-en="{text(CATEGORY_EN_BY_SUB.get(conference['sub'], category))}">{text(category)}</span></div>
      <div class="conference-detail-actions">{official_link}{calendar_actions}</div>
      <div class="conference-detail-calendar-events" id="google-calendar-events" hidden></div>
      </div>
    </article>
    <section class="editions"><h2>past venues</h2><ul class="edition-list">{history or '<li>No earlier edition in the database.</li>'}</ul></section>
    """
    breadcrumb = f'<nav class="breadcrumb" aria-label="Breadcrumb"><a href="{BASE_URL}/">Main site</a><span>/</span><a href="/conferences/">All conferences</a><span>/</span><span>{text(name)} {year}</span></nav>'
    return layout(title, description, canonical, body, breadcrumb=breadcrumb, detail_page=True)


def directory_page(conferences: list[dict], categories: dict[str, str]) -> str:
    groups = defaultdict(list)
    for conference in conferences:
        latest = max(conference["confs"], key=lambda item: item["year"])
        groups[conference["sub"]].append((conference, latest))
    sections = []
    for sub in sorted(groups):
        links = ""
        for conference, edition in sorted(groups[sub], key=lambda pair: pair[0]["title"].lower()):
            ranks = conference.get("rank") or {}
            search_text = f"{conference['title']} {conference.get('description') or ''} {edition['year']}"
            links += (
                f'<li data-category="{text(sub)}" data-ccf="{text(ranks.get("ccf") or "N")}"'
                f' data-core="{text(ranks.get("core") or "N")}" data-thcpl="{text(ranks.get("thcpl") or "N")}"'
                f' data-search="{text(search_text)}">'
                f'<a href="{text(edition_path(conference, edition))}">{text(conference["title"])} {edition["year"]}</a></li>'
            )
        category = categories.get(sub, sub)
        sections.append(f'<section class="directory-section" id="{text(sub.lower())}"><h2 data-zh="{text(category)}" data-en="{text(CATEGORY_EN_BY_SUB.get(sub, category))}">{text(category)}</h2><ul class="directory-list">{links}</ul></section>')
    body = f'<p class="directory-empty" id="directory-empty" hidden>No matching conferences.</p>{"".join(sections)}'
    breadcrumb = f'<nav class="breadcrumb" aria-label="Breadcrumb"><a href="{BASE_URL}/">Main site</a><span>/</span><span>All conferences</span></nav>'
    return layout("Conference Deadlines Directory | CCFDDL", "Find conference deadlines, dates, locations and official websites for every conference tracked by CCFDDL.", BASE_URL + "/conferences/", body, category_links(categories), breadcrumb)


def stylesheet() -> str:
    return """/* Matches the main site's header, conference cards and detail dialog. */
:root{--color-primary:#409eff;--color-text-primary:#2c3e50;--color-text-secondary:#666;--color-border-light:#ebeef5}
*{box-sizing:border-box}
body{margin:0;background:#faf9f7;color:var(--color-text-primary);font-family:"PingFang SC","Microsoft YaHei","Roboto","Helvetica Neue",Helvetica,Arial,sans-serif}
a{color:var(--color-primary);text-decoration:underline;text-decoration-color:currentColor}
a:hover{color:#d9554f}
.home{max-width:1240px;margin:0 auto;padding:0 20px;font-family:"Roboto Mono","SF Mono",Monaco,monospace;-webkit-font-smoothing:antialiased}
.site-header{padding-top:8px}
.header-main{position:relative;display:flex;align-items:center;flex-wrap:wrap;gap:7px;min-height:36px;padding-right:250px;font-size:16px}
.header-github{display:flex;align-items:center}
.title{display:inline-flex;align-items:baseline;color:var(--color-text-primary);font-size:29px;line-height:1;text-decoration:none;border-bottom:2px solid currentColor;white-space:nowrap}
.title:hover{color:var(--color-text-primary)}
.title-accent{color:#d9554f;font-style:italic}
.github-star-link{display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 9px;border:1px solid #d9d3cb;border-radius:8px;background:#fff;box-shadow:0 1px 2px rgba(63,55,47,.05);color:#3f4751;font-size:13px;font-weight:600;line-height:1;text-decoration:none;white-space:nowrap}
.github-star-link:hover{border-color:#bfc8d1;background:#f7f9fb;color:#29394b}
.github-star-link svg{width:16px;height:16px}
.github-star-count{margin-left:1px;padding-left:7px;border-left:1px solid #e3ded8;color:#4d5966;font-variant-numeric:tabular-nums;font-weight:600}
.header-auth{position:absolute;top:4px;right:0;display:flex;align-items:center}
.github-login-button{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:28px;padding:0 10px;border:1px solid #d9d3cb;border-radius:8px;background:#fff;color:#3f4751;font-size:12px;line-height:1;text-decoration:none;white-space:nowrap}
.github-login-button:hover{border-color:#bfc8d1;background:#f7f9fb;color:#29394b;text-decoration:none}
.github-login-button svg{width:16px;height:16px}
.github-account-menu{position:relative;font-size:12px}
.github-account-trigger{display:flex;align-items:center;gap:8px;height:32px;padding:3px 10px 3px 4px;border:1px solid #d9d3cb;border-radius:9px;background:#fff;color:#3f4751;cursor:pointer;list-style:none}
.github-account-trigger::-webkit-details-marker{display:none}
.github-account-trigger img{width:24px;height:24px;border-radius:50%}
.github-account-name{max-width:145px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.github-account-options{position:absolute;z-index:10;top:calc(100% + 6px);right:0;display:grid;min-width:132px;padding:4px;border:1px solid #d9d3cb;border-radius:9px;background:#fff;box-shadow:0 8px 22px rgba(44,62,80,.13)}
.github-account-options a,.github-account-options button{display:block;padding:8px 10px;border:0;border-radius:6px;background:transparent;color:#3f4751;font:inherit;font-size:14px;font-weight:600;text-align:left;text-decoration:none;white-space:nowrap;cursor:pointer}
.github-account-options a:hover,.github-account-options button:hover{background:#f5f7fa}
.subtitle{display:inline-block;margin:3px 0 0;padding-top:7px;color:var(--color-text-secondary);font-size:16px;line-height:20px}
.subtitle a{color:inherit}
.language-row{display:flex;align-items:center;gap:14px;min-height:28px;margin-top:12px;font-size:14px;color:#333}
.language-row .is-active{color:#409eff}
.language-switch{position:relative;width:38px;height:20px;padding:0;border:0;border-radius:999px;background:#dcdfe6;cursor:pointer}
.language-switch span{position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.12);transition:transform .15s}
.language-switch[aria-checked=true]{background:#409eff}
.language-switch[aria-checked=true] span{transform:translateX(18px)}
.category-filter-grid{display:flex;align-items:center;flex-wrap:wrap;gap:10px;margin-top:12px;padding:12px 0 2px;border-top:1px solid #e8e3dc}
.category-filter-grid a{display:block;min-height:22px;padding:2px 9px;border:1px solid transparent;border-radius:7px;background:#f2efeb;color:#655f58;font-family:"Segoe UI","Segoe UI Web (West European)",ui-sans-serif,system-ui,-apple-system,"system-ui",Roboto,"Helvetica Neue",sans-serif;font-size:14px;font-weight:500;line-height:16px;text-decoration:none;white-space:nowrap}
.category-filter-grid a:hover{border-color:#ddd4ca;background:#ebe6df}
.category-filter-grid a[aria-current=page],.category-filter-grid a.is-selected{border-color:#9fc4e3;background:#edf5fb;color:#356d9e}
.directory-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:10px;min-height:46px;padding:4px 0 10px;border-bottom:1px solid #e8e3dc}
.detail-toolbar{margin-top:12px;padding-top:12px;border-top:1px solid #e8e3dc}
.toolbar-clock{display:inline-flex;align-items:center;flex-wrap:wrap;gap:4px 8px;color:#666;font-size:14px;white-space:nowrap}
.toolbar-clock-value{color:#666;font-variant-numeric:tabular-nums;font-weight:500}
.toolbar-timezone{display:inline-flex;align-items:center;gap:0;line-height:1.4}
.toolbar-timezone-picker{display:inline-flex;align-items:center;cursor:pointer}
.toolbar-timezone select{max-width:190px;padding:0 0 0 2px;border:0;appearance:none;background:transparent;color:#666;font:inherit;cursor:pointer}
.toolbar-timezone-arrow{position:relative;top:-1px;margin-left:3px;font-size:12px;line-height:1;pointer-events:none}
.toolbar-timezone>span:last-child{margin-left:3px}
.toolbar-search-wrap{display:inline-flex;width:160px;height:24px;flex:none;align-items:center}
.toolbar-search{display:inline-flex;width:100%;height:24px;align-items:center;padding-left:6px;border:1px solid #c0c4cc;border-radius:4px;background:#fff;color:#666;font:12px/16px "Segoe UI","Segoe UI Web (West European)",ui-sans-serif,system-ui,-apple-system,Roboto,"Helvetica Neue",sans-serif}
.toolbar-search-prefix{display:flex;width:12px;height:12px;flex:none;align-items:center}
.toolbar-search-prefix svg{width:12px;height:12px;color:lightgray;pointer-events:none}
.toolbar-search input{display:block;width:100%;min-width:0;height:22px;margin-left:2px;padding:0 8px 0 2px;border:0;outline:0;background:transparent;color:#242424;font:inherit}
.toolbar-search input::placeholder{color:#909399}
.toolbar-search:focus-within,.toolbar-timezone select:focus{outline:2px solid #409eff;outline-offset:1px}
.toolbar-ranks{display:flex;align-items:center;gap:6px;margin-left:auto}
.rank-filter{position:relative;color:#666}
.rank-filter summary{display:inline-flex;align-items:center;justify-content:space-between;gap:6px;min-width:88px;max-width:132px;padding:5px 8px;border:1px solid #d9d9d9;border-radius:6px;background:#fff;color:#666;font:500 11px Arial,sans-serif;text-align:left;cursor:pointer;list-style:none;white-space:nowrap;user-select:none;transition:border-color .2s,color .2s,box-shadow .2s}
.rank-filter summary::-webkit-details-marker{display:none}
.rank-filter summary:hover,.rank-filter[open] summary{border-color:#1890ff;color:#1890ff}
.rank-filter.is-active summary{border-color:#1890ff;background:#f2f8ff;color:#1890ff}
.rank-filter summary:focus-visible{outline:2px solid #409eff;outline-offset:2px}
.rank-summary-text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rank-arrow{color:inherit;font-size:10px;transition:transform .2s}
.rank-filter[open] .rank-arrow{transform:rotate(180deg)}
.rank-menu{position:absolute;z-index:20;top:calc(100% + 6px);right:0;width:var(--rank-panel-width);padding:8px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;box-shadow:0 10px 24px rgba(15,23,42,.1)}
.rank-menu-header{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:6px;color:#475569;font:600 11px Arial,sans-serif}
.rank-clear{padding:0;border:0;background:transparent;color:#1890ff;font:11px Arial,sans-serif;cursor:pointer}
.rank-clear:disabled{color:#94a3b8;cursor:default}
.rank-menu-options{display:flex;flex-direction:column;gap:4px}
.rank-option{display:flex;align-items:center;gap:6px;padding:5px 6px;border-radius:6px;color:#334155;font:12px Arial,sans-serif;cursor:pointer;white-space:nowrap}
.rank-option:hover{background:#f8fafc}
.rank-option input{margin:0;accent-color:#409eff}
[hidden]{display:none!important}
main{padding:18px 0 8px}
.breadcrumb{display:flex;flex-wrap:wrap;align-items:center;gap:9px;margin:12px 0 0;color:#697583;font-size:12px}
.breadcrumb a{color:#5c7185;text-decoration:none}
.breadcrumb a:hover{text-decoration:underline;color:var(--color-primary)}
.detail-card{width:min(100%,520px);margin:0 auto;padding:18px 20px;border:1px solid #e5ded6;border-radius:8px;background:#fffdfa;color:#334155;font-size:14px;line-height:20px;box-shadow:0 1px 2px rgba(80,67,51,.04)}
.detail-content{padding:0 2px 2px}
.conference-detail-title{display:flex;align-items:center;gap:10px;margin:0;color:#292d33;font-size:27px;font-weight:500;line-height:1.15}
.conference-detail-title-text{min-width:0;overflow-wrap:anywhere}
.conference-detail-star-count{display:inline-flex;flex:none;align-items:center;gap:4px;padding:3px 7px;border:1px solid #e1dbd3;border-radius:999px;background:#f7f3ee;color:#5f6873;font-size:12px;font-variant-numeric:tabular-nums;font-weight:600;line-height:1}
.conference-detail-star-count svg{color:#e6a23c}
.conference-detail-description{margin:4px 0 14px;color:#67727e;font-size:15px}
.conference-detail-acceptance{margin:-7px 0 12px;color:#75808b;font-size:12px;white-space:pre-wrap}
.conference-detail-dblp{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;margin-left:5px;border-radius:4px;vertical-align:-4px}
.conference-detail-dblp img{width:14px;height:14px;object-fit:contain}
.conference-detail-section{margin:0 0 14px;color:#334155;font-size:13px;line-height:1.45}
.conference-detail-label{display:block;margin:0 0 5px;color:#697583;font-size:11px;font-weight:500;letter-spacing:.18em;line-height:inherit}
.conference-detail-deadline{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-top:6px;padding:9px 10px;border:1px solid #e6e1da;border-radius:7px;background:#fffdfa;color:#4d5b69}
.conference-detail-deadline.is-next{border-color:#9dbbd5;background:#edf5fc;color:#274862}
.conference-detail-deadline.is-passed{color:#77828d}
.conference-detail-deadline-main{min-width:0}
.conference-detail-deadline-name{font-weight:600}
.conference-detail-deadline-name small{margin-left:8px;color:#637d93;font-size:10px;letter-spacing:.12em}
.conference-detail-deadline-date{margin-top:2px;color:#6d7883;font-size:11px}
.conference-detail-deadline-status{flex:none;font-weight:600;white-space:nowrap}
.conference-detail-deadline.is-passed .conference-detail-deadline-status{color:#808a94}
.timezone{color:#6d7883}
.conference-detail-note{margin:6px 0 12px;padding:7px 9px;border-left:2px solid #83a9cc;background:#f2f7fc;color:#566575;font-size:12px}
.conference-detail-next{display:flex;flex-direction:column;align-items:flex-start;gap:4px;margin:2px 0 12px;padding:10px 12px;border:1px solid #e6e0d8;border-radius:8px;background:#fffefa;box-shadow:0 1px 2px rgba(80,67,51,.04)}
.conference-detail-next strong{display:block;width:100%;color:#666;font-size:20px;font-weight:700;line-height:1.25}
.conference-detail-next .countdown-detailed-value{display:block;font-size:clamp(18px,4vw,24px);font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:.01em;line-height:1.2;white-space:nowrap}
.conference-detail-next .countdown-urgent,.conference-detail-deadline-status.countdown-urgent{color:#f56c6c}
.conference-detail-next .countdown-warning,.conference-detail-deadline-status.countdown-warning{color:#e6a23c}
.conference-detail-next .countdown-normal,.conference-detail-deadline-status.countdown-normal{color:#67c23a}
.conference-detail-next .timezone{font-size:13px;font-weight:400}
.conference-detail-timeline{margin:5px 0 16px;padding:0 0 2px}
.conference-detail-timeline-track{position:relative;height:34px;margin:0 12px}
.conference-detail-timeline-line{position:absolute;top:25px;right:0;left:0;height:3px;border-radius:999px;background:#d9dfe5}
.conference-detail-timeline-markers{position:absolute;inset:0}
.conference-detail-timeline-marker{position:absolute;top:21px;width:9px;height:9px;margin-left:-4px;border:2px solid #6f9fca;border-radius:50%;background:#fffefa}
.conference-detail-timeline-marker.is-abstract{border-radius:2px}
.conference-detail-timeline-marker.is-passed{border-color:#ccc}
.conference-detail-timeline-marker.is-now{top:19px;width:13px;height:13px;margin-left:-6px;border-color:#e6a23c;box-shadow:0 0 0 3px rgba(230,162,60,.16)}
.conference-detail-timeline-marker.is-now::after{position:absolute;bottom:17px;left:50%;transform:translateX(-50%);color:#8a929b;content:"NOW";font-size:9px;font-weight:600;letter-spacing:.08em}
.conference-detail-timeline-range{display:flex;justify-content:space-between;gap:12px;margin:2px 12px 0;color:#87919c;font-size:10px;font-variant-numeric:tabular-nums}
.hint{margin:10px 0 0;color:#87919c;font-size:11px}
.conference-detail-tags{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0}
.conference-detail-tags span,.conference-detail-actions a{display:inline-block;padding:5px 8px;border:0;border-radius:4px;background:#f3f0ec;color:#586573;font-size:12px;text-decoration:none}
.conference-detail-actions{display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:10px 0 2px;border-top:1px solid #e6e1da}
.conference-detail-actions .conference-detail-website{margin-right:auto;padding-left:0;background:transparent;color:#356d9e}
.conference-detail-actions .conference-detail-calendar-link{display:inline-flex;flex:none;align-items:center;gap:5px;padding:5px 8px;border:0;border-radius:4px;background:#f3f0ec;color:#586573;font:12px "Roboto Mono","SF Mono",Monaco,monospace;text-decoration:none;white-space:nowrap;cursor:pointer}
.conference-detail-calendar-link img{display:block;width:16px;height:16px;flex:none;object-fit:contain}
.conference-detail-actions a:hover{color:#24557e}
.conference-detail-calendar-events{display:grid;gap:5px;max-height:180px;margin-top:8px;overflow-y:auto}
.conference-detail-calendar-events a{display:block;padding:6px 8px;border:1px solid #e6e1da;border-radius:5px;color:#356d9e;font-size:11px;line-height:1.4;text-decoration:none}
.conference-detail-calendar-events a:hover{background:#f3f8fc}
.editions{width:min(100%,520px);margin:24px auto 0}
.editions h2,.directory-section h2{margin:0 0 10px;color:#334155;font-size:16px;font-weight:500}
.edition-list{display:flex;flex-wrap:wrap;gap:8px;margin:0;padding:0;list-style:none}
.edition-list a{display:block;padding:6px 9px;border:1px solid #e6e0d8;border-radius:6px;background:#fffefa;color:#356d9e;font-size:12px;text-decoration:none}
.edition-list a:hover{border-color:#9dbbd5;background:#edf5fc}
.directory-section{margin:0 0 25px;padding-top:14px;border-top:1px solid #e8e3dc}
.directory-section:first-of-type{padding-top:0;border-top:0}
.directory-section:last-of-type{margin-bottom:0}
.directory-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:0;padding:0;list-style:none}
.directory-list li{display:flex;min-width:0}
.directory-list a{display:flex;align-items:center;width:100%;padding:9px 10px;border:1px solid #e6e0d8;border-radius:8px;background:#fffefa;color:#334155;font-size:13px;text-decoration:none;box-shadow:0 1px 2px rgba(80,67,51,.04)}
.directory-list a:hover{color:#409eff;border-color:#b8d2e8}
.directory-empty{margin:14px 0;color:#697583;font-size:14px}
.footer{display:flex;align-items:center;min-height:20px;padding:8px 0 16px;color:#666;font-size:14px;line-height:20px}
.footer-text{display:flex;align-items:center;gap:14px;min-width:0}
.footer-credit{min-width:0}
.footer a{color:#666}
@media(max-width:600px){.home{padding:0 16px}.header-main{display:grid;grid-template-columns:minmax(0,1fr) auto;padding-right:0}.header-main .title{grid-column:1/-1;grid-row:1}.header-github{grid-column:1;grid-row:2;justify-self:start}.header-auth{position:static;grid-column:2;grid-row:2;justify-self:end}.github-login-button span{display:none}.github-login-button{width:30px;padding:0}.title{font-size:24px}.directory-toolbar{align-items:flex-start}.toolbar-search-wrap{width:100%}.toolbar-ranks{width:100%;justify-content:space-between;margin-left:0}.rank-filter{flex:1;min-width:0}.rank-filter summary{width:100%}.detail-card{padding:18px 16px}.conference-detail-title{font-size:24px}.footer-text{font-size:14px;text-align:center}}
"""


def generate(conferences: list[dict], categories: dict[str, str], output: Path, acceptances: dict[str, list[dict]] | None = None) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    acceptances = acceptances or {}
    written = []
    seen = set()
    for conference in conferences:
        for edition in conference.get("confs", []):
            path = edition_path(conference, edition)
            if path in seen:
                raise ValueError(f"Duplicate conference page: {path}")
            seen.add(path)
            target = output / path.lstrip("/") / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(edition_page(conference, edition, categories, acceptances), encoding="utf-8")
            written.append(path)
    directory = output / "conferences"
    directory.mkdir(exist_ok=True)
    (directory / "index.html").write_text(directory_page(conferences, categories), encoding="utf-8")
    (directory / "style.css").write_text(stylesheet(), encoding="utf-8")
    (directory / "controls.js").write_text((ROOT / "scripts/seo_page_controls.js").read_text(encoding="utf-8"), encoding="utf-8")
    urls = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in ("/", "/conferences/", *sorted(written)):
        SubElement(SubElement(urls, "url"), "loc").text = BASE_URL + path
    (output / "sitemap.xml").write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(urls, encoding="utf-8") + b"\n")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "public/conference/allconf.json")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    conferences = json.loads(args.input.read_text(encoding="utf-8"))
    categories = {item["sub"]: item["name"] for item in yaml.safe_load((ROOT / "conference/types.yml").read_text(encoding="utf-8"))}
    acceptance_file = ROOT / "public/conference/allacc.json"
    acceptance_rows = json.loads(acceptance_file.read_text(encoding="utf-8")) if acceptance_file.exists() else []
    acceptances = {row["title"]: row.get("accept_rates", []) for row in acceptance_rows}
    written = generate(conferences, categories, args.output, acceptances)
    print(f"Generated {len(written)} conference pages and sitemap.xml")


if __name__ == "__main__":
    main()
