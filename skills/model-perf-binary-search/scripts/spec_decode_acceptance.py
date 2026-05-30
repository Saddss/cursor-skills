#!/usr/bin/env python3
"""Compute MTP/spec-decode draft acceptance rate from Prometheus snapshot diffs."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_NAME_RE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)")
_ACCEPT_PAT = re.compile(r"spec_decode.*accepted.*token", re.IGNORECASE)
_DRAFT_TOKEN_PAT = re.compile(r"spec_decode.*draft.*token", re.IGNORECASE)


def fetch_metrics(url: str, timeout: float = 10.0) -> str:
    req = urllib.request.Request(url, headers={"Accept": "text/plain"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_snapshot(text: str) -> dict[str, float]:
    totals: dict[str, float] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _NAME_RE.match(line)
        if not m:
            continue
        name, val = m.group(1), float(m.group(3))
        totals[name] = totals.get(name, 0.0) + val
    return totals


def pick_metric(totals: dict[str, float], pattern: re.Pattern[str]) -> tuple[str, float] | None:
    candidates = [(n, v) for n, v in totals.items() if pattern.search(n)]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1])


def cmd_snapshot(args: argparse.Namespace) -> int:
    text = fetch_metrics(args.url, args.timeout)
    header = (
        f"# snapshot {datetime.now(timezone.utc).isoformat()} "
        f"url={args.url}\n"
    )
    Path(args.out).write_text(header + text)
    print(json.dumps({"status": "OK", "out": args.out}))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    before = parse_snapshot(Path(args.before).read_text())
    after = parse_snapshot(Path(args.after).read_text())
    all_names = set(before) | set(after)
    accepted = pick_metric({n: after.get(n, 0) - before.get(n, 0) for n in all_names}, _ACCEPT_PAT)
    drafted = pick_metric({n: after.get(n, 0) - before.get(n, 0) for n in all_names}, _DRAFT_TOKEN_PAT)
    if not accepted or not drafted or drafted[1] <= 0:
        out = {
            "status": "NO_SPEC_METRICS",
            "acceptance_rate": None,
            "accepted_tokens": accepted[1] if accepted else None,
            "draft_tokens": drafted[1] if drafted else None,
            "accepted_metric": accepted[0] if accepted else None,
            "draft_metric": drafted[0] if drafted else None,
            "spec_metrics_seen": sorted(n for n in all_names if "spec_decode" in n.lower()),
        }
        print(json.dumps(out))
        return 2
    rate = accepted[1] / drafted[1]
    out = {
        "status": "OK",
        "acceptance_rate": rate,
        "accepted_tokens": accepted[1],
        "draft_tokens": drafted[1],
        "accepted_metric": accepted[0],
        "draft_metric": drafted[0],
    }
    print(json.dumps(out))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--url", default="http://localhost:8000/metrics")
    s.add_argument("--out", required=True)
    s.add_argument("--timeout", type=float, default=10.0)
    s.set_defaults(func=cmd_snapshot)
    d = sub.add_parser("diff")
    d.add_argument("--before", required=True)
    d.add_argument("--after", required=True)
    d.set_defaults(func=cmd_diff)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
