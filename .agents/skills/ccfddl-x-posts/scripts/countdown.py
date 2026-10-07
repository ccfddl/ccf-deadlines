#!/usr/bin/env python3
"""Deterministic CCFDDL selector/card builder and conservative publication ledger.
No network calls and no social-media publishing. Python 3.10+, PyYAML, Pillow.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import yaml

UTC = timezone.utc
LINK = "https://ccfddl.com"
DISPLAY_LINK = "ccfddl.com"
HASHTAGS = "#ccfddl #conf_deadline #蓝v"
ZONE_ALIASES = {"AoE": "UTC-12", "PT": "America/Los_Angeles", "ET": "America/New_York"}
NON_SUBMISSION = re.compile(r"\b(rebuttal|notification|decision|camera[- ]ready|author response|revision[- ]only|commitment)\b", re.I)


def iso(dt):
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def as_utc(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("An explicit UTC offset is required")
    return dt.astimezone(UTC)


def parse_zone(value):
    name = ZONE_ALIASES.get(str(value), str(value))
    if name in ("UTC", "GMT"):
        return UTC
    m = re.fullmatch(r"(?:UTC|GMT)([+-])(\d{1,2})(?::?(\d{2}))?", name)
    if m:
        hours, mins = int(m[2]), int(m[3] or 0)
        if hours > 14 or mins > 59 or (hours == 14 and mins):
            raise ValueError(f"Invalid UTC offset: {name}")
        return timezone(timedelta(minutes=(hours * 60 + mins) * (1 if m[1] == "+" else -1)))
    if "/" not in name:
        raise ValueError(f"Unknown or ambiguous timezone: {value}")
    return ZoneInfo(name)


def parse_deadline(value, zone):
    if value is None or str(value).strip().upper() in ("TBD", "TBA", "", "N/A"):
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?", str(value)):
        raise ValueError(f"Incomplete or unsupported deadline: {value}")
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        return dt.astimezone(UTC)
    tz = parse_zone(zone)
    localized = dt.replace(tzinfo=tz)
    if isinstance(tz, ZoneInfo):
        other = dt.replace(tzinfo=tz, fold=1)
        if localized.utcoffset() != other.utcoffset():
            raise ValueError(f"Ambiguous or nonexistent DST deadline: {value} {zone}")
        if localized.astimezone(UTC).astimezone(tz).replace(tzinfo=None) != dt:
            raise ValueError(f"Nonexistent DST deadline: {value} {zone}")
    return localized.astimezone(UTC)


def countdown(seconds, short=False):
    if seconds <= 0:
        raise ValueError("Expired deadlines must never render")
    if seconds < 60:
        return "<1m" if short else "<1 min left"
    if seconds < 3600:
        n = math.floor(seconds / 60)
        return f"{n}m" if short else f"{n} min left"
    if seconds <= 86400:
        n = math.floor(seconds / 3600)
        return f"{n}h" if short else f"{n} hour{'s' if n != 1 else ''} left"
    n = math.floor(seconds / 86400)
    return f"{n}d" if short else f"{n} day{'s' if n != 1 else ''} left"


def detail_url(event):
    """Match scripts/generate_seo_pages.py edition_path; verify the live page before publishing."""
    subject = str(event.get("source_subject", "")).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", str(event.get("conference", "")).lower()).strip("-")
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", str(event.get("id", "")).lower()).strip("-")
    year = str(event.get("year", ""))
    if not re.fullmatch(r"[a-z]+", subject) or not slug or not re.fullmatch(r"\d{4}", year):
        raise ValueError("Cannot resolve canonical conference detail URL")
    return f"{LINK}/venues/{subject}/{slug}-{year}/"


def weighted_length(text):
    """Conservative X weight: count each entire approved canonical URL as 23."""
    text = unicodedata.normalize("NFC", text)
    urls = re.findall(r"https?://[^\s]+", text, re.I)
    for url in urls:
        if not re.fullmatch(r"https://ccfddl\.com(?:/|/venues/[a-z]+/[a-z0-9]+(?:-[a-z0-9]+)*-\d{4}/)?", url):
            raise ValueError("Only canonical CCFDDL home/detail URLs are allowed")
    rest = re.sub(r"https?://[^\s]+", "", text, flags=re.I)
    if re.search(r"(?:https?://|www\.)", rest, re.I):
        raise ValueError("Only canonical CCFDDL home/detail URLs are allowed")
    bare_domain = r"(?<![\w@./-])ccfddl\.com(?![\w./:-])"
    bare_count = len(re.findall(bare_domain, rest))
    rest = re.sub(bare_domain, "", rest)
    return 23 * (len(urls) + bare_count) + sum(1 if (ord(c) <= 0x10FF or 0x2000 <= ord(c) <= 0x200D or 0x2010 <= ord(c) <= 0x201F or 0x2032 <= ord(c) <= 0x2037) else 2 for c in rest)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def snapshot_from_git(repo, output):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True)
    commit = git("rev-parse", "HEAD").strip()
    remote = git("remote", "get-url", "origin").strip()
    paths = [p for p in git("ls-tree", "-r", "--name-only", commit, "conference").splitlines() if p.endswith((".yml", ".yaml"))]
    files = []
    for path in paths:
        raw = git("show", f"{commit}:{path}")
        files.append({"path": path, "sha256": sha(raw), "content": raw})
    if not files:
        raise ValueError("No conference YAML files at this commit")
    # git show reads committed objects only, so dirty worktree files cannot leak in.
    obj = {"repository": remote, "commit": commit, "fetched_at_utc": iso(datetime.now(UTC)), "complete_catalog": True, "files": files}
    Path(output).write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def load_snapshot(path):
    obj = json.loads(Path(path).read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", obj["commit"]):
        raise ValueError("Require a complete pinned source commit")
    if obj.get("repository", "").removesuffix(".git") not in ("https://github.com/ccfddl/ccf-deadlines", "git@github.com:ccfddl/ccf-deadlines"):
        raise ValueError("Snapshot must identify the verified canonical CCFDDL repository")
    if not obj.get("files"):
        raise ValueError("Missing source provenance or files")
    as_utc(obj["fetched_at_utc"])
    rows = []
    seen = set()
    for file in obj["files"]:
        if file["path"] in seen or not file["path"].startswith("conference/") or ".." in Path(file["path"]).parts:
            raise ValueError("Invalid or duplicated source path")
        seen.add(file["path"])
        if sha(file["content"]) != file["sha256"]:
            raise ValueError(f"Source hash mismatch: {file['path']}")
        data = yaml.safe_load(file["content"])
        if not isinstance(data, list):
            raise ValueError(f"Expected conference array: {file['path']}")
        for row in data:
            rows.append((row, file["path"]))
    return obj, rows


def select(rows, config, now):
    categories = {"AI": [], "Data Systems": []}
    issues = []
    include = {x.casefold() for x in config.get("include_titles", [])}
    exclude = {x.casefold() for x in config.get("exclude_titles", [])}
    include_paths = set(config.get("include_paths", []))
    stage_selection = config.get("stage_selection", "nearest")
    if stage_selection not in ("nearest", "all_future"):
        raise ValueError("stage_selection must be nearest or all_future")
    allowed = set(config.get("ccf_ranks", ["A", "B"]))
    horizon = timedelta(days=int(config.get("horizon_days", 120)))
    for row, path in rows:
        title = str(row.get("title", "")).strip()
        if not title or title.casefold() in exclude:
            continue
        rank = str((row.get("rank") or {}).get("ccf", "N"))
        if path not in include_paths and title.casefold() not in include and rank not in allowed:
            continue
        category = "AI" if row.get("sub") == "AI" else "Data Systems"
        for conf in row.get("confs", []):
            timelines = conf.get("timeline") or []
            submission_indices = [i for i, entry in enumerate(timelines) if not NON_SUBMISSION.search(str(entry.get("comment", "")))]
            for index, item in enumerate(timelines):
                comment = str(item.get("comment", ""))
                if NON_SUBMISSION.search(comment):
                    issues.append({"source": path, "id": conf.get("id"), "round": index + 1, "reason": "Review non-submission wording in timeline comment"})
                    continue
                candidates = []
                abstract = None
                try:
                    for key, stage in (("abstract_deadline", "abstract"), ("deadline", "paper")):
                        raw = item.get(key)
                        source_zone = conf.get("timezone")
                        deadline = parse_deadline(raw, source_zone)
                        if key == "abstract_deadline":
                            abstract = deadline
                        if deadline and now < deadline <= now + horizon:
                            candidates.append((deadline, stage, raw, source_zone))
                except (ValueError, KeyError) as e:
                    issues.append({"source": path, "id": conf.get("id"), "round": index + 1, "reason": str(e)})
                    continue
                if not candidates:
                    continue
                selected_candidates = [min(candidates)] if stage_selection == "nearest" else sorted(candidates)
                identity = str(conf.get("id") or f"{title}-{conf.get('year')}")
                round_number = submission_indices.index(index) + 1
                if len(submission_indices) > 1:
                    round_label = f"R{round_number}"
                else:
                    round_label = ""
                for deadline, stage, original, shown_zone in selected_candidates:
                    event = {"conference": title, "year": conf.get("year"), "id": identity, "round_index": round_number, "timeline_index": index + 1,
                             "round_label": round_label, "stage": stage, "deadline_utc": iso(deadline),
                             "deadline_source": str(original), "timezone_source": shown_zone,
                             "seconds_left": (deadline - now).total_seconds(), "abstract_closed": bool(stage == "paper" and abstract and abstract <= now),
                             "comment": comment, "source_path": path, "source_subject": row.get("sub"), "official_url": conf.get("link"), "rank_ccf": rank}
                    categories[category].append(event)
    for name in categories:
        categories[name].sort(key=lambda e: (e["deadline_utc"], e["conference"].casefold(), e["year"] or 0, e["round_index"], e["stage"]))
        # Equivalent repeated YAML records must never appear twice.
        unique = {}
        for event in categories[name]:
            key = (event["source_path"], event["id"], event["round_index"], event["deadline_utc"], event["stage"])
            unique.setdefault(key, event)
        categories[name] = list(unique.values())
    return categories, issues


def deadline_display(event, seconds=False):
    stamp = datetime.fromisoformat(event["deadline_source"].replace("Z", "+00:00"))
    when = stamp.strftime("%Y/%m/%d %H:%M:%S" if seconds else "%Y/%m/%d %H:%M")
    zone = stamp.strftime("UTC%z") if stamp.tzinfo is not None else event["timezone_source"]
    return when, zone


def display_stage(event):
    # The user explicitly wants abstract_deadline labeled abstract everywhere,
    # even when the organizer calls that stage paper registration.
    if event["stage"] == "abstract" or event.get("deadline_field") == "abstract_deadline":
        return "abstract"
    return event.get("stage_label", event["stage"])


def event_title(event):
    year = str(event["year"])
    if not re.fullmatch(r"\d{4}", year):
        raise ValueError("A four-digit conference year is required")
    qualifiers = [display_stage(event)]
    if event["round_label"]:
        qualifiers.append(f"round {event['round_index']}")
    return f"{event['conference']}'{year[-2:]} ({', '.join(qualifiers)})"


def choose_digest_events(events, maximum):
    """Preserve all events that fit; on overflow retain both eligible CCF tiers."""
    if len(events) <= maximum:
        return list(events)
    selected = list(events[:maximum])
    eligible_ranks = {e.get("rank_ccf") for e in events} & {"A", "B"}
    if len(eligible_ranks) > maximum:
        raise ValueError("Capacity cannot represent both eligible CCF tiers; do not silently drop a tier")
    for rank in ("A", "B"):
        if rank not in eligible_ranks or any(e.get("rank_ccf") == rank for e in selected):
            continue
        replacement = next(e for e in events if e.get("rank_ccf") == rank)
        for i in range(len(selected) - 1, -1, -1):
            old_rank = selected[i].get("rank_ccf")
            if old_rank not in ("A", "B") or sum(e.get("rank_ccf") == old_rank for e in selected) > 1:
                selected[i] = replacement
                break
    positions = {id(e): i for i, e in enumerate(events)}
    selected.sort(key=lambda e: positions[id(e)])
    return selected


def tweet(category, events, now, maximum):
    # Keep the latest user-specified category header and ordinary plain text.
    if category not in ("AI", "Data Systems"):
        raise ValueError("Invalid publication category")
    publication_date = now.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y/%m/%d")
    header = f"CCFDDL daily reminders ({category}) · {publication_date}"
    lines = []
    selected = []
    for e in choose_digest_events(events, maximum):
        remaining = countdown(e["seconds_left"])
        if e["seconds_left"] > 86400:
            remaining = remaining.removesuffix(" left")
        line = f"{event_title(e)} · {remaining}"
        selected.append(e)
        lines.append(line)
    if not selected:
        return None, []
    text = "\n\n".join([header, "\n".join(lines), "see details: " + detail_url(selected[0]) + "\n" + HASHTAGS])
    return text, selected


def card_event_title(event):
    title = f"{event['conference']} {event['year']}"
    if event["round_label"]:
        title += " " + event["round_label"]
    title += " Abstract Deadline" if display_stage(event) == "abstract" else " Deadline"
    return title


def render_card(category, events, now, commit, output, preview=False, card_limit=3, total_event_count=None):
    """Adapt the repository email reminder layout for a legible social image."""
    from PIL import Image, ImageDraw, ImageFont
    if not 1 <= card_limit <= 3:
        raise ValueError("Use 1–3 visible rows per card")
    total = len(events) if total_event_count is None else total_event_count
    events = events[:card_limit]
    n = len(events)
    if not 1 <= n <= 3:
        raise ValueError("Render 1–3 visible events per image")
    has_more = total > n
    W, H = 1600, 960 - (3 - n) * 154 + (52 if has_more else 0)
    image = Image.new("RGB", (W, H), "#f2f2f2")
    draw = ImageDraw.Draw(image)
    regular = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    bold = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    def font(n, weight=False):
        try:
            return ImageFont.truetype(bold if weight else regular, n)
        except OSError as exc:
            raise RuntimeError("Install Liberation Sans (Arial-compatible) or update the explicit font paths; never silently use an unreadable fallback") from exc
    def fit(text, maximum, size=31, minimum=18, weight=False):
        for n in range(size, minimum - 1, -1):
            f = font(n, weight)
            if draw.textlength(text, font=f) <= maximum:
                return f
        raise ValueError(f"Card text cannot fit: {text}")
    accent = "#d44f3f"
    draw.text((80, 51), "ccf-deadlines", font=font(47, True), fill=accent)
    masthead = "REMINDER"
    draw.text((1520 - draw.textlength(masthead, font=font(23)), 67), masthead, font=font(23), fill="#a0a5aa")
    draw.rounded_rectangle((74, 136, 1526, H - 72), radius=12, fill="#ffffff", outline="#dedede", width=2)
    draw.rectangle((86, 136, 1514, 143), fill=accent)
    draw.text((118, 181), "DEADLINE NOTICE", font=font(24, True), fill=accent)
    heading = f"CCFDDL deadline reminders ({category})"
    draw.text((118, 225), heading, font=fit(heading, 1362, 47, weight=True), fill="#16191f")
    top, gap, card_h = 307, 18, 136
    for i, event in enumerate(events):
        y = top + i * (card_h + gap)
        draw.rounded_rectangle((116, y, 1484, y + card_h), radius=14, fill="#ffffff", outline="#e7e2dd", width=2)
        lead = countdown(event["seconds_left"]).upper()
        draw.text((146, y + 15), lead, font=font(24, True), fill=accent)
        title = card_event_title(event)
        draw.text((146, y + 49), title, font=fit(title, 1305, 31, weight=True), fill="#242933")
        when, zone = deadline_display(event, seconds=True)
        exact = f"{when} · {zone}"
        draw.text((146, y + 94), exact, font=fit(exact, 1305, 25), fill="#5f6975")
    if has_more:
        dots = "…"
        x = (W - draw.textlength(dots, font=font(50, True))) / 2
        last_bottom = top + (n - 1) * (card_h + gap) + card_h
        draw.text((x, last_bottom + 7), dots, font=font(50, True), fill="#5f6975")
    draw.text((119, H - 167), "Good luck with your submissions!", font=font(28), fill="#424a54")
    draw.text((119, H - 128), "The CCFDDL maintainer team", font=font(24), fill="#424a54")
    # Requested clean card: no in-image website CTA, UTC as-of, or source SHA.
    # Keep full provenance in the private manifest. The tweet retains the link.
    if preview:
        label = "DRAFT PREVIEW"
        draw.text((1522 - draw.textlength(label, font=font(16, True)), H - 63), label, font=font(16, True), fill=accent)
    image = image.crop((0, 0, W, H - 42))
    image.save(output)


def digest_limit(config, category):
    """Text limits are independent of optional card row limits."""
    allowed = {"AI": 6, "Data Systems": 6}
    if category not in allowed:
        raise ValueError("Invalid publication category")
    configured = config.get("max_items_by_category", {})
    if not isinstance(configured, dict) or set(configured) - set(allowed):
        raise ValueError("Text limits must name only AI and Data Systems")
    limit = configured.get(category, allowed[category])
    if type(limit) is not int or not 1 <= limit <= allowed[category]:
        raise ValueError(f"{category} text limit must be 1–{allowed[category]}")
    return limit


def build(snapshot_path, config_path, now, output, preview):
    config = json.loads(Path(config_path).read_text())
    if config.get("language", "en") != "en":
        raise ValueError("The deterministic renderer supports English; adapt and validate before using another language")
    limits = {category: digest_limit(config, category) for category in ("AI", "Data Systems")}
    media_mode = config.get("media_mode", "link_preview")
    if media_mode not in ("link_preview", "generated_card"):
        raise ValueError("media_mode must be link_preview or generated_card")
    source, rows = load_snapshot(snapshot_path)
    if not preview and (not source.get("complete_catalog") or not config.get("editorial_confirmed")):
        raise ValueError("Publication builds require the complete catalog and confirmed editorial settings")
    fetched = as_utc(source["fetched_at_utc"])
    if not preview and (now - fetched > timedelta(minutes=15) or fetched - now > timedelta(minutes=1)):
        raise ValueError("Source snapshot is stale or from the future; refresh immediately before publishing")
    categories, issues = select(rows, config, now)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    result = {"account": "ccfddl", "as_of_utc": iso(now), "preview_only": bool(preview), "source_commit": source["commit"],
              "source_repository": source["repository"], "source_fetched_at_utc": source["fetched_at_utc"],
              "configuration_confirmed": bool(config.get("editorial_confirmed", False)), "skipped_for_review": issues, "digests": []}
    for category, events in categories.items():
        text, chosen = tweet(category, events, now, limits[category])
        if not text:
            continue
        stem = "ai" if category == "AI" else "data-systems"
        (out / (stem + ".txt")).write_text(text + "\n")
        png = None
        card_events = []
        card_has_more = False
        alt = ""
        if media_mode == "generated_card":
            png = out / (stem + ".png")
            card_limit = int(config.get("card_limit", 3))
            card_events = chosen[:card_limit]
            card_has_more = len(events) > len(card_events)
            render_card(category, chosen, now, source["commit"], png, preview, card_limit, len(events))
            alt = f"CCFDDL deadline reminders ({category}). " + "; ".join(
                f"{e['conference']} {e['year']} {e['round_label']} {e['stage']}: {countdown(e['seconds_left'])}; deadline {e['deadline_source']} {e['timezone_source']}" for e in card_events) + (". More deadlines are indicated by an ellipsis; see post text and ccfddl.com." if card_has_more else ". Full dates at ccfddl.com.")
        weight = weighted_length(text)
        result["digests"].append({"category": category, "text": text, "weighted_length_upper_bound": weight,
                                  "long_text_advisory": weight > 280, "needs_publication_capability_validation": weight > 280,
                                  "media_mode": media_mode, "link_url": detail_url(chosen[0]),
                                  "card_target_url": detail_url(chosen[0]),
                                  "visible_detail_url": detail_url(chosen[0]),
                                  "preview_selection_guaranteed": False,
                                  "requires_live_url_verification": True, "link_preview_guaranteed": False,
                                  "image": str(png.resolve()) if png else None, "alt_text": alt,
                                  "events": chosen, "card_events": card_events, "card_has_more": card_has_more,
                                  "content_sha256": sha(text + (hashlib.sha256(png.read_bytes()).hexdigest() if png else "")),
                                  "candidate_event_count": len(events), "omitted_event_count": len(events) - len(chosen),
                                  "max_text_events": limits[category],
                                  "selection_policy": "all_if_fit_else_nearest_with_A_B_representation"})
    (out / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def ledger(path, operation, day, category, content_hash=None, post_url=None, post_id=None):
    if category not in ("AI", "Data Systems"):
        raise ValueError("Invalid category")
    datetime.strptime(day, "%Y-%m-%d")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = f"ccfddl:{day}:{category}"
    with open(str(path) + ".lock", "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(path.read_text()) if path.exists() else {}
        if operation == "check":
            return data.get(key)
        if operation == "reserve":
            if key in data:
                raise ValueError("Already reserved/published. Do not retry uncertain sends; inspect provider records")
            if not content_hash or not re.fullmatch(r"[0-9a-f]{64}", content_hash):
                raise ValueError("Require the exact content SHA256")
            data[key] = {"state": "pending", "content_sha256": content_hash, "reserved_at_utc": iso(datetime.now(UTC))}
        elif operation == "confirm":
            if key not in data or data[key]["state"] != "pending":
                raise ValueError("A pending reservation is required")
            if not post_id or not str(post_id).isdigit() or post_url != f"https://x.com/ccfddl/status/{post_id}":
                raise ValueError("Require verified @ccfddl post ID and exact canonical post URL")
            data[key].update({"state": "published", "post_id": post_id, "post_url": post_url, "confirmed_at_utc": iso(datetime.now(UTC))})
        else:
            raise ValueError("Unsupported ledger operation")
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".ledger-")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return data[key]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--repo", required=True)
    s.add_argument("--output", required=True)
    b = sub.add_parser("build")
    b.add_argument("--snapshot", required=True)
    b.add_argument("--config", required=True)
    b.add_argument("--as-of", required=True)
    b.add_argument("--output", required=True)
    b.add_argument("--preview", action="store_true")
    l = sub.add_parser("ledger")
    l.add_argument("operation", choices=["check", "reserve", "confirm"])
    l.add_argument("--path", required=True)
    l.add_argument("--day", required=True, help="Date in the user-confirmed publication timezone")
    l.add_argument("--category", required=True, choices=["AI", "Data Systems"])
    l.add_argument("--content-sha256")
    l.add_argument("--post-id")
    l.add_argument("--post-url")
    args = p.parse_args()
    if args.command == "snapshot":
        snapshot_from_git(args.repo, args.output)
    elif args.command == "build":
        result = build(args.snapshot, args.config, as_utc(args.as_of), args.output, args.preview)
        print(json.dumps({"digests": len(result["digests"]), "review_warnings": len(result["skipped_for_review"]), "manifest": str(Path(args.output) / "manifest.json")}))
    else:
        print(json.dumps(ledger(args.path, args.operation, args.day, args.category, args.content_sha256, args.post_url, args.post_id)))


if __name__ == "__main__":
    main()
