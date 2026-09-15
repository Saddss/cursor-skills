#!/usr/bin/env bash
# Validate all SKILL.md files in this repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="${ROOT}/skills"
errors=0

if [[ ! -d "$SKILLS_DIR" ]]; then
  echo "FAIL: missing skills directory: $SKILLS_DIR" >&2
  exit 1
fi

while IFS= read -r -d '' skill; do
  dir="$(dirname "$skill")"
  name="$(basename "$dir")"

  # Frontmatter must exist
  if ! head -n 1 "$skill" | grep -q '^---$'; then
    echo "FAIL $name: missing YAML frontmatter"
    errors=$((errors + 1))
    continue
  fi

  # Extract frontmatter block
  fm="$(awk 'BEGIN{p=0} /^---$/{p++; if(p==2){exit}} p==1 && NR>1{print}' "$skill")"

  # Required fields
  for field in name description; do
    if ! echo "$fm" | grep -q "^${field}:"; then
      echo "FAIL $name: missing '$field' in frontmatter"
      errors=$((errors + 1))
    fi
  done

  # name must match directory
  fm_name="$(echo "$fm" | awk -F': *' '/^name:/{print $2; exit}' | tr -d ' "')"
  if [[ "$fm_name" != "$name" ]]; then
    echo "FAIL $name: frontmatter name '$fm_name' != directory '$name'"
    errors=$((errors + 1))
  fi

  # Line count
  lines="$(wc -l < "$skill")"
  if [[ "$lines" -gt 500 ]]; then
    echo "WARN $name: SKILL.md is $lines lines (>500)"
  fi

  # Broken relative file links (skip anchors, URLs, and inline-code false positives)
  while IFS= read -r target; do
    [[ "$target" == http* ]] && continue
    [[ "$target" =~ ^# ]] && continue
    [[ "$target" == *" "* ]] && continue
    [[ "$target" == *,* ]] && continue
    [[ "$target" != */* && "$target" != *.md ]] && continue
    if [[ ! -f "$dir/$target" ]]; then
      echo "FAIL $name: broken link -> $target"
      errors=$((errors + 1))
    fi
  done < <(grep -oE '\[[^]]+\]\([^)]+\)' "$skill" | sed -n 's/.*(\([^)]*\)).*/\1/p')

  echo "OK   $name ($lines lines)"
done < <(find "$SKILLS_DIR" -mindepth 2 -maxdepth 2 -name SKILL.md -print0 | sort -z)

if [[ "$errors" -gt 0 ]]; then
  echo "---"
  echo "$errors validation error(s)"
  exit 1
fi

echo "---"
echo "All skills valid"
