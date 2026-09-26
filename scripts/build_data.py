#!/usr/bin/env python3

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "public" / "conference"
MERGE_SCRIPT = ROOT / "scripts" / "merge.py"


def merge(source: Path, output: Path, exclude: str | None = None) -> None:
    command = [sys.executable, str(MERGE_SCRIPT), str(source)]
    if exclude is not None:
        command.extend(["--exclude", exclude])
    with output.open("w", encoding="utf-8") as output_file:
        subprocess.run(command, cwd=ROOT, stdout=output_file, check=True)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    merge(ROOT / "conference", OUTPUT_DIR / "allconf.yml", exclude="types.yml")
    merge(ROOT / "accept_rates", OUTPUT_DIR / "allacc.yml")
    conferences = yaml.safe_load((OUTPUT_DIR / "allconf.yml").read_text(encoding="utf-8"))
    acceptances = yaml.safe_load((OUTPUT_DIR / "allacc.yml").read_text(encoding="utf-8"))
    acceptance_rates = {}
    for conference in acceptances:
        for rate in conference["accept_rates"]:
            label = rate.get("str") or rate.get("srt")
            if not label:
                continue
            for year_offset in range(1, 4):
                acceptance_rates[(conference["title"], rate["year"] + year_offset)] = label
    for conference in conferences:
        for edition in conference["confs"]:
            acc_str = acceptance_rates.get((conference["title"], edition["year"]))
            if acc_str is not None:
                edition["acc_str"] = acc_str
    current_year = datetime.now(timezone.utc).year
    current_conferences = []
    archived_conferences = []
    for conference in conferences:
        current_editions = [
            edition for edition in conference["confs"] if edition["year"] >= current_year
        ]
        archived_editions = [
            edition for edition in conference["confs"] if edition["year"] < current_year
        ]
        if current_editions:
            current_conferences.append({**conference, "confs": current_editions})
        if archived_editions:
            archived_conferences.append({**conference, "confs": archived_editions})

    json_options = {"ensure_ascii": False, "separators": (",", ":")}
    (OUTPUT_DIR / "allconf.json").write_text(
        json.dumps(current_conferences, **json_options), encoding="utf-8"
    )
    (OUTPUT_DIR / "allconf_archive.json").write_text(
        json.dumps(archived_conferences, **json_options), encoding="utf-8"
    )
    (OUTPUT_DIR / "allacc.json").unlink(missing_ok=True)
    shutil.copy2(ROOT / "conference" / "types.yml", OUTPUT_DIR / "types.yml")


if __name__ == "__main__":
    main()
