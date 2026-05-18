#!/usr/bin/env bash
# Bootstrap the model-perf-binary-search workspace.
# Idempotent: re-running on an already-set-up machine is a no-op except for the
# final "WORKDIR=..." line on stdout. Safe to call at every skill invocation.
#
# What it does:
#   1. Clone or verify the benchmarking repo (default FlowGPT/llm-inference-benchmarking@qq-test).
#   2. Install uv (user-local) if missing.
#   3. Create a .venv inside the workdir and install requirements.txt.
#   4. Symlink the replay log dataset from the shared mount into the workdir.
#   5. Ensure bench-runs/ exists.
#
# Environment overrides (all optional):
#   LLM_BENCH_DIR           target workdir         (default: $HOME/llm-inference-benchmarking)
#   LLM_BENCH_REPO_URL      repo to clone          (default: https://github.com/FlowGPT/llm-inference-benchmarking)
#   LLM_BENCH_REPO_BRANCH   branch to check out    (default: qq-test)
#   LLM_BENCH_DATASET_SRC   replay-log source path (default: /mnt/shared/qq/llm-inference-benchmarking/replay-logs-origin.log)
#
# Last stdout line is the resolved WORKDIR=<absolute path> so the caller can
# `eval` it or grep it. All progress logs go to stderr.

set -euo pipefail

REPO_URL="${LLM_BENCH_REPO_URL:-https://github.com/FlowGPT/llm-inference-benchmarking}"
REPO_BRANCH="${LLM_BENCH_REPO_BRANCH:-qq-test}"
DATASET_SRC="${LLM_BENCH_DATASET_SRC:-/mnt/shared/qq/llm-inference-benchmarking/replay-logs-origin.log}"
WORKDIR="${LLM_BENCH_DIR:-$HOME/llm-inference-benchmarking}"

log()  { printf '[bootstrap] %s\n' "$*" >&2; }
fail() { printf '[bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

log "target workdir: $WORKDIR"
log "source repo:    $REPO_URL ($REPO_BRANCH)"
log "dataset source: $DATASET_SRC"

# 1) clone or verify the benchmarking repo
if [ ! -d "$WORKDIR/.git" ]; then
  if [ -e "$WORKDIR" ] && [ -n "$(ls -A "$WORKDIR" 2>/dev/null)" ]; then
    fail "$WORKDIR exists and is non-empty but has no .git; refusing to clone over it. Move it aside or set LLM_BENCH_DIR to a different path."
  fi
  log "cloning ($REPO_BRANCH)..."
  git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$WORKDIR" >&2
else
  current_branch="$(git -C "$WORKDIR" branch --show-current 2>/dev/null || echo '?')"
  log "repo present at $WORKDIR (branch: $current_branch); skipping clone"
fi

for f in online_replay.py requirements.txt; do
  [ -f "$WORKDIR/$f" ] || fail "$WORKDIR/$f missing - clone failed or wrong branch"
done

# 2) ensure uv is on PATH
if ! command -v uv >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
  else
    log "uv not found, installing to ~/.local/bin"
    curl -fsSL https://astral.sh/uv/install.sh | sh >&2 || fail "uv install failed - see https://docs.astral.sh/uv/"
    export PATH="$HOME/.local/bin:$PATH"
    # persist for future shells
    if [ -f "$HOME/.bashrc" ] && ! grep -q '.local/bin' "$HOME/.bashrc"; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
  fi
fi
command -v uv >/dev/null 2>&1 || fail "uv still not available after install attempt"
log "uv: $(uv --version 2>&1)"

# 3) venv + requirements
cd "$WORKDIR"
if [ ! -d ".venv" ]; then
  log "creating .venv via uv venv"
  uv venv --quiet >&2
fi
log "syncing requirements.txt (uv pip install)"
uv pip install --quiet -r requirements.txt >&2

# Patch missing deps that upstream qq-test's requirements.txt forgets but
# online_replay.py imports directly. Keep this list short; only add a package
# here after confirming it's missing on a freshly-cloned qq-test branch.
EXTRA_DEPS=(requests)
log "installing extra deps not pinned by upstream: ${EXTRA_DEPS[*]}"
uv pip install --quiet "${EXTRA_DEPS[@]}" >&2

# 4) dataset symlink
TARGET_DATASET="$WORKDIR/replay-logs-origin.log"
if [ -e "$TARGET_DATASET" ] || [ -L "$TARGET_DATASET" ]; then
  if [ -L "$TARGET_DATASET" ]; then
    log "dataset symlink already in place -> $(readlink -f "$TARGET_DATASET" 2>/dev/null || readlink "$TARGET_DATASET")"
  else
    log "dataset file exists (non-symlink), size=$(stat -c %s "$TARGET_DATASET" 2>/dev/null || echo ?) bytes"
  fi
else
  [ -e "$DATASET_SRC" ] || fail "dataset source not found at $DATASET_SRC; mount the shared disk or set LLM_BENCH_DATASET_SRC"
  log "symlinking dataset -> $TARGET_DATASET"
  ln -s "$DATASET_SRC" "$TARGET_DATASET"
fi

# 5) bench-runs dir
mkdir -p "$WORKDIR/bench-runs"

# 6) sanity: venv python can import the main module (all deps resolved)
smoke_err="$("$WORKDIR/.venv/bin/python" -c "
import sys
sys.path.insert(0, '$WORKDIR')
try:
    import online_replay  # noqa: F401
except Exception as e:
    print(f'{type(e).__name__}: {e}')
" 2>&1)"
if [ -n "$smoke_err" ]; then
  fail "online_replay import smoke check failed: $smoke_err
       fix the missing dependency, then either edit requirements.txt or add it to EXTRA_DEPS in bootstrap.sh"
fi
log "smoke check: online_replay imports OK"

log "ready"

# Last line of stdout = the resolved workdir, for callers to capture.
printf 'WORKDIR=%s\n' "$WORKDIR"
