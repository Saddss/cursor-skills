#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: prepare_dataset.sh SHARED_DATA_DIR DATASET_SRC WORKDIR" >&2
  exit 2
fi

case "$2" in
  /*) ;;
  *)
    echo "dataset source must be an absolute path: $2" >&2
    exit 1
    ;;
esac

SHARED_DATA_DIR="$(realpath "$1")"
SELECTED_DATASET_SRC="$2"
DATASET_SRC="$(realpath "$SELECTED_DATASET_SRC")"
WORKDIR="$(realpath "$3")"

case "$DATASET_SRC" in
  "$SHARED_DATA_DIR"/*) ;;
  *)
    echo "dataset must be under $SHARED_DATA_DIR: $DATASET_SRC" >&2
    exit 1
    ;;
esac

if [ ! -f "$SELECTED_DATASET_SRC" ] || [ ! -s "$SELECTED_DATASET_SRC" ]; then
  echo "dataset is missing or empty: $SELECTED_DATASET_SRC" >&2
  exit 1
fi

DATASET_DIR="$WORKDIR/datasets"
TARGET_DATASET="$DATASET_DIR/$(basename "$SELECTED_DATASET_SRC")"
mkdir -p "$DATASET_DIR"

if [ -L "$TARGET_DATASET" ]; then
  echo "local dataset must not be a symlink: $TARGET_DATASET" >&2
  exit 1
elif [ -e "$TARGET_DATASET" ]; then
  if [ ! -f "$TARGET_DATASET" ] || [ ! -s "$TARGET_DATASET" ]; then
    echo "local dataset exists but is not a non-empty file: $TARGET_DATASET" >&2
    exit 1
  fi
  echo "[bootstrap] local dataset already present: $TARGET_DATASET" >&2
else
  PARTIAL="$(mktemp "$DATASET_DIR/.$(basename "$TARGET_DATASET").partial.XXXXXX")"
  trap 'rm -f "$PARTIAL"' EXIT
  echo "[bootstrap] copying selected dataset: $SELECTED_DATASET_SRC" >&2
  cp "$SELECTED_DATASET_SRC" "$PARTIAL"
  mv -n "$PARTIAL" "$TARGET_DATASET"
  if [ -e "$PARTIAL" ]; then
    echo "local dataset appeared during copy: $TARGET_DATASET" >&2
    exit 1
  fi
  if [ -L "$TARGET_DATASET" ] || [ ! -f "$TARGET_DATASET" ] || [ ! -s "$TARGET_DATASET" ]; then
    echo "copied dataset is not a non-empty regular file: $TARGET_DATASET" >&2
    exit 1
  fi
  trap - EXIT
fi

printf 'DATASET=%q\n' "$TARGET_DATASET"
