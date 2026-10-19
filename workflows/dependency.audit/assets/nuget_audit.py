# SPDX-License-Identifier: Apache-2.0
"""DockPipe audit adapter: NuGet's JSON findings need an explicit CI exit policy."""
import json
import os
from pathlib import Path
import subprocess
import sys


class AuditError(ValueError):
    """The audit cannot establish a complete, trustworthy result."""


def evaluate(report, expected_project):
    if not isinstance(report, dict) or report.get("version") != 1:
        raise AuditError("Unsupported NuGet report version")
    parameters = report.get("parameters", "")
    if not isinstance(parameters, str) or not {"--vulnerable", "--include-transitive"}.issubset(parameters.split()):
        raise AuditError("Audit must include vulnerable and transitive packages")
    sources = report.get("sources")
    if not isinstance(sources, list) or not sources or not all(isinstance(s, str) and s for s in sources):
        raise AuditError("Missing vulnerability sources")
    projects = report.get("projects")
    if not isinstance(projects, list) or len(projects) != 1:
        raise AuditError("Expected exactly the requested Roslyn project")
    project = projects[0]
    if not isinstance(project, dict) or not isinstance(project.get("path"), str) or Path(project["path"]).resolve() != expected_project.resolve():
        raise AuditError("Report project does not match requested project")

    def check_problems(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"problems", "errors", "warnings"} and child:
                    raise AuditError("NuGet reported audit problems: " + json.dumps(child))
                check_problems(child)
        elif isinstance(value, list):
            for child in value:
                check_problems(child)

    check_problems(report)
    frameworks = project.get("frameworks", [])
    if not isinstance(frameworks, list):
        raise AuditError("Malformed framework list")
    findings = []
    for framework in frameworks:
        if not isinstance(framework, dict) or not isinstance(framework.get("framework"), str):
            raise AuditError("Malformed framework result")
        for group in ("topLevelPackages", "transitivePackages"):
            packages = framework.get(group, [])
            if not isinstance(packages, list):
                raise AuditError("Malformed package list")
            for package in packages:
                if not isinstance(package, dict) or not all(isinstance(package.get(key), str) and package[key] for key in ("id", "resolvedVersion")):
                    raise AuditError("Malformed package identity")
                vulnerabilities = package.get("vulnerabilities")
                if not isinstance(vulnerabilities, list) or not vulnerabilities:
                    raise AuditError("Vulnerable-package entry lacks vulnerability details")
                for item in vulnerabilities:
                    severity = item.get("severity", "").lower() if isinstance(item, dict) and isinstance(item.get("severity"), str) else ""
                    if severity not in {"low", "moderate", "high", "critical"}:
                        raise AuditError("Unknown vulnerability severity")
                    advisory = item.get("advisoryurl")
                    if not isinstance(advisory, str) or not advisory.startswith("https://"):
                        raise AuditError("Missing vulnerability advisory URL")
                    findings.append({"package": package["id"], "version": package["resolvedVersion"], "framework": framework["framework"], "severity": severity, "advisory": advisory, "actionable": severity in {"high", "critical"}})
    return findings


def run():
    root = Path(__file__).resolve().parents[3]
    project = root / "workers/roslyn/FreeFlight.Roslyn.csproj"
    assets = root / "bin/.local/roslyn/obj/FreeFlight.Roslyn"
    receipt = root / "bin/.local/reports/nuget-audit.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    outcome = {"status": "error", "policy": "high-and-critical", "includeTransitive": True}
    exit_code = 2
    try:
        if not (assets / "project.assets.json").is_file():
            raise AuditError("Restored Roslyn assets missing; run the workers.roslyn DockPipe workflow first")
        env = dict(os.environ, MSBuildProjectExtensionsPath=str(assets) + os.sep)
        result = subprocess.run(["dotnet", "list", str(project), "package", "--vulnerable", "--include-transitive", "--format", "json", "--output-version", "1", "--no-restore"], cwd=root, env=env, capture_output=True, text=True, timeout=180, check=False)
        if result.returncode != 0:
            raise AuditError(f"NuGet audit command failed ({result.returncode}): {result.stdout}\n{result.stderr}")
        if result.stderr.strip():
            raise AuditError("NuGet emitted diagnostics: " + result.stderr)
        report = json.loads(result.stdout)
        findings = evaluate(report, project)
        outcome.update(report=report, findings=findings)
        exit_code = 1 if any(f["actionable"] for f in findings) else 0
        outcome["status"] = "vulnerable" if exit_code else "passed"
    except (AuditError, OSError, ValueError, subprocess.SubprocessError) as error:
        outcome["error"] = str(error)
    receipt.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(outcome, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(run())
