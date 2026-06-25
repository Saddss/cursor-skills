#!/usr/bin/env bash
# Bootstrap the model-perf-binary-search workspace.
# Idempotent: re-running on an already-set-up machine is cheap.
# Last stdout line: WORKDIR=<absolute path>
#
# Steps:
#   1. Verify shared disk mount (/mnt/shared/sss).
#   2. Clone or update Saddss/llm-inference-benchmarking @ sss-test.
#   3. uv venv + requirements.txt + requests.
#   4. Copy replay-logs-conv-avg5k.json into the workdir.
#   5. bench-runs/ + health check.
#
# Environment overrides (optional):
#   LLM_BENCH_DIR              workdir (default: $HOME/llm-inference-benchmarking)
#   LLM_BENCH_REPO_URL         default: https://github.com/Saddss/llm-inference-benchmarking
#   LLM_BENCH_REPO_BRANCH      default: sss-test
#   LLM_BENCH_DATASET_SRC      default: /mnt/shared/sss/data/replay-logs-conv-avg5k.json
#   LLM_BENCH_SHARED_MOUNT     default: /mnt/shared/sss

set -euo pipefail

REPO_URL="${LLM_BENCH_REPO_URL:-https://github.com/Saddss/llm-inference-benchmarking.git}"
REPO_BRANCH="${LLM_BENCH_REPO_BRANCH:-sss-test}"
SHARED_MOUNT="${LLM_BENCH_SHARED_MOUNT:-/mnt/shared/sss}"
DATASET_SRC="${LLM_BENCH_DATASET_SRC:-$SHARED_MOUNT/data/replay-logs-conv-avg5k.json}"
DATASET_NAME="replay-logs-conv-avg5k.json"
WORKDIR="${LLM_BENCH_DIR:-$HOME/llm-inference-benchmarking}"

log()  { printf '[bootstrap] %s\n' "$*" >&2; }
fail() { printf '[bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

log "target workdir: $WORKDIR"
log "source repo:    $REPO_URL ($REPO_BRANCH)"
log "shared mount:   $SHARED_MOUNT"
log "dataset source: $DATASET_SRC"

# 0) shared disk must be mounted before anything else
if [ ! -d "$SHARED_MOUNT" ]; then
  fail "共享盘未挂载：$SHARED_MOUNT 不存在。请先挂盘后再运行 bootstrap。"
fi

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

# 4) copy dataset (not symlink — portable across machines)
TARGET_DATASET="$WORKDIR/$DATASET_NAME"
if [ -f "$TARGET_DATASET" ] && [ -s "$TARGET_DATASET" ]; then
  log "dataset already present: $TARGET_DATASET ($(stat -c %s "$TARGET_DATASET" 2>/dev/null || echo ?) bytes)"
else
  [ -f "$DATASET_SRC" ] || fail "dataset not found at $DATASET_SRC (shared mount OK but file missing)"
  log "copying dataset -> $TARGET_DATASET (this may take a minute)..."
  cp -f "$DATASET_SRC" "$TARGET_DATASET"
  log "dataset copied ($(stat -c %s "$TARGET_DATASET" 2>/dev/null || echo ?) bytes)"
fi

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
printf 'WORKDIR=%s\n' "$WORKDIR"
exit 0
