"""Operator bootstrap; CI may exercise it only inside the guarded disposable-host fixture."""
import base64
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys


def require(value, message):
    if not value:
        raise ValueError(message)


def configuration(networks):
    require(isinstance(networks, list) and networks, "Operator networks required")
    ranges = [str(ipaddress.IPv4Network(value, strict=True)) for value in networks]
    allowlist = "\n".join("    " + value + " 1;" for value in ranges)
    nginx = '''geo $http_x_dockpipe_client_ip $freeflight_operator {
    default 0;
ALLOWLIST
}
server {
    listen 127.0.0.1:18080;
    server_name freeflight-staging.dockpipe.com;
    root /srv/freeflight-staging/current;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Robots-Tag noindex always;
    location = /healthz { default_type text/plain; return 200 "ok\\n"; }
    location = / { limit_except GET { deny all; } try_files /index.html =404; }
    location ~ ^/(index\\.html|review\\.html|styles\\.css|loader\\.js|qtloader\\.js|freeflight-site\\.(js|wasm)|release\\.json|robots\\.txt|NOTICES\\.txt)$ {
        limit_except GET { deny all; }
        try_files $uri =404;
    }
    location / { return 404; }
}
server {
    listen 127.0.0.1:18081;
    server_name freeflight-staging.dockpipe.com;
    if ($host != freeflight-staging.dockpipe.com) { return 404; }
    if ($freeflight_operator = 0) { return 403; }
    location / { proxy_pass http://127.0.0.1:18080; }
}
'''.replace("ALLOWLIST", allowlist)
    ssh = '''Port 2223
AddressFamily inet
ListenAddress 0.0.0.0
HostKey /etc/ssh/ssh_host_ed25519_key
PidFile /run/freeflight-release-sshd.pid
AllowUsers freeflight-release
AuthorizedKeysFile /etc/ssh/authorized_keys/freeflight-release
AuthenticationMethods publickey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PermitEmptyPasswords no
UsePAM yes
StrictModes yes
DisableForwarding yes
PermitTTY no
PermitUserEnvironment no
PermitUserRC no
ForceCommand /usr/local/libexec/freeflight-site-activate
MaxSessions 1
MaxAuthTries 3
MaxStartups 10:30:30
LoginGraceTime 20
'''
    service = '''[Unit]
Description=FreeFlight restricted static release receiver
After=network.target
[Service]
ExecStart=/usr/sbin/sshd -D -f /etc/ssh/freeflight-release.conf
Restart=on-failure
[Install]
WantedBy=multi-user.target
'''
    return nginx, ssh, service


def install(payload, run=subprocess.run):
    require(os.geteuid() == 0, "Operator bootstrap requires root")
    import pwd
    require(set(payload) == {"publicKey", "networks", "receiver", "entrypoint"}, "Unexpected bootstrap fields")
    require(re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}", payload["publicKey"]), "Invalid release public key")
    nginx, ssh, service = configuration(payload["networks"])
    marker = Path("/var/lib/freeflight-bootstrap")
    owned = marker / "owner.json"
    managed = [Path(p) for p in ["/usr/local/lib/freeflight", "/etc/freeflight-site", "/srv/freeflight-staging",
               "/usr/local/libexec/freeflight-site-activate", "/etc/nginx/conf.d/freeflight-staging.conf",
               "/etc/ssh/freeflight-release.conf", "/etc/ssh/authorized_keys/freeflight-release",
               "/etc/systemd/system/freeflight-release-sshd.service"]]
    require(not marker.is_symlink(), "Unsafe bootstrap marker")
    if owned.exists():
        require(json.loads(owned.read_text()) == {"product": "freeflight", "environment": "staging"}, "Foreign bootstrap owner")
    else:
        require(not any(p.exists() or p.is_symlink() for p in managed), "Unowned FreeFlight paths already exist")
        try:
            pwd.getpwnam("freeflight-release")
        except KeyError:
            pass
        else:
            raise ValueError("Unowned FreeFlight account already exists")
        for port in (2223, 18080, 18081):
            with socket.socket() as listener:
                listener.bind(("0.0.0.0" if port == 2223 else "127.0.0.1", port))
        marker.mkdir(mode=0o700)
        owned.write_text(json.dumps({"product": "freeflight", "environment": "staging"}))
    run(["nginx", "-t"], check=True, capture_output=True)
    try:
        account = pwd.getpwnam("freeflight-release")
    except KeyError:
        run(["useradd", "--system", "--home-dir", "/srv/freeflight-staging", "--shell", "/bin/sh", "freeflight-release"], check=True)
        account = pwd.getpwnam("freeflight-release")
    require(account.pw_uid != 0 and account.pw_dir == "/srv/freeflight-staging" and account.pw_shell == "/bin/sh", "Unexpected release account")
    for directory in ("/srv/freeflight-staging", "/srv/freeflight-staging/releases"):
        path = Path(directory)
        require(not path.is_symlink(), "Unsafe serving path")
        path.mkdir(exist_ok=True, mode=0o755)
        os.chown(path, account.pw_uid, account.pw_gid)
        path.chmod(0o755)
    files = {
        "/usr/local/lib/freeflight/receive.py": (base64.b64decode(payload["receiver"], validate=True), 0o644),
        "/usr/local/libexec/freeflight-site-activate": (base64.b64decode(payload["entrypoint"], validate=True), 0o755),
        "/etc/freeflight-site/receiver.json": (json.dumps({"environment": "staging", "activationEnabled": True,
            "root": "/srv/freeflight-staging", "loopbackPort": 18080}).encode(), 0o644),
        "/etc/nginx/conf.d/freeflight-staging.conf": (nginx.encode(), 0o644),
        "/etc/ssh/freeflight-release.conf": (ssh.encode(), 0o644),
        "/etc/ssh/authorized_keys/freeflight-release": (("restrict " + payload["publicKey"] + "\n").encode(), 0o644),
        "/etc/systemd/system/freeflight-release-sshd.service": (service.encode(), 0o644),
    }
    for name, (data, mode) in files.items():
        path = Path(name)
        require(not path.is_symlink(), "Unsafe managed file")
        path.parent.mkdir(parents=True, exist_ok=True)
        require(path.parent.resolve() == path.parent and path.parent.stat().st_uid == 0
                and path.parent.stat().st_mode & 0o022 == 0, "Unsafe configuration directory")
        with path.open("wb") as output:
            output.write(data)
        os.chown(path, 0, 0)
        path.chmod(mode)
    run(["/usr/sbin/sshd", "-t", "-f", "/etc/ssh/freeflight-release.conf"], check=True, capture_output=True)
    effective = run(["/usr/sbin/sshd", "-T"], check=True, capture_output=True, text=True).stdout
    require("allowusers platform-admin" in effective.splitlines(), "Administrator listener isolation changed")
    run(["nginx", "-t"], check=True, capture_output=True)
    run(["systemctl", "daemon-reload"], check=True)
    run(["systemctl", "enable", "--now", "freeflight-release-sshd"], check=True)
    run(["systemctl", "reload", "nginx"], check=True)
    print("FreeFlight static receiver installed; public readiness and CI enablement remain pending")


if __name__ == "__main__":
    try:
        install(json.load(sys.stdin))
    except Exception:
        print("FreeFlight bootstrap failed; inspect retained state before retrying.", file=sys.stderr)
        sys.exit(1)
