#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_dir="$(dirname -- "$script_dir")/rules"
target_dir="${CURSOR_RULES_DIR:-$HOME/.cursor/rules}"

mkdir -p "$target_dir"

for source_file in "$source_dir"/*.mdc; do
  target_file="$target_dir/$(basename -- "$source_file")"
  if [[ -e "$target_file" ]] && ! cmp -s "$source_file" "$target_file"; then
    echo "Refusing to overwrite a different rule: $target_file" >&2
    exit 1
  fi
  cp "$source_file" "$target_file"
  echo "Installed $target_file"
done
