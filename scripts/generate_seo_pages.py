#!/usr/bin/env python3
"""Generate crawlable conference pages from the same data used by the app."""

import argparse
import json
import re
from collections import defaultdict
from html import escape
from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import Element, SubElement, tostring

import yaml


ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://ccfddl.com"
KNOWN_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}(?::\d{2})?)?$")


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
        return "To be announced"
    shown = raw[:-3] if len(raw) == 19 else raw
    return f"{text(shown)} <span class=\"timezone\">{text(timezone)}</span>"


def layout(title: str, description: str, canonical: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{text(title)}</title>
  <meta name="description" content="{text(description)}">
  <link rel="canonical" href="{text(canonical)}">
  <link rel="stylesheet" href="/conferences/style.css">
</head>
<body>
  <header class="site-header"><a class="brand" href="/">CCFDDL <strong>Open Deadlines</strong></a><nav><a href="/conferences/">Conference directory</a><a href="/?view=table">Tabular form</a></nav></header>
  <main>{body}</main>
  <footer>Maintained by <a href="https://github.com/ccfddl/ccf-deadlines">@ccfddl</a>. Conference data is for reference; verify details on the official website.</footer>
</body>
</html>
"""


def deadline_rows(edition: dict) -> str:
    labels = (
        ("abstract_deadline", "Abstract deadline / 摘要截止"),
        ("deadline", "Paper deadline / 投稿截止"),
        ("rebuttal_deadline", "Rebuttal deadline"),
        ("decision_deadline", "Decision date"),
    )
    rows = []
    for point in edition.get("timeline", []):
        comment = str(point.get("comment") or "").strip()
        for field, label in labels:
            if not point.get(field):
                continue
            note = f"<small>{text(comment)}</small>" if comment and field == "deadline" else ""
            rows.append(
                f"<tr><th scope=\"row\">{label}</th><td>{format_deadline(point[field], edition.get('timezone', ''))}{note}</td></tr>"
            )
    return "".join(rows) or '<tr><td colspan="2">No deadline announced yet.</td></tr>'


def edition_page(conference: dict, edition: dict, categories: dict[str, str]) -> str:
    name, year = conference["title"], edition["year"]
    path = edition_path(conference, edition)
    canonical = BASE_URL + path
    known = [str(point.get("deadline")) for point in edition.get("timeline", []) if KNOWN_DATE.fullmatch(str(point.get("deadline", "")))]
    deadline_summary = f"paper deadline {min(known)[:16]} {edition.get('timezone', '')}" if known else "paper deadline to be announced"
    description = f"{name} {year}: {deadline_summary}; {edition.get('date') or 'conference dates TBA'}; {edition.get('place') or 'location TBA'}. Deadlines and past editions on CCFDDL."
    title = f"{name} {year} Deadline and Conference Dates | CCFDDL"
    category = categories.get(conference["sub"], conference["sub"])
    ranks = conference.get("rank") or {}
    rank_text = " · ".join(f"{label} {text(ranks[key])}" for key, label in (("ccf", "CCF"), ("core", "CORE"), ("thcpl", "TH-CPL")) if ranks.get(key))
    official = safe_link(str(edition.get("link") or ""))
    official_link = f'<a class="button" href="{text(official)}" rel="noopener noreferrer">Official conference website ↗</a>' if official else ""
    other_editions = sorted((item for item in conference["confs"] if item["year"] != year), key=lambda item: item["year"], reverse=True)
    history = "".join(f'<li><a href="{text(edition_path(conference, item))}">{text(name)} {item["year"]}</a></li>' for item in other_editions)
    body = f"""
    <nav class="breadcrumb"><a href="/conferences/">All conferences</a> / {text(name)} {year}</nav>
    <p class="eyebrow">{text(category)}{(' · ' + rank_text) if rank_text else ''}</p>
    <h1>{text(name)} {year} deadlines</h1>
    <p class="lead">{text(conference.get('description') or name)}</p>
    <div class="facts"><div><strong>Conference dates / 会议时间</strong><span>{text(edition.get('date') or 'To be announced')}</span></div><div><strong>Location / 地点</strong><span>{text(edition.get('place') or 'To be announced')}</span></div></div>
    <section><h2>Submission deadlines / 投稿时间</h2><table><tbody>{deadline_rows(edition)}</tbody></table><p class="hint">Times use the conference's stated time zone. Check the official site before submitting.</p>{official_link}</section>
    <section><h2>Other editions</h2><ul class="edition-list">{history or '<li>No earlier edition in the database.</li>'}</ul></section>
    """
    return layout(title, description, canonical, body)


def directory_page(conferences: list[dict], categories: dict[str, str]) -> str:
    groups = defaultdict(list)
    for conference in conferences:
        latest = max(conference["confs"], key=lambda item: item["year"])
        groups[conference["sub"]].append((conference, latest))
    sections = []
    for sub in sorted(groups):
        links = "".join(
            f'<li><a href="{text(edition_path(conference, edition))}">{text(conference["title"])} {edition["year"]}</a></li>'
            for conference, edition in sorted(groups[sub], key=lambda pair: pair[0]["title"].lower())
        )
        sections.append(f'<section><h2>{text(categories.get(sub, sub))}</h2><ul class="directory-list">{links}</ul></section>')
    body = f'<h1>Conference deadlines / 会议截稿时间</h1><p class="lead">Browse the latest edition of each conference tracked by CCFDDL.</p>{"".join(sections)}'
    return layout("Conference Deadlines Directory | CCFDDL", "Find conference deadlines, dates, locations and official websites for every conference tracked by CCFDDL.", BASE_URL + "/conferences/", body)


def stylesheet() -> str:
    return """*{box-sizing:border-box}body{margin:0;background:#faf9f7;color:#2c3e50;font:16px/1.55 Arial,Helvetica,sans-serif}a{color:#409eff}a:hover{color:#d9554f}.site-header{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:18px max(24px,calc((100vw - 1100px)/2));border-bottom:1px solid #e6e0d8;background:#fffefa}.brand{color:#2c3e50;font-size:23px;text-decoration:none}.brand strong{color:#409eff;font-weight:500}.site-header nav{display:flex;gap:18px;font-size:14px}main{max-width:1100px;margin:0 auto;padding:26px 24px 60px}.breadcrumb,.eyebrow,.hint{color:#66717d;font-size:14px}.breadcrumb{margin-bottom:24px}.eyebrow{margin-bottom:4px}h1{margin:0 0 8px;font-size:32px;font-weight:500;line-height:1.2}h2{font-size:21px;font-weight:500}.lead{margin:0 0 26px;color:#53606d}.facts{display:flex;flex-wrap:wrap;gap:12px}.facts div{display:flex;flex-direction:column;min-width:220px;flex:1;padding:15px;background:#fff;border:1px solid #e6e0d8;border-radius:8px}.facts strong{font-size:13px;font-weight:500;color:#66717d}.facts span{margin-top:6px}section{margin-top:32px}table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e6e0d8}th,td{padding:10px 14px;border-bottom:1px solid #ebe6df;text-align:left;vertical-align:top}th{width:35%;font-weight:500}td small{display:block;color:#66717d}.timezone{color:#66717d}.button{display:inline-block;padding:9px 14px;border:1px solid #409eff;border-radius:6px;text-decoration:none}.edition-list,.directory-list{padding-left:20px}.edition-list{display:flex;flex-wrap:wrap;column-gap:32px}.directory-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:5px 24px}footer{padding:24px;border-top:1px solid #e6e0d8;color:#66717d;text-align:center;font-size:13px}@media(max-width:600px){.site-header{align-items:flex-start;flex-direction:column}.site-header nav{flex-wrap:wrap}h1{font-size:27px}th{width:42%}}
"""


def generate(conferences: list[dict], categories: dict[str, str], output: Path) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
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
            target.write_text(edition_page(conference, edition, categories), encoding="utf-8")
            written.append(path)
    directory = output / "conferences"
    directory.mkdir(exist_ok=True)
    (directory / "index.html").write_text(directory_page(conferences, categories), encoding="utf-8")
    (directory / "style.css").write_text(stylesheet(), encoding="utf-8")
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
    categories = {item["sub"]: item["name_en"] for item in yaml.safe_load((ROOT / "conference/types.yml").read_text(encoding="utf-8"))}
    written = generate(conferences, categories, args.output)
    print(f"Generated {len(written)} conference pages and sitemap.xml")


if __name__ == "__main__":
    main()
