"""Download a pinned validator and check authored configuration, never state or plans."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[3]
cloud = Path(os.environ['FREEFLIGHT_CLOUD_CHECKOUT']).resolve()
base = ROOT / 'bin/.local/terraform-validation'
base.mkdir(parents=True, exist_ok=True)
if platform.system() != 'Darwin' or platform.machine() != 'arm64':
    raise ValueError('This pinned local validator targets macOS ARM64')
archive = base / 'terraform_1.13.5_darwin_arm64.zip'
expected = '1bf942231235e7e1a4c38c6d7b820e54f526ac487f87d19f0c4a425c6ddb62cb'
if not archive.exists():
    with urlopen('https://releases.hashicorp.com/terraform/1.13.5/' + archive.name, timeout=60) as source:
        data = source.read(100 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Terraform download checksum mismatch')
    archive.write_bytes(data)
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise ValueError('Terraform cached checksum mismatch')
binary = base / 'terraform'
with zipfile.ZipFile(archive) as bundle:
    binary.write_bytes(bundle.read('terraform'))
binary.chmod(0o755)
workspace = Path(tempfile.mkdtemp(prefix='authored-', dir=base))
source = cloud / 'infra/terraform/digitalocean'
for path in source.glob('*.tf'):
    shutil.copyfile(path, workspace / path.name)
shutil.copyfile(source / '.terraform.lock.hcl', workspace / '.terraform.lock.hcl')
# Static file() inputs only: placeholder compiled payload is not a deployable artifact.
bootstrap = workspace / 'bootstrap'
bootstrap.mkdir()
for name in ('bootstrap.sh', 'receive-site.cjs', 'site-http.conf', 'release-sshd.conf', 'release-sshd.service'):
    (bootstrap / name).write_text('# schema-validation-only placeholder\n')
home = workspace / 'home'
home.mkdir()
environment = {'PATH': os.environ['PATH'], 'HOME': str(home), 'TF_IN_AUTOMATION': '1', 'CHECKPOINT_DISABLE': '1'}
# Terraform may add this platform's verified h1 hash to the scratch lock only.
for args in [('init', '-backend=false', '-input=false'), ('validate', '-no-color')]:
    subprocess.run([str(binary), '-chdir=' + str(workspace), *args], env=environment, check=True)
print('Authored Terraform schema validated; no backend, state, provider credentials, plan or apply used')
