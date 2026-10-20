# SPDX-License-Identifier: Apache-2.0
"""Offline ABI and clean-runtime policy regressions; never start Docker."""
import importlib.util
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('jammy_check', Path(__file__).with_name('check.py'))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class CompatibilityTests(unittest.TestCase):
    def test_consumer_requirements_ignore_exported_definitions(self):
        output = "Version definition section '.gnu.version_d' contains 1 entry:\n Name: GLIBC_2.99\n"
        output += "Version needs section '.gnu.version_r' contains 4 entries:\n"
        output += ' Name: GLIBC_2.35\n Name: GLIBC_2.2.5\n Name: GLIBCXX_3.4.30\n Name: CXXABI_1.3.13\n'
        self.assertEqual(check.version_needs(output), {'GLIBC': '2.35', 'GLIBCXX': '3.4.30', 'CXXABI': '1.3.13'})

    def test_rejects_actual_noble_requirements_and_unknown_private_abi(self):
        for name in ('GLIBC_2.38', 'GLIBCXX_3.4.32', 'CXXABI_1.3.14', 'GLIBC_PRIVATE'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                check.version_needs('Version needs section\n Name: GLIBC_2.2.5\n Name: ' + name)

    def test_missing_consumer_requirements_fail_closed(self):
        for output in ('No version information found', 'Version definition section\n Name: GLIBC_2.35',
                       'Version needs section\n Name: OTHER_1.0'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                check.version_needs(output)

    def test_clean_container_uses_only_bundle_and_cleans_unique_image(self):
        self.check_clean_container('ubuntu22', check.IMAGE, 'libicu70 libssl3 libstdc++6', '/usr/bin/dpkg-query')

    def test_fedora_uses_same_isolated_semantics_with_rpm_inventory(self):
        self.check_clean_container('fedora44', check.FEDORA_IMAGE, 'openssl-libs libstdc++ tzdata zlib-ng-compat', '/usr/bin/rpm')

    def test_unknown_runtime_profile_fails_before_docker(self):
        with patch.object(check.subprocess, 'run') as run, self.assertRaises(ValueError):
            check.clean_runtime(Path('/unused'), 'custom-image')
        run.assert_not_called()

    def check_clean_container(self, profile, image, packages, query):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            client = root / 'bin/.local/client'
            client.mkdir(parents=True)
            (client / 'client.mjs').write_text('// fixture')
            archive = root / 'bundle.tar.gz'
            with tarfile.open(archive, 'w:gz'):
                pass
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                if args[1] == 'build':
                    dockerfile = (Path(args[-1]) / 'Dockerfile').read_text()
                    self.assertIn(image, dockerfile)
                    self.assertIn(packages, dockerfile)
                    self.assertNotIn('apt-get install -y node', dockerfile)
                    if profile == 'fedora44':
                        self.assertIn('dnf -y --setopt=install_weak_deps=False install', dockerfile)
                        self.assertNotIn('apt-get', dockerfile)
                return subprocess.CompletedProcess(args, 0, 'Official MCP SDK verified packaged TS definition/references/diagnostics, JS symbol, C# diagnostics/symbol and engine capabilities\n')
            with patch.object(check, 'ROOT', root), patch.object(check.subprocess, 'run', side_effect=run), \
                    patch.object(check.subprocess, 'check_output', return_value='library=1.0\n') as inventory:
                receipt = check.clean_runtime(archive, profile)
            query_args = inventory.call_args.args[0]
            self.assertEqual(query_args[query_args.index('--entrypoint') + 1], query)
            self.assertEqual(receipt['packages'], ['library=1.0'])
            self.assertEqual(receipt['baseImage'], image)
            invocation = calls[1]
            self.assertEqual(invocation[invocation.index('--network') + 1], 'none')
            self.assertIn('--read-only', invocation)
            self.assertEqual(invocation[invocation.index('--user') + 1], '65532:65532')
            self.assertEqual(invocation[invocation.index('--entrypoint') + 1], '/opt/freeflight/lib/freeflight/node/bin/node')
            self.assertFalse(any(arg in invocation for arg in ('--mount', '-v', '--privileged')))
            self.assertEqual(calls[-1][:4], ['docker', 'image', 'rm', '--force'])
            self.assertEqual(calls[0][calls[0].index('--tag') + 1], calls[-1][-1])
            self.assertFalse(receipt['hostRuntimeMounted'])


if __name__ == '__main__':
    unittest.main()
