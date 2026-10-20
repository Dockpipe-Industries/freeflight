#!/usr/bin/env bash
set -euo pipefail
[[ "${SITE_DEPLOY_ENABLED:-}" == true ]] || {
  echo "FreeFlight receiver is not enabled. Configure the separately approved identity, pinned host key, host and port; release publication is independent." >&2
  exit 1
}
: "${SITE_DEPLOY_HOST:?Missing approved FreeFlight receiver host}"
: "${SITE_DEPLOY_SSH_PORT:?Missing approved receiver port}"
: "${SITE_DEPLOY_KNOWN_HOSTS:?Missing independently trusted host key}"
: "${SITE_DEPLOY_PRIVATE_KEY:?Missing dedicated FreeFlight receiver identity}"
[[ "$SITE_DEPLOY_HOST" =~ ^[a-zA-Z0-9.-]+$ && "$SITE_DEPLOY_HOST" != -* ]]
[[ "$SITE_DEPLOY_SSH_PORT" =~ ^[0-9]+$ ]] && (( SITE_DEPLOY_SSH_PORT > 0 && SITE_DEPLOY_SSH_PORT < 65536 ))
[[ "${FREEFLIGHT_DEPLOY_ENVIRONMENT:-}" == staging || "${FREEFLIGHT_DEPLOY_ENVIRONMENT:-}" == production ]]
artifact=bin/.local/site-pipeline/delivery.tar
[[ -f "$artifact" && ! -L "$artifact" ]]
digest="$(sha256sum "$artifact")"
digest="${digest%% *}"
[[ "$digest" =~ ^[a-f0-9]{64}$ ]]
umask 077
trust_directory="$(mktemp -d bin/.local/site-send.XXXXXXXX)"
unset SSH_AGENT_PID
cleanup() {
  if [[ -n "${SSH_AGENT_PID:-}" ]]; then ssh-agent -k >/dev/null; fi
  rm -f -- "$trust_directory/known_hosts"
  rmdir -- "$trust_directory"
}
trap cleanup EXIT
printf '%s\n' "$SITE_DEPLOY_KNOWN_HOSTS" > "$trust_directory/known_hosts"
eval "$(ssh-agent -s)" >/dev/null
printf '%s\n' "$SITE_DEPLOY_PRIVATE_KEY" | ssh-add - >/dev/null 2>&1
unset SITE_DEPLOY_PRIVATE_KEY
ssh -F /dev/null -p "$SITE_DEPLOY_SSH_PORT" -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -o GlobalKnownHostsFile=/dev/null -o UpdateHostKeys=no -o IdentitiesOnly=no \
  -o "UserKnownHostsFile=$trust_directory/known_hosts" \
  "freeflight-release@$SITE_DEPLOY_HOST" "deploy $FREEFLIGHT_DEPLOY_ENVIRONMENT $digest" \
  < "$artifact" > bin/.local/site-pipeline/activation.log
python3 - <<'PY'
import json
from pathlib import Path
root = Path("bin/.local/site-pipeline")
expected = json.loads((root / "deployment.json").read_text())
lines = (root / "activation.log").read_text().splitlines()
result = json.loads(next(line for line in reversed(lines) if line.startswith('{"schema":')))
assert result["status"] == "activated" and result["verifiedHttps"] is True
assert all(result[key] == expected[key] for key in expected)
(root / "activation.json").write_text(json.dumps(result, indent=2) + "\n")
PY
