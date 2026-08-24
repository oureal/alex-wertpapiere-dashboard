#!/usr/bin/env python3
"""Reproducibly extract the literal const DATA object from index.html."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "index.html"
DEFAULT_OUTPUT = ROOT / "data/legacy/index-data-2026-08-21.json"
DATA_PATTERN = re.compile(rb"(?:^|\n)const DATA=(\{.*?\});\r?\nconst eur=", re.DOTALL)


def extract(source: bytes) -> bytes:
    match = DATA_PATTERN.search(source)
    if not match:
        raise ValueError("Could not find a unique const DATA object")
    payload = match.group(1)
    json.loads(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = extract(args.input.read_bytes())
    if args.check:
        if not args.output.exists() or args.output.read_bytes() != payload:
            print(f"ERROR: {args.output} is not the exact extracted DATA payload")
            return 1
        print(f"Legacy DATA reference matches {args.input} ({len(payload)} bytes).")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(f"Extracted {len(payload)} bytes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
