#!/usr/bin/env python3

import shutil
import subprocess
import sys
from pathlib import Path

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
    shutil.copy2(ROOT / "conference" / "types.yml", OUTPUT_DIR / "types.yml")


if __name__ == "__main__":
    main()
