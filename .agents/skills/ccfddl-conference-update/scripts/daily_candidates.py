#!/usr/bin/env python3
"""Local-only conference triage; historical estimates are never repository facts."""

import argparse
import calendar
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
import re
import statistics

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required; use the repository's Python environment.")


FIELDS = ("abstract_deadline", "deadline", "rebuttal_deadline", "decision_deadline")
OUTCOMES = ("unchanged", "tbd", "not-announced", "changed", "covered-pr", "source-error", "conflict")
MONTHS = {name.lower(): index for index in range(1, 13)
          for name in (calendar.month_name[index], calendar.month_abbr[index])}


def iso_day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def milestones(edition, fields=FIELDS):
    return sorted(day for row in edition.get("timeline", []) for field in fields
                  if (day := iso_day(row.get(field))))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def event_month_end(edition):
    """Conservative gating only: retain an edition through its opening month."""
    raw = str(edition.get("date", ""))
    iso = re.match(r"^(\d{4})-(\d{2})-\d{2}", raw)
    if iso:
        year, month = map(int, iso.groups())
    else:
        match = re.match(r"^(?:\d{1,2}(?:\s*[-–]\s*\d{1,2})?\s+)?([A-Za-z]+)", raw)
        month = MONTHS.get(match[1].lower()) if match else None
        years = re.findall(r"\b(\d{4})\b", raw)
        year = int(years[-1]) if years else edition["year"]
    if not month or not 1 <= month <= 12:
        return None
    return date(year, month, calendar.monthrange(year, month)[1])


def next_window(editions, lead_days):
    years = sorted({edition["year"] for edition in editions})
    gaps = [b - a for a, b in zip(years, years[1:])][-3:]
    # Unknown or irregular cadence stays eligible for human inspection.
    if not gaps or len(set(gaps)) != 1:
        return None
    target = years[-1] + gaps[-1]
    estimates = []
    for edition in sorted(editions, key=lambda e: e["year"])[-3:]:
        days = milestones(edition, FIELDS[:2])
        if days:
            first = days[0]
            try:
                estimates.append(first.replace(year=first.year + target - edition["year"]).toordinal())
            except ValueError:  # Leap day is a gating hint, not a promised date.
                estimates.append(first.replace(year=first.year + target - edition["year"], day=28).toordinal())
    return date.fromordinal(int(statistics.median(estimates))) - timedelta(days=lead_days) if estimates else None


def candidates(repo, today, lead_days, filters):
    rows, matched = [], set()
    for path in sorted((repo / "conference").glob("*/*.yml")):
        with path.open() as stream:
            conferences = yaml.safe_load(stream)
        for conference in conferences:
            title = conference["title"]
            hits = {item for item in filters if item.casefold() in (title.casefold(), path.stem.casefold())}
            if filters and not hits:
                continue
            matched.update(hits)
            editions = conference.get("confs", [])
            if not editions:
                continue
            latest = max(editions, key=lambda e: e["year"])
            prefix = f"{path.relative_to(repo)}::{title}::"
            for edition in editions:
                days = milestones(edition)
                event_end = event_month_end(edition)
                active = any(day >= today - timedelta(days=14) for day in days)
                active |= bool(event_end and event_end >= today - timedelta(days=14))
                active |= event_end is None and edition["year"] >= today.year - 1
                if not active:
                    continue
                unknown = any(str(value).strip().upper() in ("TBD", "TBA")
                              for row in edition.get("timeline", []) for field, value in row.items()
                              if field in FIELDS)
                imminent = any(today - timedelta(days=2) <= day <= today + timedelta(days=14) for day in days)
                row = {"key": prefix + edition["id"], "conference": title, "scope": "edition",
                       "year": edition["year"], "file": str(path.relative_to(repo)),
                       "url": edition.get("link"), "rounds": len(edition.get("timeline", [])),
                       "reason": "near milestone" if imminent else "TBD / active edition" if unknown else "active edition",
                       "_fingerprint": fingerprint(edition), "_priority": 0 if imminent else 1 if unknown else 2,
                       "_imminent": imminent, "_gate": None}
                rows.append(row)
            gate = next_window(editions, lead_days)
            rows.append({"key": prefix + "next-after:" + latest["id"], "conference": title,
                         "scope": "next-edition", "after_year": latest["year"],
                         "file": str(path.relative_to(repo)), "url": latest.get("link"),
                         "reason": "historical checking window" if gate else "unknown cadence/window",
                         "_fingerprint": fingerprint(editions), "_priority": 3,
                         "_imminent": False, "_gate": gate})
    return rows, sorted(set(filters) - matched)


def load_state(path):
    if not path.exists():
        return {"version": 1, "checks": {}}
    with path.open() as stream:
        state = json.load(stream)
    if state.get("version") != 1 or not isinstance(state.get("checks"), dict):
        raise ValueError("Unsupported ledger format; preserve the old file and use another --state path.")
    return state


def cached_until(row, old, today):
    if old.get("fingerprint") != row["_fingerprint"]:
        return None
    next_check = iso_day(old.get("next_check"))
    source_dates = [day for source in old.get("sources", []) if (day := iso_day(source.get("next_check")))]
    if next_check and source_dates:
        next_check = min(next_check, *source_dates)
    if not next_check or next_check <= today:
        return None
    # Quiet-period backoff never suppresses checks beyond a day near a milestone.
    if row["_imminent"] and iso_day(old.get("last_checked")) != today:
        return None
    return next_check


def scan(args, rows, unmatched, state):
    due, early, cached = [], 0, 0
    for row in rows:
        old = state["checks"].get(row["key"], {})
        changed = bool(old and old.get("fingerprint") != row["_fingerprint"])
        if not args.force:
            if not changed and row["_gate"] and row["_gate"] > args.today:
                early += 1
                continue
            if cached_until(row, old, args.today):
                cached += 1
                continue
        row["last_checked"] = old.get("last_checked")
        row["local_changed"] = changed
        # Keep the shortlist small; complete per-source/round history stays local.
        row["source_count"] = len(old.get("sources", []))
        row["sources"] = old.get("sources", [])[-3:]
        due.append(row)
    due.sort(key=lambda row: (not row["local_changed"], row["_priority"], row["last_checked"] or "", row["key"]))
    if args.limit and len(due) > args.limit:
        # Reserve half the batch for old/unvisited work so daily urgent checks
        # cannot indefinitely crowd out the remainder.
        priority = due[:(args.limit + 1) // 2]
        selected = {row["key"] for row in priority}
        oldest = sorted((row for row in due if row["key"] not in selected),
                        key=lambda row: (row["last_checked"] or "", row["key"]))
        shown = priority + oldest[:args.limit - len(priority)]
    else:
        shown = due
    print(json.dumps({"today": str(args.today), "due": len(due), "shown": len(shown),
                      "remaining": len(due) - len(shown), "cached": cached, "too_early": early,
                      "untracked_leads": unmatched}))
    for row in shown:
        print(json.dumps({key: value for key, value in row.items() if not key.startswith("_")}, ensure_ascii=False))


def record(args, rows, state, path):
    row = next((row for row in rows if row["key"] == args.key), None)
    if row is None:
        raise ValueError("Key not found among active/next candidates; rescan the current checkout.")
    old = state["checks"].get(args.key, {})
    old_sources = old.get("sources", []) if old.get("fingerprint") == row["_fingerprint"] else []
    prior_source = next((source for source in old_sources
                         if (source["url"], source["round"]) == (args.source, args.round)), {})
    repeated = (prior_source.get("outcome") == args.outcome and old.get("fingerprint") == row["_fingerprint"])
    # Multiple source/round records on one day are one check, not more backoff.
    count = 1
    if repeated:
        count = prior_source.get("count", 1) + (prior_source.get("last_checked") != str(args.today))
    interval = {"tbd": 3, "unchanged": 7 if count == 1 else 14,
                "not-announced": 7 if count == 1 else 14, "changed": 1,
                "covered-pr": 7, "source-error": min(2 ** min(count - 1, 3), 7), "conflict": 1}[args.outcome]
    if row["_imminent"]:
        interval = 1
    next_check = args.next_check or args.today + timedelta(days=interval)
    source = {"url": args.source, "round": args.round, "revision": args.revision,
              "last_checked": str(args.today), "next_check": str(next_check), "outcome": args.outcome, "count": count}
    sources = [entry for entry in old_sources
               if not (entry["url"] == args.source and (entry["round"] == args.round or args.round == "all"))] + [source]
    source_dates = [day for entry in sources if (day := iso_day(entry.get("next_check")))]
    candidate_next = args.today if args.partial else min(source_dates)
    state["checks"][args.key] = {"fingerprint": row["_fingerprint"], "last_checked": str(args.today),
                                "next_check": str(candidate_next), "outcome": args.outcome, "sources": sources}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)
    print(json.dumps({"recorded": args.key, "outcome": args.outcome, "next_check": str(candidate_next), "state": str(path)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "record"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--repo", type=Path, default=Path.cwd())
        sub.add_argument("--state", type=Path, help="Local-only JSON ledger; default REPO/.cache/ccfddl-conference-update/state.json")
        sub.add_argument("--today", type=date.fromisoformat, required=True, help="Current date in the user's timezone")
        sub.add_argument("--lead-days", type=int, default=180, help="Fallback pre-submission search buffer; gating only")
        if name == "scan":
            sub.add_argument("--conference", action="append", default=[], help="Exact title or YAML filename stem; repeatable")
            sub.add_argument("--limit", type=int, default=12, help="Maximum due rows; 0 means all")
            sub.add_argument("--force", action="store_true", help="Bypass historical gates and cached results")
        else:
            sub.add_argument("--key", required=True)
            sub.add_argument("--outcome", choices=OUTCOMES, required=True)
            sub.add_argument("--source", required=True, help="Actual official URL checked or attempted")
            sub.add_argument("--round", required=True, help="Checked track/round; 'all' means all relevant rounds")
            sub.add_argument("--revision", help="Optional source ETag/Last-Modified/relevant-section digest")
            sub.add_argument("--next-check", type=date.fromisoformat)
            sub.add_argument("--partial", action="store_true", help="Only part of this candidate checked; leave it due")
    args = parser.parse_args()
    if args.lead_days < 0 or (args.command == "scan" and args.limit < 0):
        parser.error("--lead-days and --limit must be nonnegative")
    repo = args.repo.resolve()
    if not (repo / "conference").is_dir():
        parser.error("--repo must contain conference/")
    path = args.state or repo / ".cache/ccfddl-conference-update/state.json"
    try:
        rows, unmatched = candidates(repo, args.today, args.lead_days, getattr(args, "conference", []))
        state = load_state(path)
        if args.command == "scan":
            scan(args, rows, unmatched, state)
        else:
            record(args, rows, state, path)
    except (ValueError, OSError, yaml.YAMLError, KeyError, TypeError) as error:
        parser.exit(1, f"Unable to process repository/ledger: {error}\n")


if __name__ == "__main__":
    main()
