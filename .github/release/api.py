# SPDX-License-Identifier: Apache-2.0
"""GitHub Actions API glue; all reusable release validation is owned by DockPipe."""
import hashlib
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workflows/release.verify/assets'))
from policy import PLATFORMS, EXTRAS, REPO, check_run, require, platforms, release_context

API = 'https://api.github.com/repos/' + REPO


class Redirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        parsed = urlparse(url)
        require(parsed.scheme == 'https' and (parsed.hostname in {'api.github.com', 'release-assets.githubusercontent.com'}
                or parsed.hostname.endswith('.blob.core.windows.net')), 'Unapproved GitHub download redirect')
        result = super().redirect_request(request, fp, code, message, headers, url)
        result.remove_header('Authorization')
        return result


def request(path, method='GET', data=None, binary=False, asset=False):
    url = path if path.startswith('https://') else API + path
    require(urlparse(url).hostname in {'api.github.com', 'uploads.github.com'}, 'Unexpected API host')
    # Binary selects response handling, not the media type of the GitHub API request.
    headers = {'Accept': 'application/octet-stream' if asset else 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2026-03-10'}
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json'
    elif hasattr(data, 'fileno'):
        headers.update({'Content-Type': 'application/octet-stream', 'Content-Length': str(os.fstat(data.fileno()).st_size)})
    query = Request(url, data=data, headers=headers, method=method)
    query.add_unredirected_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    response = build_opener(Redirect()).open(query, timeout=120)
    if binary:
        return response
    with response:
        return json.load(response)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def promotion_evidence(pulls):
    """Recover merge commits from timeline events under the pinned 2026 API."""
    result = []
    for pull in pulls:
        base, head = pull.get('base', {}), pull.get('head', {})
        if not pull.get('merged_at') or (base.get('ref'), head.get('ref')) not in {
                ('dev', 'js/dev'), ('staging', 'dev'), ('master', 'staging')} or any(
                (side.get('repo') or {}).get('full_name') != REPO for side in (base, head)):
            continue
        number = pull.get('number')
        require(type(number) is int and number > 0, 'Invalid promotion PR number')
        events = []
        for page in range(1, 11):
            batch = request('/issues/' + str(number) + '/timeline?per_page=100&page=' + str(page))
            require(isinstance(batch, list), 'Invalid promotion timeline response')
            events.extend(event for event in batch if event.get('event') == 'merged')
            if len(batch) < 100:
                break
        else:
            raise ValueError('Promotion timeline exceeds bounded query; review manually')
        require(len(events) == 1, 'Exactly one authoritative merge event required')
        event = events[0]
        sha = event.get('commit_id', '')
        require(isinstance(sha, str) and re.fullmatch('[a-f0-9]{40}', sha)
                and event.get('commit_url') == API + '/commits/' + sha,
                'Merge event commit or repository mismatch')
        # GitHub records the timeline event separately from merging the PR.
        # Retain a conservative audit bound, not exact-second identity.
        try:
            merged_at = datetime.strptime(pull['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
            recorded_at = datetime.strptime(event['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Invalid promotion timestamp') from error
        require(0 <= (recorded_at - merged_at).total_seconds() <= 60,
                'Merge event recording delay exceeds audit bound')
        commit = request('/commits/' + sha)
        require(isinstance(commit, dict), 'Invalid promotion commit response')
        parents = commit.get('parents', [])
        require(commit.get('sha') == sha and commit.get('url') == API + '/commits/' + sha
                and isinstance(parents, list) and len(parents) == 2
                and all(isinstance(parent, dict) and isinstance(parent.get('sha'), str)
                        and re.fullmatch('[a-f0-9]{40}', parent['sha'])
                        and parent.get('url') == API + '/commits/' + parent['sha'] for parent in parents)
                and parents[1]['sha'] == head.get('sha') and parents[0]['sha'] != parents[1]['sha'],
                'Promotion merge commit does not corroborate the exact PR head')
        # 2026-03-10 removed merge_commit_sha from every PR response. Keep the
        # policy's internal normalized field plus its authoritative source evidence.
        result.append({**pull, 'merge_commit_sha': sha, 'merge_event': event,
                       'merge_commit_evidence': {'sha': sha, 'url': commit['url'], 'parents': parents}})
    return result


def extract_native_artifact(archive, directory, jammy=False):
    """Accept only native package files, including upload-artifact's packages/ root."""
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        require(0 < len(members) <= 16, 'Unexpected package artifact entries')
        seen = set()
        selected = []
        for member in members:
            name = member.filename.removeprefix('packages/')
            require((re.fullmatch(r'freeflight-[a-z0-9-]+\.(?:tar\.gz|mcpb)(?:\.sha256)?', name)
                     or (jammy and member.filename == 'jammy-compatibility.json'))
                    and name not in seen and not member.is_dir() and member.file_size <= 2 * 1024 ** 3
                    and (member.external_attr >> 16) & 0o170000 in (0, 0o100000), 'Unsafe artifact entry')
            seen.add(name)
            selected.append((member, name))
        # Validate the entire layout before writing any extracted files.
        for member, name in selected:
            with bundle.open(member) as stream, (directory / name).open('xb') as output:
                shutil.copyfileobj(stream, output)


def select():
    """Choose tested source bytes, never rebuild on the promotion merge."""
    channel, branch = release_context()
    require(channel == 'staging', 'Automatic selection is staging-only')
    target = os.environ['GITHUB_SHA']
    require(request('/git/ref/heads/' + branch)['object']['sha'] == target, 'Staging moved before selection')
    tree = subprocess.check_output(['git', 'rev-parse', target + '^{tree}'], text=True).strip()
    for page in range(1, 11):
        runs = request('/actions/workflows/ci.yml/runs?branch=js%2Fdev&event=push&status=completed&per_page=100&page=' + str(page))['workflow_runs']
        for run in runs:
            if run.get('conclusion') != 'success':
                continue
            source = check_run(run, '.github/workflows/ci.yml')
            if subprocess.run(['git', 'merge-base', '--is-ancestor', source, target], capture_output=True).returncode:
                continue
            if subprocess.check_output(['git', 'rev-parse', source + '^{tree}'], text=True).strip() == tree:
                with open(os.environ['GITHUB_ENV'], 'a') as output:
                    output.write('QUALIFICATION_RUN=' + str(run['id']) + '\n')
                print('Selected successful exact-tree qualification run ' + str(run['id']))
                return
        if len(runs) < 100:
            break
    raise ValueError('No successful exact-tree js/dev push qualification; promote qualified source first')


def collect():
    channel, branch = release_context()
    selected_platforms = platforms(channel)
    run_id = os.environ['QUALIFICATION_RUN']
    require(re.fullmatch('[1-9][0-9]*', run_id), 'Numeric qualification run ID required')
    run = request('/actions/runs/' + run_id)
    source = check_run(run, '.github/workflows/ci.yml')
    codeqls = request('/actions/workflows/codeql.yml/runs?event=push&head_sha=' + source + '&per_page=100')['workflow_runs']
    codeqls = [r for r in codeqls if r.get('conclusion') == 'success']
    require(codeqls, 'No successful exact-source CodeQL push run')
    codeql = max(codeqls, key=lambda r: r['id'])
    check_run(codeql, '.github/workflows/codeql.yml', source)
    master = request('/git/ref/heads/' + branch)['object']['sha']
    require(master == os.environ['GITHUB_SHA'], 'Master moved after dispatch')
    pulls = []
    for base in (('dev', 'staging') if channel == 'staging' else ('dev', 'staging', 'master')):
        for page in range(1, 11):
            batch = request('/pulls?state=closed&base=' + base + '&per_page=100&page=' + str(page))
            pulls.extend(batch)
            if len(batch) < 100:
                break
        else:
            raise ValueError('Promotion history exceeds bounded query; review manually')
    pulls = promotion_evidence(pulls)
    listing = request('/actions/runs/' + run_id + '/artifacts?per_page=100')
    require(listing['total_count'] <= 100, 'Unexpected artifact count')
    artifacts = [a for a in listing['artifacts'] if a['name'] in selected_platforms or a['name'] in EXTRAS]
    require(len(artifacts) == len(selected_platforms) + len(EXTRAS) and {a['name'] for a in artifacts} == set(selected_platforms) | EXTRAS, 'Missing/duplicate release artifacts')
    candidate = ROOT / 'bin/.local/release-candidate'
    candidate.mkdir(parents=True, exist_ok=False)
    for artifact in artifacts:
        require(not artifact['expired'] and artifact.get('workflow_run', {}).get('id') == run['id'], 'Expired or foreign artifact')
        expected = artifact.get('digest', '')
        require(re.fullmatch('sha256:[a-f0-9]{64}', expected), 'GitHub artifact digest required')
        directory = candidate / 'artifacts' / artifact['name']
        directory.mkdir(parents=True)
        archive = directory / 'download.zip'
        with request('/actions/artifacts/' + str(int(artifact['id'])) + '/zip', binary=True) as response, archive.open('wb') as output:
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                require(total <= 3 * 1024 ** 3, 'Oversized artifact download')
                output.write(block)
        require(digest(archive) == expected[7:], 'GitHub artifact archive digest mismatch')
        if artifact['name'] in EXTRAS:
            additional = candidate / 'additional'
            additional.mkdir(exist_ok=True)
            archive.rename(additional / (artifact['name'] + '.zip'))
            continue
        extract_native_artifact(archive, directory, jammy=artifact['name'] == 'preview-ubuntu-22.04-linux-x64')
        archive.unlink()
    (candidate / 'evidence.json').write_text(json.dumps({'run': run, 'codeql': codeql, 'master': master,
                                                       'pulls': pulls, 'artifacts': artifacts}, indent=2))
    with open(os.environ['GITHUB_ENV'], 'a') as output:
        output.write('FREEFLIGHT_RELEASE_CANDIDATE=' + str(candidate) + '\n')


def publish():
    require(os.environ.get('RELEASE_MODE') == 'publish', 'Explicit publish mode required')
    channel, branch = release_context()
    # Repeat all DockPipe gates immediately before writes; no rebuild or repacking.
    subprocess.run(['dockpipe', '--workflow', 'release.verify'], check=True)
    candidate = Path(os.environ['FREEFLIGHT_RELEASE_CANDIDATE'])
    verified = json.loads((candidate / 'verified.json').read_text())
    require(request('/git/ref/heads/' + branch)['object']['sha'] == verified['master'], 'Promoted branch moved during qualification')
    check_run(request('/actions/runs/' + str(verified['runId'])), '.github/workflows/ci.yml', verified['source'])
    check_run(request('/actions/runs/' + str(verified['codeqlRunId'])), '.github/workflows/codeql.yml', verified['source'])
    prepared = Path(verified['prepared'])
    report = json.loads((prepared / 'release-manifest.json').read_text())
    tag = report['tag']
    require(verified['channel'] == channel and verified['branch'] == branch, 'Release channel changed')
    if channel == 'production':
        require(re.fullmatch(r'\d+\.\d+\.\d+', report['version']), 'Production publication requires stable VERSION')
    files = [(Path(a['source']), a['sha256']) for a in report['artifacts']]
    files += [(Path(a['source']), a['sha256']) for a in report['additionalAssets']]
    files += [(prepared / name, digest(prepared / name)) for name in ('SHA256SUMS', 'release-manifest.json')]
    for endpoint in ('/releases/tags/' + tag, '/git/ref/tags/' + tag):
        try:
            request(endpoint)
        except HTTPError as error:
            require(error.code == 404, 'Could not establish release/tag absence')
        else:
            raise ValueError('Existing release/tag: stop and reconcile; never overwrite automatically')
    release = request('/releases', 'POST', {'tag_name': tag, 'target_commitish': verified['master'],
        'name': 'FreeFlight ' + ('staging ' if channel == 'staging' else '') + report['version'],
        'draft': True, 'prerelease': channel == 'staging', 'make_latest': 'false' if channel == 'staging' else 'true',
        'body': 'Complete native bundles qualified by CI run ' + str(verified['runId']) +
                ' and CodeQL run ' + str(verified['codeqlRunId']) + '. Source ' + verified['source'] +
                '. Promotion PRs: ' + ', '.join('#' + str(n) for n in verified['promotionPulls']) +
                '. No automatic MCP Registry publication. ' +
                ('Staging preview for testing; master is unchanged. Linux x64 uses the Ubuntu 22.04 baseline. '
                 'Archive version remains ' + report['version'] + '; the tag identifies the qualified run. '
                 'Use the matching archive and SHA256SUMS, extract separately, and configure trustedRoots for chosen source folders. '
                 'Actual private-project acceptance remains unverified.' if channel == 'staging' else '')})
    (candidate / 'publication-attempt.json').write_text(json.dumps({'releaseId': release['id'], 'tag': tag, 'status': 'draft-created'}, indent=2))
    for path, expected in files:
        require(digest(path) == expected, 'Local asset changed after qualification')
        with path.open('rb') as stream:
            asset = request('https://uploads.github.com/repos/' + REPO + '/releases/' + str(release['id']) + '/assets?name=' + quote(path.name), 'POST', stream)
        require(asset.get('state') == 'uploaded' and asset.get('digest') == 'sha256:' + expected,
                'Uploaded asset digest mismatch; draft retained for reconciliation')
    result = request('/releases/' + str(release['id']), 'PATCH',
                     {'draft': False, 'prerelease': channel == 'staging',
                      'make_latest': 'false' if channel == 'staging' else 'true'})
    require(result.get('draft') is False, 'Publication outcome uncertain; inspect existing release')
    print('GitHub Release published: ' + result['html_url'])
    (candidate / 'publication-attempt.json').write_text(json.dumps({'releaseId': release['id'], 'tag': tag, 'status': 'published', 'url': result['html_url']}, indent=2))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('release_tag=' + tag + '\nrelease_url=' + result['html_url'] + '\n')


if __name__ == '__main__':
    {'select': select, 'collect': collect, 'publish': publish}[sys.argv[1]]()
