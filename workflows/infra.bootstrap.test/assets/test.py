"""Destructive only to a dedicated disposable CI VM; never run on an operator/server host."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
if not (os.geteuid() == 0 and os.environ.get('GITHUB_ACTIONS') == 'true'
        and os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'
        and os.environ.get('RUNNER_OS') == 'Linux'
        and os.environ.get('GITHUB_REPOSITORY') == 'Dockpipe-Industries/freeflight'):
    raise SystemExit('Requires the dedicated disposable GitHub-hosted Linux job; no host changes performed')
sys.path.insert(0, str(ROOT / 'workflows/infra.up/assets'))
sys.path.insert(0, str(ROOT / 'workflows/site.deploy.receive/assets'))
import bootstrap
from test_receive import fixture, encode


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, timeout=120, **kwargs)


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def http(port, path='/', headers=None):
    try:
        with urlopen(Request('http://127.0.0.1:' + str(port) + path, headers=headers or {}), timeout=3) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def main():
    run(['apt-get', 'update'])
    run(['apt-get', 'install', '-y', '--no-install-recommends', 'nginx', 'openssh-server', 'openssh-client'],
        env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})
    work = Path(tempfile.mkdtemp(prefix='freeflight-ci-'))
    work.chmod(0o700)
    # These keys exist only in this disposable runner and never become artifacts.
    key = work / 'release-key'
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)])
    public = ' '.join(key.with_suffix('.pub').read_text().split()[:2])
    run(['ssh-keygen', '-A'])
    Path('/run/sshd').mkdir(exist_ok=True)
    try:
        pwd.getpwnam('platform-admin')
    except KeyError:
        run(['useradd', '--system', '--shell', '/bin/sh', 'platform-admin'])
    # Controlled pre-existing administrator policy in the disposable VM.
    admin = Path('/etc/ssh/sshd_config')
    admin.write_text('Port 22\nHostKey /etc/ssh/ssh_host_ed25519_key\nAllowUsers platform-admin\n'
                     'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\nUsePAM yes\n')
    sentinel = Path('/etc/nginx/conf.d/preexisting-site-sentinel.conf')
    sentinel.write_text('server { listen 127.0.0.1:18082; location / { return 200 "existing-site-untouched"; } }\n')
    run(['nginx', '-t'])
    run(['systemctl', 'enable', '--now', 'nginx'])
    run(['systemctl', 'reload', 'nginx'])
    original = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in [admin, sentinel]}
    assert_true(http(18082)[1] == b'existing-site-untouched', 'Pre-existing site unavailable')
    payload = {'publicKey': public, 'networks': ['192.0.2.7/32'],
               'receiver': base64.b64encode((ROOT / 'workflows/site.deploy.receive/assets/receive.py').read_bytes()).decode(),
               'entrypoint': base64.b64encode((ROOT / 'workflows/site.deploy.receive/assets/forced-command.sh').read_bytes()).decode()}
    bootstrap.install(payload)
    bootstrap.install(payload)  # Supported repeat setup keeps identity and existing services.
    # Exercise the bounded hostname migration against real Nginx before activation.
    sys.path.insert(0, str(ROOT / 'workflows/infra.hostname/assets'))
    from remote import FILES, OLD, NEW, migrate
    hashes = {}
    for name in FILES:
        path = Path(name)
        old_data = path.read_bytes().replace(NEW.encode(), OLD.encode())
        path.write_bytes(old_data)
        hashes[name] = hashlib.sha256(old_data).hexdigest()
    run(['nginx', '-t'])
    run(['systemctl', 'reload', 'nginx'])
    migrate({'hashes': hashes})
    # systemctl reload returns after signaling Nginx; replacement workers become
    # ready asynchronously. Poll both required outcomes without repeating a mutation.
    deadline = time.monotonic() + 5
    while True:
        new_status = http(18081, '/healthz', {'Host': NEW, 'X-DockPipe-Client-IP': '192.0.2.7'})[0]
        old_status = http(18081, '/healthz', {'Host': OLD, 'X-DockPipe-Client-IP': '192.0.2.7'})[0]
        if (new_status, old_status) == (200, 404) or time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    assert_true(new_status == 200, 'New hostname did not become ready: HTTP ' + str(new_status))
    assert_true(old_status == 404, 'Old hostname remained accepted: HTTP ' + str(old_status))
    for path, digest in original.items():
        assert_true(hashlib.sha256(path.read_bytes()).hexdigest() == digest, 'Existing service configuration changed')
    assert_true(http(18082)[1] == b'existing-site-untouched', 'Existing service changed during install')
    assert_true(http(18081, headers={'Host': 'freeflight-staging.dockpipe.com'})[0] == 403, 'Missing visitor identity accepted')
    assert_true(http(18081, headers={'Host': 'wrong.example', 'X-DockPipe-Client-IP': '192.0.2.7'})[0] == 404, 'Wrong host accepted')
    account = pwd.getpwnam('freeflight-release')
    assert_true(account.pw_uid != 0 and os.getgrouplist(account.pw_name, account.pw_gid) == [account.pw_gid], 'Privileged group grant')
    denied = subprocess.run(['runuser', '-u', 'freeflight-release', '--', 'sudo', '-n', 'true'], capture_output=True)
    assert_true(denied.returncode != 0, 'Release account received sudo')
    trust = work / 'known_hosts'
    trust.write_text('[127.0.0.1]:2223 ' + ' '.join(Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()[:2]) + '\n')
    ssh = ['ssh', '-F', '/dev/null', '-p', '2223', '-i', str(key), '-o', 'IdentityAgent=none', '-o', 'IdentitiesOnly=yes',
           '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'GlobalKnownHostsFile=/dev/null',
           '-o', 'UserKnownHostsFile=' + str(trust), '-o', 'ConnectTimeout=5']
    def deliver(bundle, command=None):
        data, digest = encode(bundle)
        return subprocess.run(ssh + ['freeflight-release@127.0.0.1', command or 'deploy ' + digest],
                              input=data, capture_output=True, timeout=35)
    for command in ['id', 'deploy ' + '0' * 64, 'deploy staging ' + 'a' * 64]:
        assert_true(deliver(fixture(), command).returncode != 0, 'Forbidden command accepted')
    for user in ['root', 'platform-admin']:
        denied = subprocess.run(ssh + [user + '@127.0.0.1', 'id'], capture_output=True, timeout=10)
        assert_true(denied.returncode != 0, 'Release listener accepted administrator')
    denied = subprocess.run(ssh + ['-o', 'ExitOnForwardFailure=yes', '-N', '-R', '0:127.0.0.1:18082',
                                  'freeflight-release@127.0.0.1'], capture_output=True, timeout=10)
    assert_true(denied.returncode != 0, 'SSH forwarding accepted')
    bad = fixture()
    bad['product'] = 'dockpipe'
    assert_true(deliver(bad).returncode != 0, 'Other product accepted')

    # Keep real Nginx serving and inject deterministic HTTP health failures via a local proxy.
    nginx = Path('/etc/nginx/conf.d/freeflight-staging.conf')
    nginx.write_text(nginx.read_text().replace('127.0.0.1:18080', '127.0.0.1:18083'))
    run(['nginx', '-t'])
    run(['systemctl', 'reload', 'nginx'])
    state = {'fail_all': False, 'observed': []}
    serving = Path('/srv/freeflight-staging')
    class FaultProxy(BaseHTTPRequestHandler):
        def do_GET(self):
            current = serving / 'current'
            try:
                receipt = json.loads((current / 'activation.json').read_text())
                state['observed'].append(current.resolve())
                reject = 'reject' in receipt['version'] or state['fail_all']
            except FileNotFoundError:
                reject = False
            if reject:
                self.send_response(503)
                self.end_headers()
                return
            status, content = http(18083, self.path)
            self.send_response(status)
            self.end_headers()
            self.wfile.write(content)
        def log_message(self, *args):
            pass
    for attempt in range(30):
        try:
            proxy = ThreadingHTTPServer(('127.0.0.1', 18080), FaultProxy)
            break
        except OSError:
            if attempt == 29:
                raise
            time.sleep(0.1)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    try:
        failed = deliver(fixture(version='0.1.0-preview.reject'))
        assert_true(failed.returncode != 0 and not (serving / 'current').exists(), 'Failed first activation was not removed')
        assert_true(not (serving / 'deploy.lock').exists(), 'Reconciled first failure left lock')
        passed = deliver(fixture())
        assert_true(passed.returncode == 0, 'Actual SSH static delivery failed: ' + passed.stderr.decode(errors='replace')[-500:])
        receipt = json.loads(passed.stdout)
        assert_true(receipt['verifiedLocal'] is True, 'Local health was not verified')
        previous = (serving / 'current').resolve()
        assert_true(http(18083, '/index.html')[1] == b'qualified index.html', 'Wrong served bytes')
        assert_true(http(18083, '/activation.json')[0] == 404, 'Internal receipt exposed')
        assert_true(http(18081, '/index.html', {'Host': 'freeflight-staging.dockpipe.com',
                    'X-DockPipe-Client-IP': '192.0.2.7'})[0] == 200, 'Approved private ingress rejected')
        failed = deliver(fixture(version='0.1.0-preview.reject'))
        assert_true(failed.returncode != 0 and (serving / 'current').resolve() == previous, 'Upgrade rollback failed')
        assert_true(not (serving / 'deploy.lock').exists(), 'Verified rollback left lock')
        assert_true(state['observed'][-1] == previous and any(p != previous for p in state['observed']), 'Candidate/rollback not exercised')
        state['fail_all'] = True
        failed = deliver(fixture(version='0.1.0-preview.reject'))
        assert_true(failed.returncode != 0 and (serving / 'deploy.lock').exists(), 'Failed rollback did not retain lock')
        assert_true(deliver(fixture()).returncode != 0, 'Unreconciled lock allowed another delivery')
        assert_true(http(18082)[1] == b'existing-site-untouched', 'Existing site changed during failure paths')
        assert_true(all(hashlib.sha256(p.read_bytes()).hexdigest() == d for p, d in original.items()), 'Existing policy changed')
        print('PASS: real bootstrap/idempotence, restricted SSH, static activation, private ingress, rollback, lock retention and existing-site preservation')
    finally:
        proxy.shutdown()
        proxy.server_close()
        run(['systemctl', 'stop', 'freeflight-release-sshd'])
        # No test keys, host keys or system journal are uploaded as artifacts.
        key.unlink()
        key.with_suffix('.pub').unlink()


if __name__ == '__main__':
    main()
