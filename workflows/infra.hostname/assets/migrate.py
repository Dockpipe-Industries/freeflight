"""Use an already authorized ephemeral agent and the state-owned public host pin."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OLD = 'freeflight.staging.dockpipe.com'
NEW = 'freeflight-staging.dockpipe.com'
PIN = 'SHA256:VA2PxQpOfbaW2ux+GiiE7i1TjV4/qfapgmO48PaaIhk'
PRESERVE = '''set -eu
sudo /usr/sbin/sshd -T
sudo find /etc/ssh /etc/nginx -type f ! -name 'freeflight*' -exec sha256sum {} + | sort
systemctl cat dockpipe-release-sshd dockpipe-site-tunnel
readlink -f /srv/dockpipe-site/current
systemctl is-active nginx ssh dockpipe-release-sshd dockpipe-site-tunnel freeflight-release-sshd
'''


def main():
    if os.environ.get('FREEFLIGHT_HOSTNAME_STAGE') != 'approved-flat-hostname-only':
        raise ValueError('Explicit hostname-only stage required')
    key = os.environ.get('FREEFLIGHT_PINNED_HOST_PUBLIC_KEY', '')
    parts = key.split()
    if len(parts) != 2 or parts[0] != 'ssh-ed25519':
        raise ValueError('Pinned host public key required')
    fingerprint = 'SHA256:' + base64.b64encode(hashlib.sha256(base64.b64decode(parts[1], validate=True)).digest()).decode().rstrip('=')
    if fingerprint != PIN or not os.environ.get('SSH_AUTH_SOCK'):
        raise ValueError('Existing pinned operator agent required')
    spec = importlib.util.spec_from_file_location('bootstrap', ROOT / 'workflows/infra.up/assets/bootstrap.py')
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    nginx = bootstrap.configuration(['134.231.41.122/32'])[0].replace(NEW, OLD).encode()
    receiver = (ROOT / 'workflows/site.deploy.receive/assets/receive.py').read_bytes().replace(NEW.encode(), OLD.encode())
    payload = {'hashes': {'/etc/nginx/conf.d/freeflight-staging.conf': hashlib.sha256(nginx).hexdigest(),
                          '/usr/local/lib/freeflight/receive.py': hashlib.sha256(receiver).hexdigest()}}
    script = base64.b64encode(Path(__file__).with_name('remote.py').read_bytes()).decode()
    with tempfile.TemporaryDirectory(prefix='freeflight-hostname-') as directory:
        known = Path(directory) / 'known_hosts'
        known.write_text('159.203.53.54 ' + key + '\n')
        known.chmod(0o600)
        ssh = ['ssh', '-F', '/dev/null', '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'UpdateHostKeys=no',
               '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'HostKeyAlgorithms=ssh-ed25519',
               '-o', 'ConnectTimeout=10', '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes',
               '-o', 'UserKnownHostsFile=' + str(known), 'platform-admin@159.203.53.54']
        def run(command, data=None):
            result = subprocess.run(ssh + [command], input=data, capture_output=True, text=True, timeout=90)
            if result.returncode:
                raise RuntimeError('Pinned SSH operation failed; reconcile before retry')
            return result.stdout
        before = run(PRESERVE)
        result = run('sudo -n python3 -c "import base64;exec(base64.b64decode(\'' + script + '\'))"', json.dumps(payload))
        if run(PRESERVE) != before:
            raise RuntimeError('Existing service preservation mismatch')
        print(result.strip())
        print('Existing Cloud/admin services preserved; no site activated or delivery enabled.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(str(error))
