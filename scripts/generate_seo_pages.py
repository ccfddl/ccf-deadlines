#!/usr/bin/env python3
"""Generate crawlable conference pages from the same data used by the app."""

import argparse
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, tostring

import yaml

from conference_dates import conference_opening
from conference_share_image import share_image


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
    return f"/venues/{conference['sub'].lower()}/{slug}-{edition['year']}/"


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
        f'<a href="/venues/?categories={text(sub)}"{(" aria-current=\"page\"" if sub == active_sub else "")}'
        f' data-category="{text(sub)}" data-zh="{text(name)}" data-en="{text(CATEGORY_EN_BY_SUB.get(sub, name))}">{text(name)}</a>'
        for sub, name in categories.items()
    )


def directory_startup() -> str:
    return '''<script id="directory-startup-recovery">
    (() => {
      const root = document.getElementById('directory-controls-root');
      const ready = () => Boolean(root.querySelector('.conference-controls'));
      const cleanup = () => {
        clearTimeout(timer);
        window.removeEventListener('DirectoryControlsReady', cleanup);
        window.removeEventListener('DirectoryControlsFailed', fail);
        window.removeEventListener('error', onError, true);
      };
      const fail = () => {
        if (ready()) { cleanup(); return; }
        let status = root.querySelector('.directory-controls-loading');
        if (!status) { status = document.createElement('p'); root.append(status); }
        status.className = 'directory-controls-loading';
        status.setAttribute('role', 'alert');
        status.textContent = document.documentElement.lang === 'en'
          ? 'Unable to load filters. Venue links are still available. '
          : '筛选控件加载失败，仍可浏览下方会议链接。';
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.textContent = document.documentElement.lang === 'en' ? 'Retry' : '重试';
        retry.onclick = () => location.reload();
        status.append(retry);
        cleanup();
      };
      const onError = event => {
        if (event.target?.tagName === 'SCRIPT' && event.target.src.includes('/venues/app-')) fail();
      };
      const timer = setTimeout(fail, 30000);
      window.addEventListener('DirectoryControlsReady', cleanup);
      window.addEventListener('DirectoryControlsFailed', fail);
      window.addEventListener('error', onError, true);
    })();
    </script>'''


def layout(title: str, description: str, canonical: str, body: str, navigation: str = "", breadcrumb: str = "", detail_page: bool = False, app_assets: str = "", static_css: str = "/venues/style.css", social_image: str = "", social_image_alt: str = "") -> str:
    social = ""
    if social_image:
        social = f'''<meta property="og:type" content="website">
  <meta property="og:site_name" content="CCFDDL">
  <meta property="og:title" content="{text(title)}">
  <meta property="og:description" content="{text(description)}">
  <meta property="og:url" content="{text(canonical)}">
  <meta property="og:image" content="{text(social_image)}">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{text(social_image_alt)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@ccfddl">
  <meta name="twitter:title" content="{text(title)}">
  <meta name="twitter:description" content="{text(description)}">
  <meta name="twitter:image" content="{text(social_image)}">
  <meta name="twitter:image:alt" content="{text(social_image_alt)}">'''
    clock_control = (
        '<div class="toolbar-clock"><time class="toolbar-clock-value" id="display-clock">—</time>'
        '<span class="toolbar-timezone"><span>(</span><label class="toolbar-timezone-picker">'
        '<select id="display-timezone" aria-label="Select display timezone"><option value="UTC">UTC</option></select>'
        '<span class="toolbar-timezone-arrow" aria-hidden="true">⌄</span></label><span> time)</span></span></div>'
    )
    filters = (
        f'<div class="directory-toolbar detail-toolbar">{clock_control}</div>'
        if detail_page else f'<div id="directory-controls-root"><nav class="directory-categories" style="display:flex;flex-wrap:wrap;gap:10px" aria-label="Venue categories">{navigation}</nav><p class="directory-controls-loading" role="status">Loading filters…</p></div>{directory_startup()}'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{text(title)}</title>
  <meta name="description" content="{text(description)}">
  <link rel="canonical" href="{text(canonical)}">
  {social}
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2114972416819347" crossorigin="anonymous"></script>
  <link rel="icon" href="/favicon.ico">
  <link rel="icon" type="image/svg+xml" href="/ccfddl-logo.svg">
  {app_assets}
  <link rel="stylesheet" href="{text(static_css)}">
</head>
<body class="{'detail-page' if detail_page else 'directory-page'}">
  <div class="home">
    <header class="site-header">
      <div class="header-main"><a class="title" href="{BASE_URL}/"><span>CCFDDL&nbsp;Open&nbsp;</span><span class="title-accent">Deadlines</span></a><div class="header-github"><a class="github-star-link" href="https://github.com/ccfddl/ccf-deadlines" target="_blank" rel="noopener noreferrer" aria-label="Star ccfddl/ccf-deadlines on GitHub"><svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.62 7.62 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg><span>Star</span><span class="github-star-count" id="github-star-count" hidden></span></a><a class="header-x-link" href="https://x.com/ccfddl" target="_blank" rel="noopener noreferrer" aria-label="Follow CCFDDL on X" title="Follow CCFDDL on X"><svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.07-4.425 5.07H.316l5.733-6.57L0 .75h5.063l3.495 4.633L12.601.75Zm-.86 13.028h1.36L4.323 2.145H2.865z"/></svg><span>Follow</span></a></div><div class="header-auth" id="github-auth"><a class="github-login-button" id="github-login-link" href="{BASE_URL}/api/auth/github?return_to=%2F"><svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.62 7.62 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg><span data-zh="使用 GitHub 登录" data-en="Sign in with GitHub">使用 GitHub 登录</span></a></div></div>
      <div class="el-row subtitle">Worldwide Conference Deadline Countdowns. Preview in <a href="{BASE_URL}/?view=table">tabular form</a> or <a href="{BASE_URL}/venues/" target="_blank" rel="noopener noreferrer">directory</a>.</div>
      <div class="el-row subtitle">*Disclaimer: The data provided by ccfddl is agenticly collected and for reference purposes only.</div>
      {breadcrumb}
      {filters}
    </header>
    <main>{body}</main>
    <footer class="footer"><div class="footer-text"><span class="footer-credit">Maintained by @ccfddl. If you find it useful, star or follow <a href="https://github.com/ccfddl" target="_blank" rel="noopener noreferrer">@ccfddl</a> on Github.</span></div></footer>
  </div>
  <script>(function(){{
    function setLanguage(english){{
      document.documentElement.lang=english?'en':'zh-CN';
      document.querySelectorAll('[data-en][data-zh]').forEach(function(node){{node.textContent=english?node.dataset.en:node.dataset.zh;}});
    }}
    var stored;try{{stored=localStorage.getItem('language_preference');}}catch(error){{}}
    setLanguage(stored==='en'||(stored!=='zh'&&!navigator.language.toLowerCase().startsWith('zh')));
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
  <script src="/venues/controls.js" defer></script>
</body>
</html>
"""


def deadline_rows(edition: dict) -> str:
    labels = (
        ("abstract_deadline", "Abstract Submission"),
        ("deadline", "Paper Submission"),
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
    if not rows:
        rows.append(("", '<div class="conference-detail-deadline">Dates to be announced</div>'))
    opening = conference_opening(edition)
    opening_date = format_deadline(opening, timezone) if opening else "TBD"
    attributes = f' data-raw="{text(opening)}" data-source-tz="{text(timezone)}"' if opening else ""
    rows.append((opening or "9999", (
        f'<div class="conference-detail-deadline" data-deadline-type="opening"{attributes}>'
        '<div class="conference-detail-deadline-main">'
        '<div class="conference-detail-deadline-name">Conference Opening</div>'
        f'<div class="conference-detail-deadline-date">{opening_date}</div></div>'
        '<span class="conference-detail-deadline-status" aria-live="off"></span></div>'
    )))
    return "".join(row for _, row in sorted(rows, key=lambda entry: entry[0]))


def edition_page(conference: dict, edition: dict, categories: dict[str, str], acceptances: dict[str, list[dict]], static_css: str = "/venues/style.css") -> str:
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
    opening = conference_opening(edition)
    if opening:
        all_known.append(opening)
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
    breadcrumb = f'<nav class="breadcrumb" aria-label="Breadcrumb"><a href="{BASE_URL}/">Main site</a><span>/</span><a href="/venues/">All venues</a><span>/</span><span>{text(name)} {year}</span></nav>'
    return layout(title, description, canonical, body, breadcrumb=breadcrumb, detail_page=True, static_css=static_css, social_image=canonical + "share.png", social_image_alt=f"{name} {year}: conference dates and location on CCFDDL")


def directory_page(conferences: list[dict], categories: dict[str, str], app_assets: str = "", static_css: str = "/venues/style.css") -> str:
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
    body = f'<p class="directory-empty" id="directory-empty" hidden>No matching venues.</p>{"".join(sections)}'
    breadcrumb = f'<nav class="breadcrumb" aria-label="Breadcrumb"><a href="{BASE_URL}/">Main site</a><span>/</span><span>All venues</span></nav>'
    return layout("Venue Deadlines Directory | CCFDDL", "Find conference deadlines, dates, locations and official websites for every conference tracked by CCFDDL.", BASE_URL + "/venues/", body, category_links(categories), breadcrumb, app_assets=app_assets, static_css=static_css)


def stylesheet() -> str:
    return """/* Matches the main site's header, conference cards and detail dialog. */
:root{--color-primary:#409eff;--color-text-primary:#2c3e50;--color-text-secondary:#666;--color-border-light:#ebeef5}
.detail-page *, main *, .header-main *, .breadcrumb *{box-sizing:border-box}
body.detail-page{margin:0}
body{background:#faf9f7;color:var(--color-text-primary);font-family:"PingFang SC","Microsoft YaHei","Roboto","Helvetica Neue",Helvetica,Arial,sans-serif}
a{color:var(--color-primary);text-decoration:underline;text-decoration-color:currentColor}
a:hover{color:#d9554f}
.detail-page .home{max-width:1240px;margin:0 auto;padding:0 20px;font-family:"Roboto Mono","SF Mono",Monaco,monospace;-webkit-font-smoothing:antialiased}
.site-header{padding-top:8px}
.header-main{position:relative;display:flex;align-items:center;flex-wrap:wrap;gap:7px;min-height:36px;padding-right:250px;font-size:16px}
.header-x-link:focus-visible{outline:2px solid currentColor;outline-offset:2px}
.header-github{display:flex;align-items:center;gap:6px}
.title{display:inline-flex;align-items:baseline;color:var(--color-text-primary);font-size:29px;line-height:1;text-decoration:none;border-bottom:2px solid currentColor;white-space:nowrap}
.title:hover{color:var(--color-text-primary)}
.title-accent{color:#d9554f;font-style:italic}
.github-star-link,.header-x-link{display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 9px;border:1px solid #d9d3cb;border-radius:8px;background:#fff;box-shadow:0 1px 2px rgba(63,55,47,.05);color:#3f4751;font-size:13px;font-weight:600;line-height:1;text-decoration:none;white-space:nowrap}
.github-star-link:hover,.header-x-link:hover{border-color:#bfc8d1;background:#f7f9fb;color:#29394b}
.github-star-link svg,.header-x-link svg{width:16px;height:16px}
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
.directory-toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:10px;min-height:46px;padding:4px 0 10px;border-bottom:1px solid #e8e3dc}
.detail-toolbar{margin-top:12px;padding-top:12px;border-top:1px solid #e8e3dc}
.detail-toolbar .toolbar-clock{display:inline-flex;align-items:center;flex-wrap:wrap;gap:4px 8px;color:#666;font-size:14px;white-space:nowrap}
.detail-toolbar .toolbar-clock-value{color:#666;font-variant-numeric:tabular-nums;font-weight:500}
.detail-toolbar .toolbar-timezone{display:inline-flex;align-items:center;gap:0;line-height:1.4}
.detail-toolbar .toolbar-timezone-picker{display:inline-flex;align-items:center;cursor:pointer}
.detail-toolbar .toolbar-timezone select{max-width:190px;padding:0 0 0 2px;border:0;appearance:none;background:transparent;color:#666;font:inherit;cursor:pointer}
.detail-toolbar .toolbar-timezone-arrow{position:relative;top:-1px;margin-left:3px;font-size:12px;line-height:1;pointer-events:none}
.detail-toolbar .toolbar-timezone>span:last-child{margin-left:3px}
.directory-categories{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}.directory-controls-loading{font-size:14px;color:#666}
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
@media(max-width:600px){.detail-page .home{padding:0 16px}.header-main{display:grid;grid-template-columns:minmax(0,1fr) auto;padding-right:0}.header-main .title{grid-column:1/-1;grid-row:1}.header-github{grid-column:1;grid-row:2;justify-self:start}.header-x-link{justify-content:center;width:30px;padding:0}.header-x-link span{display:none}.header-auth{position:static;grid-column:2;grid-row:2;justify-self:end}.github-login-button span{display:none}.github-login-button{width:30px;padding:0}.title{font-size:24px}.detail-toolbar{align-items:flex-start}.detail-card{padding:18px 16px}.conference-detail-title{font-size:24px}.footer-text{font-size:14px;text-align:center}}
"""


def shared_app_assets(output: Path) -> str:
    index = output / "index.html"
    if not index.exists():
        # Data-only generation (including unit fixtures) keeps the static directory usable.
        return ""
    built = index.read_text(encoding="utf-8")
    from html.parser import HTMLParser

    class Assets(HTMLParser):
        css = ""
        module = ""
        wasm = ""

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            href = attrs.get("href", "")
            if tag != "link":
                return
            if attrs.get("rel") == "stylesheet":
                self.css = href
            elif attrs.get("rel") == "modulepreload" and href.endswith(".js") and "/snippets/" not in href:
                self.module = href
            elif attrs.get("type") == "application/wasm":
                self.wasm = href

    assets = Assets()
    assets.feed(built)
    if not all((assets.css, assets.module, assets.wasm)):
        raise ValueError("Generate conference pages after Trunk has built the shared app assets")
    bootstrap = (
        "try {\n"
        f"  const {{ default: init }} = await import({json.dumps(assets.module)});\n"
        f"  await init({{ module_or_path: {json.dumps(assets.wasm)} }});\n"
        "  if (!document.querySelector('#directory-controls-root .conference-controls')) throw new Error('Directory controls did not mount');\n"
        "  window.dispatchEvent(new Event('DirectoryControlsReady'));\n"
        "} catch (error) {\n"
        "  console.error('Directory controls failed to load', error);\n"
        "  window.dispatchEvent(new Event('DirectoryControlsFailed'));\n"
        "}\n"
    )
    directory = output / "venues"
    directory.mkdir(exist_ok=True)
    filename = f'app-{hashlib.sha256(bootstrap.encode()).hexdigest()[:16]}.js'
    (directory / filename).write_text(bootstrap, encoding="utf-8")
    return f'<link rel="stylesheet" href="{text(assets.css)}"><script type="module" src="/venues/{filename}"></script>'


def generate(conferences: list[dict], categories: dict[str, str], output: Path, acceptances: dict[str, list[dict]] | None = None) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    for asset in ("favicon.ico", "ccfddl-logo.svg"):
        shutil.copy2(ROOT / "public" / asset, output / asset)
    acceptances = acceptances or {}
    directory = output / "venues"
    directory.mkdir(exist_ok=True)
    css = stylesheet()
    css_filename = f'style-{hashlib.sha256(css.encode()).hexdigest()[:16]}.css'
    (directory / css_filename).write_text(css, encoding="utf-8")
    # Keep the previous URL available for already-cached edition pages.
    (directory / "style.css").write_text(css, encoding="utf-8")
    static_css = f'/venues/{css_filename}'
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
            share_image(conference, edition, CATEGORY_EN_BY_SUB.get(conference["sub"], conference["sub"]), target.parent / "share.png")
            target.write_text(edition_page(conference, edition, categories, acceptances, static_css), encoding="utf-8")
            written.append(path)
    assets = shared_app_assets(output)
    directory = output / "venues"
    directory.mkdir(exist_ok=True)
    (directory / "index.html").write_text(directory_page(conferences, categories, assets, static_css), encoding="utf-8")
    (directory / "controls.js").write_text((ROOT / "scripts/seo_page_controls.js").read_text(encoding="utf-8"), encoding="utf-8")
    urls = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in ("/", "/venues/", *sorted(written)):
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
