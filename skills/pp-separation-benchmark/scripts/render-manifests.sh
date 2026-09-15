#!/usr/bin/env bash
# Render the @@VAR@@ placeholders in ../manifests/*.yaml into a target dir using
# environment variables. Portable to any host — nothing machine-specific is baked
# into the templates.
#
# Usage:
#   cp scripts/env.example my.env && edit my.env
#   set -a && . ./my.env && set +a
#   scripts/render-manifests.sh [OUT_DIR]     # default OUT_DIR: ./rendered
#
# Required vars (see scripts/env.example):
#   HF_HOST_PATH  MODEL_PATH  SERVED_MODEL  DRAFT_PATH  VLLM_IMAGE
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SELF_DIR/../manifests"
OUT="${1:-./rendered}"
: "${HF_HOST_PATH:?set HF_HOST_PATH (host dir with model weights)}"
: "${MODEL_PATH:?set MODEL_PATH (model path inside container)}"
: "${SERVED_MODEL:?set SERVED_MODEL (served model name)}"
: "${DRAFT_PATH:?set DRAFT_PATH (MTP draft model path inside container; use \"\" to drop spec-decode)}"
: "${VLLM_IMAGE:?set VLLM_IMAGE (vLLM serving image)}"

mkdir -p "$OUT"
for f in "$SRC"/*.yaml; do
  b="$(basename "$f")"
  sed -e "s#@@HF_HOST_PATH@@#${HF_HOST_PATH}#g" \
      -e "s#@@MODEL_PATH@@#${MODEL_PATH}#g" \
      -e "s#@@SERVED_MODEL@@#${SERVED_MODEL}#g" \
      -e "s#@@DRAFT_PATH@@#${DRAFT_PATH}#g" \
      -e "s#@@VLLM_IMAGE@@#${VLLM_IMAGE}#g" \
      "$f" > "$OUT/$b"
done
# fail loudly if any placeholder survived
if grep -rq '@@' "$OUT"/*.yaml; then
  echo "ERROR: unrendered placeholders remain:"; grep -rn '@@' "$OUT"/*.yaml; exit 1
fi
echo "rendered $(ls "$OUT"/*.yaml | wc -l) manifests into $OUT"
