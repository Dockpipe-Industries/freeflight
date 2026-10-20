#!/bin/sh
# Root-owned entry point; executed as the unprivileged FreeFlight release account.
set -eu
[ "$#" -eq 0 ] || exit 1
exec /usr/bin/env -i PATH=/usr/bin:/bin \
  SSH_ORIGINAL_COMMAND="${SSH_ORIGINAL_COMMAND:-}" \
  /usr/bin/python3 -B /usr/local/lib/freeflight/receive.py \
  --receive /etc/freeflight-site/receiver.json
