# SPDX-License-Identifier: Apache-2.0
"""GitHub Actions API glue; all reusable release validation is owned by DockPipe."""
import hashlib
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
from policy import PLATFORMS, EXTRAS, REPO, check_run, require

API = 'https://api.github.com/repos/' + REPO


class Redirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        parsed = urlparse(url)
        require(parsed.scheme == 'https' and (parsed.hostname in {'api.github.com', 'release-assets.githubusercontent.com'}
                or parsed.hostname.endswith('.blob.core.windows.net')), 'Unapproved GitHub download redirect')
        result = super().redirect_request(request, fp, code, message, headers, url)
        result.remove_header('Authorization')
        return result


def request(path, method='GET', data=None, binary=False):
    url = path if path.startswith('https://') else API + path
    require(urlparse(url).hostname in {'api.github.com', 'uploads.github.com'}, 'Unexpected API host')
    # Binary selects response handling, not the media type of the GitHub API request.
    headers = {'Accept': 'application/vnd.github+json',
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
                and event.get('created_at') == pull['merged_at']
                and event.get('commit_url') == API + '/commits/' + sha,
                'Merge event commit, repository or timestamp mismatch')
        # 2026-03-10 removed merge_commit_sha from every PR response. Keep the
        # policy's internal normalized field plus its authoritative source evidence.
        result.append({**pull, 'merge_commit_sha': sha, 'merge_event': event})
    return result


def extract_native_artifact(archive, directory):
    """Accept only native package files, including upload-artifact's packages/ root."""
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        require(0 < len(members) <= 16, 'Unexpected package artifact entries')
        seen = set()
        selected = []
        for member in members:
            name = member.filename.removeprefix('packages/')
            require(re.fullmatch(r'freeflight-[a-z0-9-]+\.(?:tar\.gz|mcpb)(?:\.sha256)?', name)
                    and name not in seen and not member.is_dir() and member.file_size <= 2 * 1024 ** 3
                    and (member.external_attr >> 16) & 0o170000 in (0, 0o100000), 'Unsafe artifact entry')
            seen.add(name)
            selected.append((member, name))
        # Validate the entire layout before writing any extracted files.
        for member, name in selected:
            with bundle.open(member) as stream, (directory / name).open('xb') as output:
                shutil.copyfileobj(stream, output)


def collect():
    run_id = os.environ['QUALIFICATION_RUN']
    require(re.fullmatch('[1-9][0-9]*', run_id), 'Numeric qualification run ID required')
    run = request('/actions/runs/' + run_id)
    source = check_run(run, '.github/workflows/ci.yml')
    codeqls = request('/actions/workflows/codeql.yml/runs?event=push&head_sha=' + source + '&per_page=100')['workflow_runs']
    codeqls = [r for r in codeqls if r.get('conclusion') == 'success']
    require(codeqls, 'No successful exact-source CodeQL push run')
    codeql = max(codeqls, key=lambda r: r['id'])
    check_run(codeql, '.github/workflows/codeql.yml', source)
    master = request('/git/ref/heads/master')['object']['sha']
    require(master == os.environ['GITHUB_SHA'], 'Master moved after dispatch')
    pulls = []
    for base in ('dev', 'staging', 'master'):
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
    artifacts = [a for a in listing['artifacts'] if a['name'].startswith('native-') or a['name'] in EXTRAS]
    require(len(artifacts) == len(PLATFORMS) + len(EXTRAS) and {a['name'] for a in artifacts} == set(PLATFORMS) | EXTRAS, 'Missing/duplicate release artifacts')
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
        extract_native_artifact(archive, directory)
        archive.unlink()
    (candidate / 'evidence.json').write_text(json.dumps({'run': run, 'codeql': codeql, 'master': master,
                                                       'pulls': pulls, 'artifacts': artifacts}, indent=2))
    with open(os.environ['GITHUB_ENV'], 'a') as output:
        output.write('FREEFLIGHT_RELEASE_CANDIDATE=' + str(candidate) + '\n')


def publish():
    require(os.environ.get('RELEASE_MODE') == 'publish', 'Explicit publish mode required')
    require(os.environ.get('GITHUB_REF') == 'refs/heads/master' and os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and os.environ.get('GITHUB_REPOSITORY') == REPO, 'Publication requires canonical master dispatch')
    # Repeat all DockPipe gates immediately before writes; no rebuild or repacking.
    subprocess.run(['dockpipe', '--workflow', 'release.verify'], check=True)
    candidate = Path(os.environ['FREEFLIGHT_RELEASE_CANDIDATE'])
    verified = json.loads((candidate / 'verified.json').read_text())
    require(request('/git/ref/heads/master')['object']['sha'] == verified['master'], 'Master moved during qualification')
    check_run(request('/actions/runs/' + str(verified['runId'])), '.github/workflows/ci.yml', verified['source'])
    check_run(request('/actions/runs/' + str(verified['codeqlRunId'])), '.github/workflows/codeql.yml', verified['source'])
    prepared = Path(verified['prepared'])
    report = json.loads((prepared / 'release-manifest.json').read_text())
    tag = report['tag']
    for endpoint in ('/releases/tags/' + tag, '/git/ref/tags/' + tag):
        try:
            request(endpoint)
        except HTTPError as error:
            require(error.code == 404, 'Could not establish release/tag absence')
        else:
            raise ValueError('Existing release/tag: stop and reconcile; never overwrite automatically')
    release = request('/releases', 'POST', {'tag_name': tag, 'target_commitish': verified['master'],
        'name': 'FreeFlight ' + report['version'], 'draft': True, 'prerelease': '-' in report['version'],
        'body': 'Complete native bundles qualified by CI run ' + str(verified['runId']) +
                ' and CodeQL run ' + str(verified['codeqlRunId']) + '. Source ' + verified['source'] +
                '. Promotion PRs: ' + ', '.join('#' + str(n) for n in verified['promotionPulls']) +
                '. No automatic MCP Registry publication.'})
    (candidate / 'publication-attempt.json').write_text(json.dumps({'releaseId': release['id'], 'tag': tag, 'status': 'draft-created'}, indent=2))
    files = [(Path(a['source']), a['sha256']) for a in report['artifacts']]
    files += [(Path(a['source']), a['sha256']) for a in report['additionalAssets']]
    files += [(prepared / name, digest(prepared / name)) for name in ('SHA256SUMS', 'release-manifest.json')]
    for path, expected in files:
        require(digest(path) == expected, 'Local asset changed after qualification')
        with path.open('rb') as stream:
            asset = request('https://uploads.github.com/repos/' + REPO + '/releases/' + str(release['id']) + '/assets?name=' + quote(path.name), 'POST', stream)
        require(asset.get('state') == 'uploaded' and asset.get('digest') == 'sha256:' + expected,
                'Uploaded asset digest mismatch; draft retained for reconciliation')
    result = request('/releases/' + str(release['id']), 'PATCH', {'draft': False})
    require(result.get('draft') is False, 'Publication outcome uncertain; inspect existing release')
    print('GitHub Release published: ' + result['html_url'])
    (candidate / 'publication-attempt.json').write_text(json.dumps({'releaseId': release['id'], 'tag': tag, 'status': 'published', 'url': result['html_url']}, indent=2))


if __name__ == '__main__':
    {'collect': collect, 'publish': publish}[sys.argv[1]]()
