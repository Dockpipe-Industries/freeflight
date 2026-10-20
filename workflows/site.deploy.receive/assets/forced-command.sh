#!/bin/sh
# Operator-installed, root-owned fixed entry point. Never install from CI.
# The restricted SSH account may invoke only this exact reviewed sudo command.
set -eu
[ "$#" -eq 1 ] || exit 1
cd /opt/freeflight/receiver
exec /usr/bin/env -i \
  PATH=/usr/local/bin:/usr/bin:/bin \
  HOME=/var/empty \
  DOCKPIPE_GLOBAL_ROOT=/opt/freeflight/receiver-runtime \
  DOCKPIPE_COMPILE_DEPS=0 \
  SSH_ORIGINAL_COMMAND="$1" \
  /usr/local/bin/dockpipe --workflow site.deploy.receive
