using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using Microsoft.CodeAnalysis;

namespace FreeFlight.Roslyn;

internal sealed class ProjectLoadException(string code, string message, string? selectedProject,
    string remediation, object[]? diagnostics = null) : Exception(message)
{
    public object Detail => new { code, message = Message, selectedProject, remediation, diagnostics = diagnostics ?? [] };
}

internal sealed record LoadWarning(string code, string message, string project,
    string severity, string reportedKind, string evidence);

/// <summary>
/// Roslyn can flatten MSBuild warnings into Failure (dotnet/roslyn#75182). Never
/// infer severity from an NU prefix or from arbitrary message substrings. Recover
/// only an exact, project-bound NuGet Warning persisted by restore. All unmatched
/// Failure diagnostics still reject the graph. Assets are evidence, not commands.
/// </summary>
internal static class ProjectLoadDiagnostics
{
    private static readonly HashSet<string> Recoverable = ["NU1603", "NU1701", "NU1903"];
    private sealed record Evidence(string Project, string Assets, string Code, string Message, string Level);

    public static List<LoadWarning> Classify(string root, string selected, Solution solution,
        IEnumerable<WorkspaceDiagnostic> diagnostics, Func<string, string> checkPath,
        ResourcePolicy resources, CancellationToken token, IReadOnlyDictionary<string, string> evaluatedAssets)
    {
        var evidence = new List<Evidence>();
        long total = 0;
        var missingAssets = new List<(string Project, string Assets)>();
        var projectCount = 0;
        foreach (var project in solution.Projects)
        {
            token.ThrowIfCancellationRequested();
            if (++projectCount > 256) throw new ProjectLoadException("project_load_failed", "Trusted workspace exceeds 256 projects", selected, "Select a smaller project graph.");
            if (project.FilePath is null) continue;
            var projectPath = checkPath(project.FilePath);
            var assets = evaluatedAssets.TryGetValue(projectPath, out var evaluated) ? evaluated : Path.Combine(Path.GetDirectoryName(projectPath)!, "obj", "project.assets.json");
            if (!File.Exists(assets))
            {
                missingAssets.Add((projectPath, assets));
                // Some SDK design-time targets deliberately skip package resolution
                // when assets are absent, and their binlogs may omit this property.
                // Detect only declarative SDK/PackageReference markers, never evaluate
                // XML ourselves. Legacy projects without these markers need no assets.
                RequireDefaultAssets(root, selected, projectPath, assets, resources, ref total, token);
                continue;
            }
            assets = checkPath(assets);
            using var stream = File.OpenRead(assets);
            ResourcePolicy.Check("maxFileBytes", root, assets, stream.Length, resources.MaxFileBytes);
            using var bytes = new MemoryStream();
            var buffer = new byte[65536];
            for (int size; (size = stream.Read(buffer)) > 0;)
            {
                token.ThrowIfCancellationRequested();
                total += size;
                ResourcePolicy.Check("maxFileBytes", root, assets, bytes.Length + size, resources.MaxFileBytes);
                ResourcePolicy.Check("maxWorkspaceBytes", root, assets, total, resources.MaxWorkspaceBytes);
                bytes.Write(buffer, 0, size);
            }
            bytes.Position = 0;
            try
            {
                using var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 64 });
                var value = document.RootElement;
                if (!value.TryGetProperty("project", out var data) ||
                    !data.TryGetProperty("restore", out var restore) ||
                    !restore.TryGetProperty("projectPath", out var path) ||
                    !string.Equals(Path.GetFullPath(path.GetString()!), projectPath,
                        OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal))
                    continue; // Cannot bind evidence to this project.
                if (!value.TryGetProperty("logs", out var logs) || logs.ValueKind != JsonValueKind.Array) continue;
                foreach (var log in logs.EnumerateArray())
                {
                    if (evidence.Count >= 2048) throw new ProjectLoadException("project_load_failed",
                        "Restore diagnostic evidence exceeds 2048 entries", selected, "Open a smaller project graph.");
                    if (log.TryGetProperty("code", out var code) && code.ValueKind == JsonValueKind.String &&
                        log.TryGetProperty("message", out var message) && message.ValueKind == JsonValueKind.String &&
                        log.TryGetProperty("level", out var level) && level.ValueKind == JsonValueKind.String)
                        evidence.Add(new(projectPath, assets, code.GetString()!, message.GetString()!, level.GetString()!));
                }
            }
            catch (JsonException)
            {
                throw new ProjectLoadException("restore_required", "Restore assets are malformed: " + Path.GetRelativePath(root, assets),
                    selected, "Inspect these assets and explicitly restore the selected trusted project; FreeFlight never restores automatically.");
            }
        }
        // A restore Error is not made harmless by a matching Warning or by a usable
        // partial graph. Preserve it even if the MSBuild wrapper dropped that event.
        var errors = evidence.Where(e => string.Equals(e.Level, "Error", StringComparison.OrdinalIgnoreCase)).ToArray();
        if (errors.Length > 0)
            throw new ProjectLoadException("restore_required", "Restore assets contain dependency errors", selected,
                "Resolve the recorded dependency errors and explicitly restore the selected project.",
                errors.Select(e => (object)new { code = e.Code, message = e.Message, project = Path.GetRelativePath(root, e.Project), severity = e.Level }).ToArray());

        var reported = diagnostics.Take(2049).ToArray();
        if (reported.Length > 2048)
            throw new ProjectLoadException("project_load_failed", "Project loading exceeds 2048 diagnostics", selected, "Open a smaller project graph.");
        var occurrences = reported.GroupBy(diagnostic => diagnostic.Message, StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => group.Count(), StringComparer.Ordinal);
        var warnings = new List<LoadWarning>();
        var failures = new List<object>();
        var restoreRequired = false;
        foreach (var diagnostic in reported)
        {
            token.ThrowIfCancellationRequested();
            if (warnings.Count + failures.Count >= 2048)
                throw new ProjectLoadException("project_load_failed", "Project loading exceeds 2048 diagnostics", selected, "Open a smaller project graph.");
            var matches = evidence.Where(e => Recoverable.Contains(e.Code) && e.Level == "Warning" &&
                diagnostic.Message == $"Msbuild failed when processing the file '{e.Project}' with message: {e.Message}").ToArray();
            if (matches.Length == 1 && occurrences[diagnostic.Message] == 1)
            {
                var e = matches[0];
                warnings.Add(new(e.Code, e.Message, Path.GetRelativePath(root, e.Project), "Warning",
                    diagnostic.Kind.ToString(), Path.GetRelativePath(root, e.Assets)));
            }
            else if (diagnostic.Kind == WorkspaceDiagnosticKind.Warning)
                warnings.Add(new("workspace_warning", diagnostic.Message, "", "Warning", "Warning", "MSBuildWorkspace"));
            else
            {
                failures.Add(new { message = diagnostic.Message, reportedKind = diagnostic.Kind.ToString() });
                // The SDK's missing-assets diagnostic is concrete restore evidence.
                // Unknown project failures must not receive generic restore advice.
                restoreRequired |= missingAssets.Any(e => diagnostic.Message.StartsWith(
                    $"Msbuild failed when processing the file '{e.Project}' with message: ", StringComparison.Ordinal) &&
                    diagnostic.Message.Contains($"Assets file '{e.Assets}' not found", StringComparison.Ordinal));
                restoreRequired |= diagnostic.Message.Contains("NETSDK1064", StringComparison.Ordinal);
            }
        }
        if (failures.Count > 0)
            throw new ProjectLoadException(restoreRequired ? "restore_required" : "project_load_failed",
                "Trusted project loading failed", selected,
                restoreRequired ? "Required restore assets or packages are missing. Explicitly restore the selected trusted project before reopening."
                    : "Inspect the project-load diagnostics, SDK/targeting packs and project configuration. Restore is not automatically indicated.", failures.ToArray());
        return warnings;
    }

    private static void RequireDefaultAssets(string root, string selected, string projectPath, string assets,
        ResourcePolicy resources, ref long total, CancellationToken token)
    {
        using var input = File.OpenRead(projectPath);
        ResourcePolicy.Check("maxFileBytes", root, projectPath, input.Length, resources.MaxFileBytes);
        using var bytes = new MemoryStream();
        var buffer = new byte[65536];
        for (int size; (size = input.Read(buffer)) > 0;)
        {
            token.ThrowIfCancellationRequested();
            total += size;
            ResourcePolicy.Check("maxFileBytes", root, projectPath, bytes.Length + size, resources.MaxFileBytes);
            ResourcePolicy.Check("maxWorkspaceBytes", root, projectPath, total, resources.MaxWorkspaceBytes);
            bytes.Write(buffer, 0, size);
        }
        bytes.Position = 0;
        XDocument document;
        try
        {
            using var reader = XmlReader.Create(bytes, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null });
            document = XDocument.Load(reader);
        }
        catch (XmlException exception)
        {
            throw new ProjectLoadException("project_load_failed", "Cannot inspect trusted project restore requirements", selected,
                "Correct the project XML before reopening.", [new { message = exception.Message }]);
        }
        var elements = document.Root?.DescendantsAndSelf().Take(10001).ToArray() ?? [];
        if (elements.Length > 10000) throw new ProjectLoadException("project_load_failed", "Project restore inspection exceeds 10000 XML elements", selected,
            "Select a smaller supported project or inspect its evaluated restore configuration.");
        var sdk = document.Root?.Attribute("Sdk") is { Value.Length: > 0 } ||
            elements.Any(element => element.Name.LocalName == "Sdk" ||
                element.Name.LocalName == "Import" && element.Attribute("Sdk") is not null);
        var packageReference = elements.Any(element => element.Name.LocalName == "PackageReference" ||
            element.Name.LocalName == "RestoreProjectStyle" && element.Value == "PackageReference");
        if (!sdk && !packageReference) return;

        var customized = elements.Any(element => element.Name.LocalName is "ProjectAssetsFile" or "BaseIntermediateOutputPath" or
            "MSBuildProjectExtensionsPath" or "DirectoryBuildPropsPath" or "DirectoryBuildTargetsPath" ||
            element.Name.LocalName == "Import" && element.Attribute("Sdk") is null);
        // Imported configuration can change restore paths. If no evaluated path was
        // recorded, do not claim that a guessed default path proves restore is needed.
        for (var directory = Path.GetDirectoryName(projectPath)!; ; directory = Path.GetDirectoryName(directory)!)
        {
            token.ThrowIfCancellationRequested();
            customized |= File.Exists(Path.Combine(directory, "Directory.Build.props")) ||
                File.Exists(Path.Combine(directory, "Directory.Build.targets"));
            if (string.Equals(directory, root, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)) break;
        }
        if (customized)
            throw new ProjectLoadException("project_load_failed", "Cannot verify the customized restore assets path for " + Path.GetRelativePath(root, projectPath),
                selected, "Inspect the project's evaluated ProjectAssetsFile and restore state; custom or inherited intermediate paths were not present in diagnostic evidence.");
        throw new ProjectLoadException("restore_required", "Default restore assets are missing for an SDK/PackageReference project: " + Path.GetRelativePath(root, assets),
            selected, "Explicitly restore the selected trusted project before reopening. FreeFlight never restores automatically.");
    }

}
