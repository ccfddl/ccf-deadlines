#!/usr/bin/env python3

import json
import hashlib
from datetime import date, timedelta
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "public" / "conference"
MERGE_SCRIPT = ROOT / "scripts" / "merge.py"


def merge(source: Path, output: Path, exclude: str | None = None) -> None:
    command = [sys.executable, str(MERGE_SCRIPT), str(source), "--include-conference-key"]
    if exclude is not None:
        command.extend(["--exclude", exclude])
    temporary = output.with_name(f".{output.name}.tmp")
    with temporary.open("w", encoding="utf-8") as output_file:
        subprocess.run(command, cwd=ROOT, stdout=output_file, check=True)
    temporary.replace(output)


def write_json_atomic(path: Path, data: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)


def split_conferences(conferences: list, today: date) -> tuple[list, list]:
    """Keep the latest and upcoming editions, plus sources needed for estimates."""
    initial, archive = [], []
    for conference in conferences:
        editions = conference["confs"]
        years = sorted({edition["year"] for edition in editions}, reverse=True)
        retained_years = set(years[:1])
        for edition in editions:
            if (edition["year"] >= today.year and any(
                point.get("deadline") == "TBD" for point in edition["timeline"]
            )) or any(
                str(point.get(field, ""))[:10] >= (today - timedelta(days=1)).isoformat()
                and str(point.get(field, ""))[:4].isdigit()
                for point in edition["timeline"]
                for field in ("abstract_deadline", "deadline", "rebuttal_deadline", "decision_deadline")
            ):
                retained_years.add(edition["year"])
        # Estimates need the previous announced edition, even across a year gap.
        for edition in editions:
            year = edition["year"]
            if year not in retained_years or year < today.year or not any(
                point.get("deadline") == "TBD" for point in edition["timeline"]
            ):
                continue
            previous = max((candidate for candidate in years if candidate < year), default=None)
            if previous is not None:
                retained_years.add(previous)
        for target, keep in ((initial, True), (archive, False)):
            selected = [edition for edition in editions if (edition["year"] in retained_years) == keep]
            if selected:
                target.append({**conference, "confs": selected})
    return initial, archive


def acceptance_bucket(title: str) -> int:
    # Same UTF-8 FNV-1a calculation as the Rust loader.
    value = 2166136261
    for byte in title.encode("utf-8"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value % 16


def resolve_acceptance_keys(conferences: list, acceptances: list) -> list:
    """Join source identities, preserving unambiguous historical path aliases.

    Titles alone are not identities: SEC and FSE each name two conferences.
    Prefer the exact category/slug; a relocated legacy acceptance file (such as
    DB/eusipco) may use its title only if there is exactly one catalog match.
    """
    by_key, by_title = {}, {}
    for conference in conferences:
        key = conference["conference_key"]
        if key in by_key:
            raise ValueError(f"Duplicate conference identity: {key}")
        by_key[key] = conference
        by_title.setdefault(conference["title"], []).append(conference)

    resolved, seen = [], set()
    for acceptance in acceptances:
        key = acceptance["conference_key"]
        conference = by_key.get(key)
        if conference is None:
            candidates = by_title.get(acceptance["title"], [])
            if len(candidates) != 1:
                raise ValueError(f"Unknown or ambiguous acceptance identity: {key}")
            conference = candidates[0]
        key = conference["conference_key"]
        if key in seen:
            raise ValueError(f"Duplicate acceptance identity: {key}")
        seen.add(key)
        # Use the catalog title for bucket selection even after a historical rename.
        resolved.append({**acceptance, "conference_key": key, "title": conference["title"]})
    return resolved


def write_loading_data(conferences: list, acceptances: list, output_dir: Path) -> None:
    initial, archive = split_conferences(conferences, date.today())
    encoded = json.dumps(archive, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    archive_name = f"history-{hashlib.sha256(encoded).hexdigest()[:16]}.json"
    parts_dir = output_dir / "parts"
    parts_dir.mkdir(exist_ok=True)
    write_json_atomic(parts_dir / archive_name, archive)
    write_json_atomic(output_dir / "initial.json", {
        "conferences": initial,
        "archive": f"parts/{archive_name}",
    })
    buckets = [[] for _ in range(16)]
    for acceptance in acceptances:
        buckets[acceptance_bucket(acceptance["title"])].append(acceptance)
    for index, bucket in enumerate(buckets):
        write_json_atomic(parts_dir / f"acceptance-{index:02}.json", bucket)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    merge(ROOT / "conference", OUTPUT_DIR / "allconf.yml", exclude="types.yml")
    merge(ROOT / "accept_rates", OUTPUT_DIR / "allacc.yml")
    conferences = yaml.safe_load((OUTPUT_DIR / "allconf.yml").read_text(encoding="utf-8"))
    acceptances = yaml.safe_load((OUTPUT_DIR / "allacc.yml").read_text(encoding="utf-8"))
    acceptances = resolve_acceptance_keys(conferences, acceptances)
    (OUTPUT_DIR / "allacc.yml").write_text(
        yaml.safe_dump(acceptances, allow_unicode=True, sort_keys=False), encoding="utf-8",
    )
    write_json_atomic(OUTPUT_DIR / "allconf.json", conferences)
    write_json_atomic(OUTPUT_DIR / "allacc.json", acceptances)
    write_loading_data(conferences, acceptances, OUTPUT_DIR)
    (OUTPUT_DIR / "allconf_archive.json").unlink(missing_ok=True)
    shutil.copy2(ROOT / "conference" / "types.yml", OUTPUT_DIR / "types.yml")


if __name__ == "__main__":
    main()
