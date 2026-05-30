#!/usr/bin/env bash
# Migrate from pre-2025 layout (~/.cursor/skills = git root, skills at top level)
# to current layout (~/.cursor/cursor-skills with skills/ + rules/, symlinks).
set -euo pipefail

CURSOR="${HOME}/.cursor"
LEGACY="${CURSOR}/skills"
NEW_REPO="${CURSOR}/cursor-skills"
INSTALL="${NEW_REPO}/scripts/install.sh"

ts="$(date +%s)"

is_legacy_git_root() {
  [[ -d "${LEGACY}/.git" ]] && [[ ! -L "${LEGACY}" ]]
}

has_top_level_skill() {
  local d
  for d in "${LEGACY}"/*/; do
    [[ -f "${d}SKILL.md" ]] && return 0
  done
  return 1
}

already_migrated() {
  [[ -d "${NEW_REPO}/skills" ]] && [[ -d "${NEW_REPO}/rules" ]] \
    && [[ -L "${CURSOR}/skills" || -L "${CURSOR}/rules" ]]
}

echo "== Cursor skills/rules migration =="

if already_migrated; then
  echo "Looks already migrated. Pull latest:"
  echo "  cd ${NEW_REPO} && git pull"
  echo "  bash ${INSTALL}"
  exit 0
fi

if is_legacy_git_root && has_top_level_skill; then
  echo "Detected legacy layout: git root at ${LEGACY}"
  if [[ -d "${NEW_REPO}" ]]; then
    bak="${NEW_REPO}.bak.${ts}"
    echo "WARN: ${NEW_REPO} exists; moving to ${bak}"
    mv "${NEW_REPO}" "${bak}"
  fi
  echo "Renaming ${LEGACY} -> ${NEW_REPO}"
  mv "${LEGACY}" "${NEW_REPO}"
elif [[ -d "${NEW_REPO}/.git" ]]; then
  echo "Repo already at ${NEW_REPO}; pulling..."
else
  echo "No legacy repo at ${LEGACY}; cloning fresh..."
  gh repo clone Saddss/cursor-skills "${NEW_REPO}"
fi

cd "${NEW_REPO}"
git fetch origin
git pull --ff-only origin main || git pull origin main

if [[ ! -d skills ]] || [[ ! -d rules ]]; then
  echo "ERROR: remote main still looks like legacy layout (no skills/ or rules/)." >&2
  echo "       Ask repo owner to push the restructure commit first." >&2
  exit 1
fi

bash "${INSTALL}"
echo ""
echo "Done. Verify:"
echo "  readlink ${CURSOR}/skills ${CURSOR}/rules"
echo "  ls ${NEW_REPO}/skills | wc -l    # expect 36"
echo "  ls ${NEW_REPO}/rules/*.mdc       # expect 4"
echo "Restart Cursor."
