#!/usr/bin/env python3
"""Analyze online_replay.py JSON output and decide if a QPS run met the SLO.

Reads a JSON-lines file produced by `online_replay.py --json-output`, where
each line is one round's metrics. Computes the average of the per-round
`Latency.p50` over the last N rounds and compares it against an SLO.

Exit codes:
  0 -> PASS (avg p50 e2e latency < SLO and we have enough rounds)
  1 -> FAIL (avg p50 >= SLO with enough rounds)
  2 -> NOT_ENOUGH_ROUNDS (json contains fewer rounds than required)
  3 -> usage / parse error

Stdout (always, single line of JSON) so the caller can parse a structured result:
  {"status": "PASS"|"FAIL"|"NOT_ENOUGH_ROUNDS",
   "rounds_seen": int, "rounds_required": int,
   "tail_window": int,
   "avg_p50_latency_s": float | null,
   "slo_s": float,
   "per_round_p50": [float, ...]}
"""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, nargs="+",
                        help="One or more JSON-lines files from --json-output. "
                             "When multiple are given (sharded clients), per-round "
                             "p50 is averaged across files for the same round index.")
    parser.add_argument("--total-rounds", type=int, required=True,
                        help="Total rounds expected (e.g. 12 or 24).")
    parser.add_argument("--tail-window", type=int, required=True,
                        help="Number of trailing rounds to average (e.g. 6 or 12).")
    parser.add_argument("--slo", type=float, default=6.5,
                        help="E2E p50 latency SLO in seconds (default 6.5).")
    args = parser.parse_args()

    per_file_rounds: list[list[float]] = []
    for path_str in args.json:
        path = Path(path_str)
        if not path.exists():
            print(json.dumps({"status": "ERROR", "error": f"missing file {path_str}"}))
            return 3
        rounds: list[float] = []
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                lat = rec.get("Latency", {})
                p50 = lat.get("p50")
                if p50 is None:
                    continue
                rounds.append(float(p50))
        per_file_rounds.append(rounds)

    rounds_seen = min(len(r) for r in per_file_rounds) if per_file_rounds else 0
    per_round_p50 = []
    for i in range(rounds_seen):
        per_round_p50.append(sum(r[i] for r in per_file_rounds) / len(per_file_rounds))

    result = {
        "status": "NOT_ENOUGH_ROUNDS",
        "rounds_seen": rounds_seen,
        "rounds_required": args.total_rounds,
        "tail_window": args.tail_window,
        "avg_p50_latency_s": None,
        "slo_s": args.slo,
        "per_round_p50": per_round_p50,
    }

    if rounds_seen < args.total_rounds:
        print(json.dumps(result))
        return 2

    tail = per_round_p50[-args.tail_window:]
    avg_p50 = sum(tail) / len(tail)
    result["avg_p50_latency_s"] = avg_p50
    result["status"] = "PASS" if avg_p50 < args.slo else "FAIL"
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
