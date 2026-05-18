#!/usr/bin/env bash
# Smoke-test the bundled helper scripts against known fixtures.
#
# Run after editing scripts/analyze_rounds.py or scripts/prefix_cache_hit_rate.py
# to catch obvious regressions before pushing. Cheap (<1s) and self-contained --
# no network, no live engine, no GPU.
#
# Exit code: 0 if all checks pass, non-zero with case count otherwise.

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIX="$HERE/fixtures"

PASS=0
FAIL=0
ok() { printf '[OK]   %s\n' "$*"; PASS=$((PASS + 1)); }
ko() { printf '[FAIL] %s\n' "$*" >&2; FAIL=$((FAIL + 1)); }

check() {
  local name="$1" expected_rc="$2" expected_grep="$3"; shift 3
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -eq "$expected_rc" ] && echo "$out" | grep -q -- "$expected_grep"; then
    ok "$name"
  else
    ko "$name -- rc=$rc (want $expected_rc), out=$out"
  fi
}

# analyze_rounds.py
check "analyze_rounds: PASS fixture -> status PASS, rc 0" 0 '"status": "PASS"' \
  python3 "$HERE/analyze_rounds.py" \
    --json "$FIX/analyze_pass.jsonl" \
    --total-rounds 12 --tail-window 6 --slo 6.5

check "analyze_rounds: FAIL fixture -> status FAIL, rc 1" 1 '"status": "FAIL"' \
  python3 "$HERE/analyze_rounds.py" \
    --json "$FIX/analyze_fail.jsonl" \
    --total-rounds 12 --tail-window 6 --slo 6.5

check "analyze_rounds: short jsonl -> NOT_ENOUGH_ROUNDS, rc 2" 2 '"status": "NOT_ENOUGH_ROUNDS"' \
  python3 "$HERE/analyze_rounds.py" \
    --json "$FIX/analyze_pass.jsonl" \
    --total-rounds 24 --tail-window 12 --slo 6.5

# prefix_cache_hit_rate.py
check "prefix_cache: diff -> hit_rate 0.5, rc 0" 0 '"hit_rate": 0.5' \
  python3 "$HERE/prefix_cache_hit_rate.py" diff \
    --before "$FIX/prefix_before.prom" \
    --after "$FIX/prefix_after.prom"

check "prefix_cache: diff -> hits 100" 0 '"hits": 100' \
  python3 "$HERE/prefix_cache_hit_rate.py" diff \
    --before "$FIX/prefix_before.prom" \
    --after "$FIX/prefix_after.prom"

check "prefix_cache: no prefix metrics -> NO_PREFIX_METRICS, rc 2" 2 '"status": "NO_PREFIX_METRICS"' \
  python3 "$HERE/prefix_cache_hit_rate.py" diff \
    --before "$FIX/no_prefix_before.prom" \
    --after "$FIX/no_prefix_after.prom"

printf '\n=== %d passed, %d failed ===\n' "$PASS" "$FAIL"
exit "$FAIL"
