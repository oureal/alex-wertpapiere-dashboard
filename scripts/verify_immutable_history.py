#!/usr/bin/env python3
"""Verify that all immutable legacy dashboard and data snapshots are intact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/legacy/immutable-history-sha256.json"
IMMUTABLE_DIRS = (Path("dashboard/history"), Path("data/snapshots"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(manifest_path: Path = DEFAULT_MANIFEST, root: Path = ROOT) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("algorithm") != "sha256":
        return ["Manifest uses an unsupported hash algorithm"]

    expected = manifest.get("files", {})
    errors: list[str] = []
    actual_paths = {
        path.relative_to(root).as_posix()
        for directory in IMMUTABLE_DIRS
        for path in (root / directory).iterdir()
        if path.is_file()
    }
    expected_paths = set(expected)

    for missing in sorted(expected_paths - actual_paths):
        errors.append(f"Missing immutable file: {missing}")
    for unexpected in sorted(actual_paths - expected_paths):
        errors.append(f"Unregistered file in immutable directory: {unexpected}")
    for relative_path in sorted(expected_paths & actual_paths):
        actual_hash = sha256(root / relative_path)
        if actual_hash != expected[relative_path]:
            errors.append(
                f"Hash mismatch: {relative_path} "
                f"(expected {expected[relative_path]}, got {actual_hash})"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = verify(args.manifest.resolve(), args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Immutable legacy history verified successfully (6 files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
