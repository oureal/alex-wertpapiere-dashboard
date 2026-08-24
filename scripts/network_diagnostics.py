#!/usr/bin/env python3
"""Non-failing, structured reachability checks for intended free sources."""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

SOURCES = (
    ("yahoo_finance", "https://query1.finance.yahoo.com/"),
    ("alphavantage", "https://www.alphavantage.co/"),
    ("boerse_frankfurt", "https://www.boerse-frankfurt.de/"),
    ("ishares", "https://www.ishares.com/"),
    ("boerse_de", "https://www.boerse.de/"),
    ("monega", "https://www.monega.de/"),
    ("wisdomtree", "https://www.wisdomtree.eu/"),
)


def diagnose(opener: Callable = urllib.request.urlopen, timeout: float = 15) -> dict:
    results = []
    for name, url in SOURCES:
        started = time.monotonic()
        try:
            request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "private-portfolio-market-data-test/1.0"})
            with opener(request, timeout=timeout) as response:
                status = getattr(response, "status", None) or response.getcode()
            results.append({"source": name, "url": url, "reachable": 200 <= status < 500, "http_status": status, "error": None, "elapsed_ms": round((time.monotonic() - started) * 1000)})
        except urllib.error.HTTPError as error:
            results.append({"source": name, "url": url, "reachable": True, "http_status": error.code, "error": str(error), "elapsed_ms": round((time.monotonic() - started) * 1000)})
        except Exception as error:
            results.append({"source": name, "url": url, "reachable": False, "http_status": None, "error": f"{type(error).__name__}: {error}", "elapsed_ms": round((time.monotonic() - started) * 1000)})
    return {"schema_version": 1, "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "diagnostic_only": True, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()
    report = diagnose(timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for row in report["results"]:
        print(f"{row['source']}: reachable={row['reachable']} http_status={row['http_status']} error={row['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
