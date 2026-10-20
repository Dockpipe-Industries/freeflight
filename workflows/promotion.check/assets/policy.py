# SPDX-License-Identifier: Apache-2.0
"""Read-only CI policy; GitHub identity comes from its event and runner environment."""
import difflib
import json
import os
import re
import subprocess
from pathlib import Path

BOT_ID = 49699333
BOT = 'dependabot[bot]'
PROMOTIONS = {'dev': 'js/dev', 'staging': 'dev', 'master': 'staging'}
PATHS = {
    'npm': {'workers/typescript/package.json', 'workers/typescript/package-lock.json'},
    'nuget': {'workers/roslyn/FreeFlight.Roslyn.csproj', 'workers/roslyn/packages.lock.json'},
    'github_actions': {'.github/workflows/ci.yml', '.github/workflows/codeql.yml', '.github/workflows/release.yml'},
}


def require(value, message):
    if not value:
        raise ValueError(message)


def changed_lines(old, new):
    removed, added = [], []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        if line.startswith('- '):
            removed.append(line[2:])
        elif line.startswith('+ '):
            added.append(line[2:])
    return removed, added


def dependency_changes(ecosystem, changes):
    require(changes and set(changes) <= PATHS[ecosystem], 'Unexpected dependency change paths')
    for path, (old, new) in changes.items():
        require(old is not None and new is not None, 'Dependency files must already exist')
        if ecosystem == 'github_actions':
            removed, added = changed_lines(old, new)
            pattern = r'(\s*(?:- )?uses: [A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)@[a-f0-9]{40}(?:\s+# [^\r\n]*)?'
            def identities(lines):
                matches = [re.fullmatch(pattern, line) for line in lines]
                require(matches and all(matches), 'Only pinned action version replacements are allowed')
                return [m.group(1) for m in matches]
            identities(removed); identities(added)
            def normalize(text):
                return [re.fullmatch(pattern, line).group(1) if re.fullmatch(pattern, line) else line for line in text.splitlines()]
            require(normalize(old) == normalize(new), 'Action identity, position or workflow structure changed')
        elif path.endswith('/package.json'):
            before, after = json.loads(old), json.loads(new)
            require(isinstance(before, dict) and isinstance(after, dict), 'Invalid package manifest')
            changed = False
            for field in ('dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'):
                left, right = before.pop(field, {}), after.pop(field, {})
                require(isinstance(left, dict) and isinstance(right, dict) and left.keys() == right.keys(), 'Dependency identities changed')
                require(all(isinstance(v, str) and re.fullmatch(r'[~^]?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?', v) for v in [*left.values(), *right.values()]), 'Only registry version replacements are allowed')
                changed |= left != right
            require(before == after and changed, 'Nondependency package metadata changed')
        elif path.endswith('.csproj'):
            removed, added = changed_lines(old, new)
            pattern = r'(\s*<PackageReference Include="[A-Za-z0-9_.-]+" Version=")[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?("[^<>]*/>\s*)'
            def identities(lines):
                matches = [re.fullmatch(pattern, line) for line in lines]
                require(matches and all(matches), 'Only PackageReference version replacements are allowed')
                return sorted((m.group(1), m.group(2)) for m in matches)
            identities(removed); identities(added)
            def normalize(text):
                return [(m.group(1) + m.group(2)) if (m := re.fullmatch(pattern, line)) else line for line in text.splitlines()]
            require(normalize(old) == normalize(new), 'Package identity, position or build policy changed')
        else:
            require(isinstance(json.loads(old), dict) and isinstance(json.loads(new), dict), 'Invalid dependency lock')
    manifest = {'npm': 'workers/typescript/package.json', 'nuget': 'workers/roslyn/FreeFlight.Roslyn.csproj'}
    if ecosystem in manifest:
        require(manifest[ecosystem] in changes, 'Lock-only changes require ordinary development review')


def validate(event_name, event, repository, actor, actor_id, changes=None):
    if event_name != 'pull_request':
        require(event_name in {'push', 'workflow_dispatch', 'workflow_call'}, 'Unsupported event')
        return 'No pull-request promotion requested'
    pr = event['pull_request']
    base, head = pr['base'], pr['head']
    require(base['repo']['full_name'] == repository, 'Foreign base repository')
    if base['ref'] not in PROMOTIONS:
        return 'No protected-branch promotion requested'
    require(head['repo']['full_name'] == repository, 'Promotion requires same-repository head')
    if head['ref'] == PROMOTIONS[base['ref']]:
        return f"Valid promotion: {head['ref']} -> {base['ref']}"
    require(base['ref'] == 'dev', 'Dependency exception is dev-only')
    require(actor == BOT and str(actor_id) == str(BOT_ID), 'Dependency event must originate from Dependabot')
    user = pr['user']
    require(user.get('login') == BOT and user.get('id') == BOT_ID and user.get('type') == 'Bot', 'PR author is not authentic Dependabot')
    parts = head['ref'].split('/')
    require(len(parts) >= 3 and parts[0] == 'dependabot' and parts[1] in PATHS, 'Unexpected Dependabot branch')
    require(changes is not None, 'Dependency diff is required')
    dependency_changes(parts[1], changes)
    return 'Authentic dependency-only Dependabot proposal to dev; all qualification checks still required'


def git(*args):
    return subprocess.check_output(['git', *args], timeout=30)


def changes_for(pr):
    base, head = pr['base']['sha'], pr['head']['sha']
    require(all(re.fullmatch('[a-f0-9]{40}', sha) for sha in (base, head)), 'Invalid event commit')
    ancestor = git('merge-base', base, head).decode().strip()
    names = git('diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', ancestor, head).decode().split('\0')
    names = [name for name in names if name]
    require(0 < len(names) <= 20, 'Unexpected dependency diff size')
    allowed = set().union(*PATHS.values())
    require(set(names) <= allowed, 'Unrelated files in dependency proposal')
    changes = {}
    for name in names:
        contents = []
        for sha in (ancestor, head):
            entry = git('ls-tree', sha, '--', name).decode()
            require(entry.startswith('100644 blob '), 'Dependency file added, removed or mode changed')
            blob = git('show', sha + ':' + name)
            require(len(blob) <= 4 * 1024 * 1024, 'Oversized dependency file')
            contents.append(blob.decode('utf-8'))
        changes[name] = tuple(contents)
    return changes


def main():
    name = os.environ['GITHUB_EVENT_NAME']
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    repo = os.environ['GITHUB_REPOSITORY']
    changes = None
    if name == 'pull_request':
        pr = event['pull_request']
        if pr['base']['ref'] == 'dev' and pr['head']['ref'] != 'js/dev':
            changes = changes_for(pr)
    print(validate(name, event, repo, os.environ.get('GITHUB_ACTOR', ''), os.environ.get('GITHUB_ACTOR_ID', ''), changes))


if __name__ == '__main__':
    main()
