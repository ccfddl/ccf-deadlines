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
ZONE_ALIASES = {"AoE": "UTC-12", "PT": "America/Los_Angeles", "ET": "America/New_York"}
NON_SUBMISSION = re.compile(r"\b(rebuttal|notification|decision|camera[- ]ready|author response|revision[- ]only)\b", re.I)


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
        return f"{n}h" if short else f"{n} hours left"
    n = math.floor(seconds / 86400)
    return f"{n}d" if short else f"{n} days left"


def weighted_length(text):
    """Safe upper bound for generated text. Sole canonical URL uses t.co length 23.
    Emoji sequences may be overcounted; never undercounted. No arbitrary URLs.
    """
    text = unicodedata.normalize("NFC", text)
    count = text.count(LINK)
    rest = text.replace(LINK, "")
    if re.search(r"(?:https?://|www\.)", rest, re.I):
        raise ValueError("Only the canonical CCFDDL URL is allowed")
    return 23 * count + sum(1 if (ord(c) <= 0x10FF or 0x2000 <= ord(c) <= 0x200D or 0x2010 <= ord(c) <= 0x201F or 0x2032 <= ord(c) <= 0x2037) else 2 for c in rest)


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
    quarantine = config.get("quarantine_events", [])
    allowed = set(config.get("ccf_ranks", ["A"]))
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
            blocked = [q for q in quarantine if q.get("source_path") == path and q.get("id") == conf.get("id")]
            if blocked:
                issues.append({"source": path, "id": conf.get("id"), "reason": blocked[0]["reason"]})
                continue
            timelines = conf.get("timeline") or []
            for index, item in enumerate(timelines):
                comment = str(item.get("comment", ""))
                if NON_SUBMISSION.search(comment):
                    issues.append({"source": path, "id": conf.get("id"), "round": index + 1, "reason": "Review non-submission wording in timeline comment"})
                    continue
                candidates = []
                abstract = None
                try:
                    abstract = parse_deadline(item.get("abstract_deadline"), conf.get("timezone"))
                    for key, stage in (("abstract_deadline", "abstract"), ("deadline", "paper")):
                        deadline = parse_deadline(item.get(key), conf.get("timezone"))
                        if deadline and now < deadline <= now + horizon:
                            candidates.append((deadline, stage, item.get(key)))
                except (ValueError, KeyError) as e:
                    issues.append({"source": path, "id": conf.get("id"), "round": index + 1, "reason": str(e)})
                    continue
                if not candidates:
                    continue
                deadline, stage, original = min(candidates)
                identity = str(conf.get("id") or f"{title}-{conf.get('year')}")
                if len(timelines) > 1:
                    round_label = f"R{index + 1}"
                else:
                    round_label = ""
                event = {"conference": title, "year": conf.get("year"), "id": identity, "round_index": index + 1,
                         "round_label": round_label, "stage": stage, "deadline_utc": iso(deadline),
                         "deadline_source": str(original), "timezone_source": conf.get("timezone"),
                         "seconds_left": (deadline - now).total_seconds(), "abstract_closed": bool(stage == "paper" and abstract and abstract <= now),
                         "comment": comment, "source_path": path, "official_url": conf.get("link"), "rank_ccf": rank}
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


def tweet(category, events, now, maximum):
    date = now.strftime("%b %d")
    header = f"{category} deadlines | {date} UTC"
    lines = []
    selected = []
    for e in events[:maximum]:
        round_ = (" " + e["round_label"]) if e["round_label"] else ""
        note = "; abstract closed" if e["abstract_closed"] else ""
        line = f"{e['conference']} {e['year']}{round_}: {countdown(e['seconds_left'], True)} ({e['stage']}{note})"
        selected.append(e)
        lines.append(line)
    if not selected:
        return None, []
    text = "\n".join([header, *lines, "", "Dates + details: " + LINK])
    return text, selected


def render_card(category, events, now, commit, output, preview=False):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1600, 960
    image = Image.new("RGB", (W, H), "#faf9f7")
    draw = ImageDraw.Draw(image)
    regular = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
    def font(n, weight=False):
        try:
            return ImageFont.truetype(bold if weight else regular, n)
        except OSError as exc:
            raise RuntimeError("Install DejaVu Sans or update the explicit font paths; never silently use an unreadable fallback") from exc
    def fit(text, maximum, size=31, minimum=18, weight=False):
        for n in range(size, minimum - 1, -1):
            f = font(n, weight)
            if draw.textlength(text, font=f) <= maximum:
                return f
        raise ValueError(f"Card text cannot fit: {text}")
    accent = "#F66A0A"
    draw.rectangle((0, 0, W, 14), fill=accent)
    draw.text((74, 50), "CCFDDL", font=font(34, True), fill="#334155")
    draw.text((W - 370, 58), "DAILY COUNTDOWN", font=font(23, True), fill="#666666")
    draw.text((74, 113), category, font=font(64, True), fill="#2c3e50")
    draw.text((76, 196), "Upcoming submission deadlines", font=font(29), fill="#666666")
    n = len(events)
    top, gap, available = 259, 19, 507
    card_h = min(233, (available - gap * (n - 1)) // n)
    for i, event in enumerate(events):
        y = top + i * (card_h + gap)
        draw.rounded_rectangle((74, y, 1526, y + card_h), radius=23, fill="#fffefa", outline="#e6e0d8", width=2)
        draw.rounded_rectangle((75, y + 1, 87, y + card_h - 1), radius=5, fill=accent)
        title = f"{event['conference']} {event['year']}"
        if event["round_label"]:
            title += "  ·  " + event["round_label"]
        draw.text((112, y + 19), title, font=fit(title, 950, 35, weight=True), fill="#2c3e50")
        meta = event["stage"].capitalize() + " submission"
        if event["abstract_closed"]:
            meta += " · Abstract deadline passed"
        draw.text((113, y + 65), meta, font=fit(meta, 950, 25), fill="#475569")
        deadline = f"Due {event['deadline_source']} {event['timezone_source']}"
        draw.text((113, y + 105), deadline, font=fit(deadline, 990, 22), fill="#666666")
        urgency = "#f56c6c" if event["seconds_left"] < 3 * 86400 else "#e6a23c" if event["seconds_left"] < 7 * 86400 else "#67c23a"
        countdown_text = countdown(event["seconds_left"], True)
        cw = draw.textlength(countdown_text, font=font(53, True))
        draw.text((1474 - cw, y + 36), countdown_text, font=font(53, True), fill=urgency)
        draw.text((1380, y + 104), "LEFT", font=font(18, True), fill="#909399")
    draw.text((75, 807), "Explore deadlines → ccfddl.com", font=font(35, True), fill="#2c3e50")
    draw.text((77, 863), f"As of {iso(now)}  ·  Source {commit[:12]}", font=font(22), fill="#666666")
    if preview:
        draw.text((1208, 882), "DRAFT PREVIEW", font=font(21, True), fill="#9a3412")
    image.save(output)


def build(snapshot_path, config_path, now, output, preview):
    config = json.loads(Path(config_path).read_text())
    if config.get("language", "en") != "en":
        raise ValueError("The deterministic renderer supports English; adapt and validate before using another language")
    if not 1 <= int(config.get("max_items_per_category", 3)) <= 3:
        raise ValueError("Use 1–3 rows per card for readable mobile output")
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
        text, chosen = tweet(category, events, now, int(config.get("max_items_per_category", 3)))
        if not text:
            continue
        stem = "ai" if category == "AI" else "data-systems"
        (out / (stem + ".txt")).write_text(text + "\n")
        png = out / (stem + ".png")
        render_card(category, chosen, now, source["commit"], png, preview)
        alt = f"{category} conference submission countdowns as of {iso(now)}. " + "; ".join(
            f"{e['conference']} {e['year']} {e['round_label']} {e['stage']}: {countdown(e['seconds_left'])}; deadline {e['deadline_source']} {e['timezone_source']}" + ("; abstract deadline has passed" if e["abstract_closed"] else "") for e in chosen) + ". Full dates at ccfddl.com."
        result["digests"].append({"category": category, "text": text, "weighted_length_upper_bound": weighted_length(text), "long_text_advisory": weighted_length(text) > 280,
                                  "image": str(png.resolve()), "alt_text": alt, "events": chosen,
                                  "content_sha256": sha(text + hashlib.sha256(png.read_bytes()).hexdigest())})
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
