#!/usr/bin/env bash
# Link repo skills/ and rules/ to ~/.cursor/skills and ~/.cursor/rules (siblings).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURSOR_DIR="${HOME}/.cursor"

for name in skills rules; do
  src="${REPO_ROOT}/${name}"
  dest="${CURSOR_DIR}/${name}"

  if [[ ! -d "$src" ]]; then
    echo "ERROR: missing ${src}" >&2
    exit 1
  fi

  if [[ -e "$dest" && ! -L "$dest" ]]; then
    backup="${dest}.bak.$(date +%s)"
    echo "WARN: ${dest} exists (not a symlink); moving to ${backup}"
    mv "$dest" "$backup"
  elif [[ -L "$dest" ]]; then
    rm -f "$dest"
  fi

  ln -sfn "$src" "$dest"
  echo "OK  ${dest} -> ${src}"
done

echo ""
echo "Installed skills + rules under ${CURSOR_DIR}"
echo "Restart Cursor or open a new Agent chat if rules do not appear immediately."
