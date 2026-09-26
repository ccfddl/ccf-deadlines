#!/usr/bin/env python3

import json
import shutil
import subprocess
import sys
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


def write_json_atomic(path: Path, data: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    merge(ROOT / "conference", OUTPUT_DIR / "allconf.yml", exclude="types.yml")
    merge(ROOT / "accept_rates", OUTPUT_DIR / "allacc.yml")
    conferences = yaml.safe_load((OUTPUT_DIR / "allconf.yml").read_text(encoding="utf-8"))
    acceptances = yaml.safe_load((OUTPUT_DIR / "allacc.yml").read_text(encoding="utf-8"))
    write_json_atomic(OUTPUT_DIR / "allconf.json", conferences)
    write_json_atomic(OUTPUT_DIR / "allacc.json", acceptances)
    (OUTPUT_DIR / "allconf_archive.json").unlink(missing_ok=True)
    shutil.copy2(ROOT / "conference" / "types.yml", OUTPUT_DIR / "types.yml")


if __name__ == "__main__":
    main()
