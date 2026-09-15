#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

SHARED_DATA="$TMPDIR/shared/data"
WORKDIR="$TMPDIR/work"
mkdir -p "$SHARED_DATA" "$WORKDIR"
printf 'alpha-v1\n' > "$SHARED_DATA/alpha.jsonl"
printf 'beta\n' > "$SHARED_DATA/beta.jsonl"

eval "$("$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/alpha.jsonl" "$WORKDIR")"

test "$DATASET" = "$WORKDIR/datasets/alpha.jsonl"
test "$(cat "$DATASET")" = "alpha-v1"
test ! -e "$WORKDIR/datasets/beta.jsonl"

printf 'alpha-v2\n' > "$SHARED_DATA/alpha.jsonl"
eval "$("$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/alpha.jsonl" "$WORKDIR")"
test "$(cat "$DATASET")" = "alpha-v1"

printf 'outside\n' > "$TMPDIR/outside.jsonl"
if "$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$TMPDIR/outside.jsonl" "$WORKDIR" >/dev/null 2>&1; then
  echo "outside source unexpectedly accepted" >&2
  exit 1
fi

if (
  cd "$TMPDIR/shared"
  "$SCRIPT_DIR/prepare_dataset.sh" \
    "$SHARED_DATA" "data/alpha.jsonl" "$WORKDIR" >/dev/null 2>&1
); then
  echo "relative source unexpectedly accepted" >&2
  exit 1
fi

if "$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/missing.jsonl" "$WORKDIR" >/dev/null 2>&1; then
  echo "missing source unexpectedly accepted" >&2
  exit 1
fi

: > "$SHARED_DATA/empty.jsonl"
if "$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/empty.jsonl" "$WORKDIR" >/dev/null 2>&1; then
  echo "empty source unexpectedly accepted" >&2
  exit 1
fi

printf 'gamma\n' > "$SHARED_DATA/gamma.jsonl"
: > "$WORKDIR/datasets/gamma.jsonl"
if "$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/gamma.jsonl" "$WORKDIR" >/dev/null 2>&1; then
  echo "empty local target unexpectedly overwritten" >&2
  exit 1
fi
test ! -s "$WORKDIR/datasets/gamma.jsonl"

ln -s "$SHARED_DATA/alpha.jsonl" "$SHARED_DATA/alpha-alias.jsonl"
eval "$("$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/alpha-alias.jsonl" "$WORKDIR")"
test "$DATASET" = "$WORKDIR/datasets/alpha-alias.jsonl"
test -s "$DATASET"

printf 'delta\n' > "$SHARED_DATA/delta.jsonl"
ln -s "$TMPDIR/does-not-exist" "$WORKDIR/datasets/delta.jsonl"
if "$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/delta.jsonl" "$WORKDIR" >/dev/null 2>&1; then
  echo "dangling local symlink unexpectedly overwritten" >&2
  exit 1
fi
test -L "$WORKDIR/datasets/delta.jsonl"

printf 'epsilon\n' > "$SHARED_DATA/epsilon.jsonl"
printf 'victim\n' > "$TMPDIR/victim"
ln -s "$TMPDIR/victim" "$WORKDIR/datasets/epsilon.jsonl.partial"
eval "$("$SCRIPT_DIR/prepare_dataset.sh" \
  "$SHARED_DATA" "$SHARED_DATA/epsilon.jsonl" "$WORKDIR")"
test "$DATASET" = "$WORKDIR/datasets/epsilon.jsonl"
test "$(cat "$DATASET")" = "epsilon"
test "$(cat "$TMPDIR/victim")" = "victim"
test -L "$WORKDIR/datasets/epsilon.jsonl.partial"

EMPTY_SHARED="$TMPDIR/empty-shared"
mkdir -p "$EMPTY_SHARED/data"
if LLM_BENCH_SHARED_MOUNT="$EMPTY_SHARED" \
  LLM_BENCH_DIR="$TMPDIR/empty-work" \
  LLM_BENCH_DATASET_SRC="$EMPTY_SHARED/data/missing.jsonl" \
  "$SCRIPT_DIR/bootstrap.sh" >/dev/null 2>&1; then
  echo "empty shared directory unexpectedly accepted" >&2
  exit 1
fi

HIDDEN_SHARED="$TMPDIR/hidden-shared"
mkdir -p "$HIDDEN_SHARED/data"
printf 'hidden\n' > "$HIDDEN_SHARED/data/.hidden.jsonl"
set +e
hidden_output="$(
  LLM_BENCH_SHARED_MOUNT="$HIDDEN_SHARED" \
  LLM_BENCH_DIR="$TMPDIR/hidden-work" \
  "$SCRIPT_DIR/bootstrap.sh" 2>&1
)"
hidden_rc=$?
set -e
test "$hidden_rc" -ne 0
if [[ "$hidden_output" != *未选择数据集* ]]; then
  echo "hidden dataset was treated as an empty shared directory" >&2
  exit 1
fi

printf 'PASS\n'
