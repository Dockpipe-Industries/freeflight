# SPDX-License-Identifier: Apache-2.0
import copy
import unittest
from policy import BOT, BOT_ID, dependency_changes, validate

REPO = 'Dockpipe-Industries/freeflight'
ACTION = '      - uses: actions/checkout@' + 'a' * 40 + ' # v4\n'
CHANGES = {'.github/workflows/ci.yml': (ACTION, ACTION.replace('a' * 40, 'b' * 40))}


def event():
    return {'pull_request': {'base': {'ref': 'dev', 'repo': {'full_name': REPO}},
                            'head': {'ref': 'dependabot/github_actions/dev/actions/checkout-7', 'repo': {'full_name': REPO}},
                            'user': {'login': BOT, 'id': BOT_ID, 'type': 'Bot'}}}


class PolicyTests(unittest.TestCase):
    def run_policy(self, value=None, actor=BOT, actor_id=BOT_ID, changes=None):
        return validate('pull_request', value or event(), REPO, actor, actor_id, CHANGES if changes is None else changes)

    def test_authentic_dependabot(self):
        self.assertIn('all qualification checks still required', self.run_policy())

    def test_real_dependabot_ecosystem_branch_names(self):
        e = event()
        e['pull_request']['head']['ref'] = 'dependabot/npm_and_yarn/workers/typescript/dev/typescript-5.9.4'
        changes = {'workers/typescript/package.json': ('{"dependencies":{"typescript":"5.9.3"}}', '{"dependencies":{"typescript":"5.9.4"}}')}
        self.assertIn('Authentic', self.run_policy(e, changes=changes))
        e['pull_request']['head']['ref'] = 'dependabot/npm/workers/typescript/dev/typescript-5.9.4'
        with self.assertRaises(ValueError): self.run_policy(e, changes=changes)
        e['pull_request']['head']['ref'] = 'dependabot/nuget/workers/roslyn/dev/Microsoft.Build.Locator-1.11.2'
        old = '<PackageReference Include="Microsoft.Build.Locator" Version="1.7.8" />'
        self.assertIn('Authentic', self.run_policy(e, changes={'workers/roslyn/FreeFlight.Roslyn.csproj': (old, old.replace('1.7.8', '1.11.2'))}))

    def test_ordinary_promotions(self):
        for base, head in [('dev', 'js/dev'), ('staging', 'dev'), ('master', 'staging')]:
            e = event(); e['pull_request']['base']['ref'] = base; e['pull_request']['head']['ref'] = head
            self.assertIn('Valid promotion', self.run_policy(e, actor='maintainer', actor_id=123))

    def test_invalid_identities(self):
        for actor, actor_id in [('maintainer', BOT_ID), (BOT, 123), ('dependabot', BOT_ID), ('', '')]:
            with self.subTest(actor=actor, actor_id=actor_id), self.assertRaises(ValueError):
                self.run_policy(actor=actor, actor_id=actor_id)
        for field, value in [('login', 'maintainer'), ('id', 123), ('type', 'User')]:
            e = event(); e['pull_request']['user'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.run_policy(e)

    def test_spoofed_heads_and_bases(self):
        for head in ['deps/dev-upload-artifact-7', 'feature', 'dependabot/unknown/x', 'dependabot/github_actions']:
            e = event(); e['pull_request']['head']['ref'] = head
            with self.subTest(head=head), self.assertRaises(ValueError): self.run_policy(e)
        for base in ['master', 'staging']:
            e = event(); e['pull_request']['base']['ref'] = base
            with self.subTest(base=base), self.assertRaises(ValueError): self.run_policy(e)
        for side in ['base', 'head']:
            e = event(); e['pull_request'][side]['repo']['full_name'] = 'attacker/freeflight'
            with self.subTest(side=side), self.assertRaises(ValueError): self.run_policy(e)

    def test_no_diff_or_unrelated_files(self):
        for changes in [{}, {'src/main.cpp': ('old', 'new')}, {**CHANGES, 'README.md': ('old', 'new')}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.run_policy(changes=changes)
        with self.assertRaises(ValueError): validate('pull_request', event(), REPO, BOT, BOT_ID)

    def test_workflow_commands_permissions_and_identity_cannot_change(self):
        for new in [ACTION + '      - run: arbitrary\n', ACTION.replace('actions/checkout', 'attacker/checkout'),
                    ACTION.replace('a' * 40, 'main'), ACTION + 'permissions: write-all\n', ACTION * 2]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                self.run_policy(changes={'.github/workflows/ci.yml': (ACTION, new)})

    def test_action_and_package_relocation_rejected(self):
        other = ACTION.replace('actions/checkout', 'vendor/publish')
        old = ACTION + '        with:\n          token: first\n' + other + '        with:\n          token: second\n'
        new = other + '        with:\n          token: first\n' + ACTION + '        with:\n          token: second\n'
        with self.assertRaises(ValueError): self.run_policy(changes={'.github/workflows/ci.yml': (old, new)})
        a = '<PackageReference Include="First" Version="1.0.0" />\n'
        b = a.replace('First', 'Second')
        with self.assertRaises(ValueError): dependency_changes('nuget', {'workers/roslyn/FreeFlight.Roslyn.csproj': (a + '</ItemGroup>\n<ItemGroup>\n' + b, b + '</ItemGroup>\n<ItemGroup>\n' + a)})

    def test_npm_versions_only(self):
        changes = {'workers/typescript/package.json': ('{"dependencies":{"typescript":"5.9.3"}}', '{"dependencies":{"typescript":"7.0.2"}}'),
                   'workers/typescript/package-lock.json': ('{}', '{"lockfileVersion":3}')}
        dependency_changes('npm', changes)
        for new in ['{"dependencies":{"typescript":"file:/tmp/x"}}', '{"scripts":{"install":"bad"},"dependencies":{"typescript":"7.0.2"}}', '{"dependencies":{"other":"1.0.0"}}']:
            altered = copy.deepcopy(changes); altered['workers/typescript/package.json'] = (changes['workers/typescript/package.json'][0], new)
            with self.subTest(new=new), self.assertRaises(ValueError): dependency_changes('npm', altered)

    def test_nuget_version_only(self):
        old = '    <PackageReference Include="Microsoft.Build.Locator" Version="1.7.8" />'
        new = old.replace('1.7.8', '1.11.2')
        dependency_changes('nuget', {'workers/roslyn/FreeFlight.Roslyn.csproj': (old, new)})
        for altered in [new + '\n<Target Name="bad" />', new.replace('Microsoft.Build.Locator', 'Other'), new.replace(' />', ' ExcludeAssets="runtime" />')]:
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                dependency_changes('nuget', {'workers/roslyn/FreeFlight.Roslyn.csproj': (old, altered)})

    def test_added_removed_and_lock_only_rejected(self):
        for changes in [{'.github/workflows/ci.yml': (None, ACTION)}, {'.github/workflows/ci.yml': (ACTION, None)}]:
            with self.assertRaises(ValueError): self.run_policy(changes=changes)
        with self.assertRaises(ValueError): dependency_changes('npm', {'workers/typescript/package-lock.json': ('{}', '{}')})

    def test_local_events(self):
        for name in ['push', 'workflow_dispatch', 'workflow_call']:
            self.assertIn('No pull-request', validate(name, {}, REPO, '', ''))
        with self.assertRaises(ValueError): validate('pull_request_target', {}, REPO, BOT, BOT_ID)


if __name__ == '__main__':
    unittest.main()
