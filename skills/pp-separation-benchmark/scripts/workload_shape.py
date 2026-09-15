#!/usr/bin/env python3
"""Split a conversation-replay dataset into hot (non-truncated) vs cold (truncated)
pools and report request-count AND token-load fractions.

The key insight this surfaces: truncated requests are one fraction of the request
*count* but a different fraction of the token *load* (e.g. 52.9% of requests but
59.7% of tokens). Allocate cold/hot GPUs by token load, not request count.

Usage:
  workload_shape.py --input replay.jsonl \
      [--trunc-field enable_kv_evict] [--tokens-field input_tokens]

Each JSONL row is expected to carry a boolean truncation flag (default
`enable_kv_evict`, read from row or row["body"]) and an input token count
(default `input_tokens`; falls back to len(prompt)//4 heuristic if absent).
Prints a JSON summary with per-pool count, mean/median/p90/p99 input tokens,
request_fraction, token_load_fraction, and total_input_tokens.
"""
import argparse, json, statistics, sys


def _get(row, field):
    if field in row:
        return row[field]
    body = row.get("body")
    if isinstance(body, dict) and field in body:
        return body[field]
    return None


def _tokens(row, tokens_field):
    v = _get(row, tokens_field)
    if isinstance(v, (int, float)):
        return int(v)
    # heuristic fallback: ~4 chars/token over the prompt/messages text
    text = ""
    body = row.get("body", row)
    if isinstance(body, dict):
        if isinstance(body.get("prompt"), str):
            text = body["prompt"]
        elif isinstance(body.get("messages"), list):
            text = " ".join(m.get("content", "") for m in body["messages"]
                            if isinstance(m, dict) and isinstance(m.get("content"), str))
    return max(1, len(text) // 4)


def _pct(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize(toks):
    return {
        "count": len(toks),
        "mean_tokens": statistics.fmean(toks) if toks else 0.0,
        "median_tokens": statistics.median(toks) if toks else 0.0,
        "p90_tokens": _pct(toks, 0.90),
        "p99_tokens": _pct(toks, 0.99),
        "total_input_tokens": sum(toks),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True)
    ap.add_argument("--trunc-field", default="enable_kv_evict")
    ap.add_argument("--tokens-field", default="input_tokens")
    a = ap.parse_args()

    hot, cold = [], []  # non-truncated, truncated
    n = 0
    with open(a.input) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            n += 1
            flag = _get(row, a.trunc_field)
            if not isinstance(flag, bool):
                sys.exit(f"row {n}: truncation field {a.trunc_field!r} is not strict boolean: {flag!r}")
            t = _tokens(row, a.tokens_field)
            (cold if flag else hot).append(t)

    total_tok = sum(hot) + sum(cold)
    hs, cs = summarize(hot), summarize(cold)
    hs["request_fraction"] = len(hot) / n if n else 0.0
    cs["request_fraction"] = len(cold) / n if n else 0.0
    hs["token_load_fraction"] = sum(hot) / total_tok if total_tok else 0.0
    cs["token_load_fraction"] = sum(cold) / total_tok if total_tok else 0.0

    print(json.dumps({
        "rows": n,
        "truncation_rate": cs["request_fraction"],
        "hot_non_truncated": hs,
        "cold_truncated": cs,
        "note": "Allocate cold/hot GPUs by token_load_fraction, not request_fraction.",
    }, indent=2))


if __name__ == "__main__":
    main()
