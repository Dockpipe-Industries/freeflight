# SPDX-License-Identifier: Apache-2.0
import copy
import contextlib
import io
import json
import subprocess
import tempfile
from unittest.mock import patch
import nuget_audit
from pathlib import Path
import unittest
from nuget_audit import AuditError, evaluate

PROJECT = Path('/project/FreeFlight.Roslyn.csproj')
CLEAN = {"version": 1, "parameters": "--vulnerable --include-transitive", "sources": ["https://api.nuget.org/v3/index.json"], "projects": [{"path": str(PROJECT)}]}


def report_with(severity, group="transitivePackages"):
    report = copy.deepcopy(CLEAN)
    report['projects'][0]['frameworks'] = [{"framework": "net10.0", group: [{"id": "Example", "resolvedVersion": "1.0.0", "vulnerabilities": [{"severity": severity, "advisoryurl": "https://example.org/advisory"}]}]}]
    return report


class AuditPolicyTests(unittest.TestCase):
    def test_clean_nuget_shape_without_frameworks(self):
        self.assertEqual(evaluate(CLEAN, PROJECT), [])

    def test_actionable_severities_for_direct_and_transitive_dependencies(self):
        for group in ('topLevelPackages', 'transitivePackages'):
            for severity in ('High', 'Critical'):
                with self.subTest(group=group, severity=severity):
                    findings = evaluate(report_with(severity, group), PROJECT)
                    self.assertEqual(len(findings), 1)
                    self.assertTrue(findings[0]['actionable'])
                    self.assertEqual(findings[0]['package'], 'Example')

    def test_lower_severities_remain_reported(self):
        for severity in ('Low', 'Moderate'):
            findings = evaluate(report_with(severity), PROJECT)
            self.assertFalse(findings[0]['actionable'])
            self.assertEqual(findings[0]['severity'], severity.lower())

    def test_unknown_or_missing_severity_fails(self):
        for severity in ('', 'Unknown'):
            with self.assertRaises(AuditError):
                evaluate(report_with(severity), PROJECT)

    def test_errors_and_warnings_fail_even_with_clean_projects(self):
        for level in ('error', 'warning'):
            report = copy.deepcopy(CLEAN)
            report['problems'] = [{'level': level, 'text': 'feed unavailable'}]
            with self.assertRaises(AuditError):
                evaluate(report, PROJECT)

    def test_nested_problems_fail(self):
        report = copy.deepcopy(CLEAN)
        report['projects'][0]['problems'] = ['failed retrieval']
        with self.assertRaises(AuditError):
            evaluate(report, PROJECT)

    def test_incomplete_report_fails(self):
        for key in ('version', 'parameters', 'sources', 'projects'):
            report = copy.deepcopy(CLEAN)
            del report[key]
            with self.assertRaises(AuditError):
                evaluate(report, PROJECT)

    def test_wrong_project_or_future_schema_fails(self):
        report = copy.deepcopy(CLEAN)
        report['version'] = 2
        with self.assertRaises(AuditError):
            evaluate(report, PROJECT)
        with self.assertRaises(AuditError):
            evaluate(CLEAN, Path('/another.csproj'))

    def test_malformed_findings_fail(self):
        for key in ('vulnerabilities', 'id', 'resolvedVersion'):
            report = report_with('High')
            del report['projects'][0]['frameworks'][0]['transitivePackages'][0][key]
            with self.assertRaises(AuditError):
                evaluate(report, PROJECT)

    def test_transitive_flag_required(self):
        report = copy.deepcopy(CLEAN)
        report['parameters'] = '--vulnerable'
        with self.assertRaises(AuditError):
            evaluate(report, PROJECT)

    def test_command_exit_policy_and_failure_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            assets = root / 'bin/.local/roslyn/obj/FreeFlight.Roslyn'
            assets.mkdir(parents=True)
            (assets / 'project.assets.json').write_text('{}')
            source = root / 'workflows/dependency.audit/assets/nuget_audit.py'
            for kind, expected in [('clean', 0), ('vulnerable', 1), ('error', 2), ('malformed', 2), ('stderr', 2), ('timeout', 2)]:
                with self.subTest(kind=kind):
                    report = report_with('High') if kind == 'vulnerable' else copy.deepcopy(CLEAN)
                    report['projects'][0]['path'] = str(root / 'workers/roslyn/FreeFlight.Roslyn.csproj')
                    result = subprocess.CompletedProcess([], 1 if kind == 'error' else 0, 'invalid' if kind == 'malformed' else json.dumps(report), 'feed warning' if kind == 'stderr' else '')
                    with patch.object(nuget_audit, '__file__', str(source)), patch.object(nuget_audit.subprocess, 'run', side_effect=subprocess.TimeoutExpired('dotnet', 180) if kind == 'timeout' else None, return_value=result) as invoke, contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(nuget_audit.run(), expected)
                    receipt = json.loads((root / 'bin/.local/reports/nuget-audit.json').read_text())
                    self.assertEqual(receipt['status'], 'passed' if expected == 0 else 'vulnerable' if expected == 1 else 'error')
                    self.assertIn('--no-restore', invoke.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
