#!/usr/bin/env python3
"""Keep recently published browser assets available to cached HTML and modules."""

import argparse
import json
import shutil
import time
from pathlib import Path


MANIFEST = '.asset-retention.json'


def browser_assets(directory: Path):
    for path in directory.rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(directory)
        if path.suffix not in {'.js', '.css', '.wasm'}:
            continue
        if len(relative.parts) == 1 or relative.parts[0] == 'snippets':
            yield relative
        elif relative.parts[0] == 'venues' and len(relative.parts) == 2:
            yield relative


def retain_assets(output: Path, previous: Path, *, now=None, retention_hours=24):
    if retention_hours <= 0:
        raise ValueError('Asset retention must be positive')
    if not previous.is_dir():
        raise ValueError('Published site checkout is missing')
    now = time.time() if now is None else now
    manifest = previous / MANIFEST
    timestamps = json.loads(manifest.read_text()) if manifest.exists() else {}
    active = {str(path): now for path in browser_assets(output)}
    retained = 0
    for relative in browser_assets(previous):
        key = str(relative)
        if key in active:
            continue
        last_seen = timestamps.get(key, now)
        if now - last_seen > retention_hours * 3600:
            continue
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(previous / relative, target)
        active[key] = last_seen
        retained += 1
    (output / MANIFEST).write_text(json.dumps(active, sort_keys=True, indent=2) + '\n')
    return retained


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--retention-hours', type=float, default=24)
    args = parser.parse_args()
    count = retain_assets(args.output, args.previous, retention_hours=args.retention_hours)
    print(f'Retained {count} previously published browser assets')
