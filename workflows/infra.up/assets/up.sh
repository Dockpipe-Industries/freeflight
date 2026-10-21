#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${FREEFLIGHT_CLOUD_CHECKOUT:?Select the reviewed isolated Cloud extension checkout}"
: "${FREEFLIGHT_CLOUD_COMMIT:?Pin the reviewed Cloud extension commit}"
: "${FREEFLIGHT_INFRA_ENVIRONMENT_ID:?Select the explicitly approved staging Environment}"
[[ "$FREEFLIGHT_CLOUD_COMMIT" =~ ^[a-f0-9]{40}$ ]]
[[ "$(git -C "$FREEFLIGHT_CLOUD_CHECKOUT" rev-parse HEAD)" == "$FREEFLIGHT_CLOUD_COMMIT" ]]
git -C "$FREEFLIGHT_CLOUD_CHECKOUT" diff --quiet HEAD --
[[ -f "$FREEFLIGHT_CLOUD_CHECKOUT/workflows/infra.up/assets/scripts/freeflight-up.ts" ]]
git diff --quiet HEAD --
export FREEFLIGHT_SOURCE_ROOT="$PWD"
export DOCKPIPE_SOURCE_ROOT="$FREEFLIGHT_CLOUD_CHECKOUT"
# Resolve only caller-selected credential references; no production Environment fallback.
mkdir -p "$FREEFLIGHT_CLOUD_CHECKOUT/bin/.local"
exec flock -n "$FREEFLIGHT_CLOUD_CHECKOUT/bin/.local/freeflight-up.lock" op run --environment "$FREEFLIGHT_INFRA_ENVIRONMENT_ID" -- \
  node "$FREEFLIGHT_CLOUD_CHECKOUT/workflows/infra.up/assets/scripts/freeflight-up.ts"
