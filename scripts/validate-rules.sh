#!/usr/bin/env bash
# Validate Cursor project rules in rules/*.mdc
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RULES_DIR="${ROOT}/rules"
errors=0

shopt -s nullglob
mdc_files=("$RULES_DIR"/*.mdc)
if [[ ${#mdc_files[@]} -eq 0 ]]; then
  echo "FAIL: no .mdc files in $RULES_DIR"
  exit 1
fi

for rule in "${mdc_files[@]}"; do
  name="$(basename "$rule" .mdc)"

  if ! head -n 1 "$rule" | grep -q '^---$'; then
    echo "FAIL $name: missing YAML frontmatter"
    errors=$((errors + 1))
    continue
  fi

  fm="$(awk 'BEGIN{p=0} /^---$/{p++; if(p==2){exit}} p==1 && NR>1{print}' "$rule")"

  if ! echo "$fm" | grep -q '^description:'; then
    echo "FAIL $name: missing 'description' in frontmatter"
    errors=$((errors + 1))
  fi

  if ! echo "$fm" | grep -q '^alwaysApply:'; then
    echo "WARN $name: missing 'alwaysApply' (defaults to false in Cursor)"
  fi

  echo "OK  $name"
done

if [[ "$errors" -gt 0 ]]; then
  echo ""
  echo "$errors error(s)"
  exit 1
fi

echo ""
echo "All ${#mdc_files[@]} rule(s) passed validation."
