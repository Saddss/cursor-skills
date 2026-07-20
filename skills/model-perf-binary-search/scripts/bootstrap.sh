#!/usr/bin/env bash
# Bootstrap the model-perf-binary-search workspace.
# Idempotent: re-running on an already-set-up machine is cheap.
# Stdout: shell-safe WORKDIR=<path> and DATASET=<path> assignments.
#
# Steps:
#   1. Verify shared disk mount (/mnt/shared/sss).
#   2. Clone or update Saddss/llm-inference-benchmarking @ sss-test.
#   3. uv venv + requirements.txt + requests.
#   4. Copy the explicitly selected shared dataset into the workdir.
#   5. bench-runs/ + health check.
#
# Environment overrides (optional):
#   LLM_BENCH_DIR              workdir (default: $HOME/llm-inference-benchmarking)
#   LLM_BENCH_REPO_URL         default: https://github.com/Saddss/llm-inference-benchmarking
#   LLM_BENCH_REPO_BRANCH      default: sss-test
#   LLM_BENCH_DATASET_SRC      required: selected file under <mount>/data
#   LLM_BENCH_SHARED_MOUNT     default: /mnt/shared/sss

set -euo pipefail

REPO_URL="${LLM_BENCH_REPO_URL:-https://github.com/Saddss/llm-inference-benchmarking.git}"
REPO_BRANCH="${LLM_BENCH_REPO_BRANCH:-sss-test}"
SHARED_MOUNT="${LLM_BENCH_SHARED_MOUNT:-/mnt/shared/sss}"
SHARED_DATA_DIR="$SHARED_MOUNT/data"
DATASET_SRC="${LLM_BENCH_DATASET_SRC:-}"
WORKDIR="${LLM_BENCH_DIR:-$HOME/llm-inference-benchmarking}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { printf '[bootstrap] %s\n' "$*" >&2; }
fail() { printf '[bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

log "target workdir: $WORKDIR"
log "source repo:    $REPO_URL ($REPO_BRANCH)"
log "shared mount:   $SHARED_MOUNT"
log "dataset source: ${DATASET_SRC:-<not selected>}"

# 0) each session must explicitly select one shared dataset
[ -d "$SHARED_DATA_DIR" ] || fail "共享数据目录不存在：$SHARED_DATA_DIR。请先挂盘。"
if ! (
  shopt -s dotglob nullglob
  for candidate in "$SHARED_DATA_DIR"/*; do
    if [ -f "$candidate" ] && [ -s "$candidate" ]; then
      exit 0
    fi
  done
  exit 1
); then
  fail "共享数据目录没有非空数据集：$SHARED_DATA_DIR。"
fi
[ -n "$DATASET_SRC" ] || fail "未选择数据集：请先列出 $SHARED_DATA_DIR 并设置 LLM_BENCH_DATASET_SRC。"
case "$DATASET_SRC" in
  /*) ;;
  *) fail "数据集路径必须是绝对路径：$DATASET_SRC" ;;
esac
[ -f "$DATASET_SRC" ] && [ -s "$DATASET_SRC" ] || fail "数据集不存在或为空：$DATASET_SRC"
CANONICAL_SHARED_DATA_DIR="$(realpath "$SHARED_DATA_DIR")"
CANONICAL_DATASET_SRC="$(realpath "$DATASET_SRC")"
case "$CANONICAL_DATASET_SRC" in
  "$CANONICAL_SHARED_DATA_DIR"/*) ;;
  *) fail "数据集必须位于 $CANONICAL_SHARED_DATA_DIR：$CANONICAL_DATASET_SRC" ;;
esac

# 1) clone or update repo @ sss-test
if [ ! -d "$WORKDIR/.git" ]; then
  if [ -e "$WORKDIR" ] && [ -n "$(ls -A "$WORKDIR" 2>/dev/null)" ]; then
    fail "$WORKDIR exists and is non-empty but has no .git; move it aside or set LLM_BENCH_DIR."
  fi
  log "cloning ($REPO_BRANCH)..."
  git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$WORKDIR" >&2
else
  current_branch="$(git -C "$WORKDIR" branch --show-current 2>/dev/null || echo '?')"
  log "repo present (branch: $current_branch); fetching $REPO_BRANCH"
  git -C "$WORKDIR" fetch origin "$REPO_BRANCH" >&2 || fail "git fetch failed"
  git -C "$WORKDIR" checkout "$REPO_BRANCH" >&2 || fail "git checkout $REPO_BRANCH failed"
  if ! git -C "$WORKDIR" pull --ff-only origin "$REPO_BRANCH" >&2; then
    log "WARN: git pull --ff-only failed (local commits?); continuing with current HEAD"
  fi
fi

for f in online_replay.py requirements.txt; do
  [ -f "$WORKDIR/$f" ] || fail "$WORKDIR/$f missing — wrong branch or incomplete clone"
done

# 2) uv
if ! command -v uv >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
  else
    log "uv not found, installing to ~/.local/bin"
    curl -fsSL https://astral.sh/uv/install.sh | sh >&2 || fail "uv install failed"
    export PATH="$HOME/.local/bin:$PATH"
    if [ -f "$HOME/.bashrc" ] && ! grep -q '.local/bin' "$HOME/.bashrc"; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
  fi
fi
command -v uv >/dev/null 2>&1 || fail "uv not available"
log "uv: $(uv --version 2>&1)"

# 3) venv + deps
cd "$WORKDIR"
if [ ! -d ".venv" ]; then
  log "creating .venv"
  uv venv --quiet >&2
fi
log "uv pip install -r requirements.txt"
uv pip install --quiet -r requirements.txt >&2
log "uv pip install requests"
uv pip install --quiet requests >&2

# 4) copy only the selected dataset (not symlink — portable across machines)
DATASET_ASSIGNMENT="$(
  "$SCRIPT_DIR/prepare_dataset.sh" "$SHARED_DATA_DIR" "$DATASET_SRC" "$WORKDIR"
)" || fail "selected dataset preparation failed"

# 5) bench-runs
mkdir -p "$WORKDIR/bench-runs"

# 6) import smoke
smoke_err="$("$WORKDIR/.venv/bin/python" -c "
import sys
sys.path.insert(0, '$WORKDIR')
try:
    import online_replay  # noqa: F401
except Exception as e:
    print(f'{type(e).__name__}: {e}')
" 2>&1)"
if [ -n "$smoke_err" ]; then
  fail "online_replay import failed: $smoke_err"
fi
log "smoke check: online_replay imports OK"

# 7) health check
HEALTH_PY="$(dirname "$0")/health_check.py"
HEALTH_PYTHON="$WORKDIR/.venv/bin/python"
if python3 -c "import torch" >/dev/null 2>&1; then
  HEALTH_PYTHON="$(command -v python3)"
fi
log "running health check"
set +e
"$HEALTH_PYTHON" "$HEALTH_PY" --workdir "$WORKDIR" >&2
HEALTH_RC=$?
set -e
log "health check exit=$HEALTH_RC (json: $WORKDIR/.health_check.json)"

log "ready"
printf 'WORKDIR=%q\n' "$WORKDIR"
printf '%s\n' "$DATASET_ASSIGNMENT"
exit 0
