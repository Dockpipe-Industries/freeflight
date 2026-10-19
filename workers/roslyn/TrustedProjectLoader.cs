using Microsoft.Build.Locator;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.MSBuild;
using Microsoft.CodeAnalysis.Text;

namespace FreeFlight.Roslyn;

/// <summary>
/// Explicitly trusted design-time evaluation only. MSBuild can execute repository
/// code during loading; these settings and path checks are not an execution sandbox.
/// The resulting graph is copied into AdhocWorkspace before semantic compilation.
/// </summary>
internal static class TrustedProjectLoader
{
    public static async Task<SolutionInfo> Load(string root, string? requested,
        Func<string, string> checkPath, CancellationToken token)
    {
        if (!MSBuildLocator.IsRegistered)
        {
            // Registration is intentionally deferred: safe-source never searches for an SDK.
            MSBuildLocator.RegisterDefaults();
        }

        string target;
        if (requested is not null)
        {
            target = checkPath(requested);
        }
        else
        {
            var solutions = Directory.GetFiles(root, "*.sln");
            var candidates = solutions.Length > 0 ? solutions : Directory.GetFiles(root, "*.csproj");
            if (candidates.Length != 1)
                throw new ArgumentException("Trusted mode requires exactly one root-level .sln/.csproj, or an explicit project path");
            target = checkPath(candidates[0]);
        }

        var extension = Path.GetExtension(target);
        if (extension is not (".sln" or ".csproj"))
            throw new ArgumentException("Trusted mode accepts only .sln or .csproj");

        var properties = new Dictionary<string, string>
        {
            ["DesignTimeBuild"] = "true",
            ["BuildProjectReferences"] = "false",
            ["SkipCompilerExecution"] = "true",
            ["ProvideCommandLineArgs"] = "true",
            ["RunAnalyzers"] = "false",
            ["RunAnalyzersDuringBuild"] = "false",
            ["EnableNETAnalyzers"] = "false",
            ["RestoreDuringBuild"] = "false"
        };
        using var loader = MSBuildWorkspace.Create(properties);
        loader.LoadMetadataForReferencedProjects = false;
        if (extension == ".sln") await loader.OpenSolutionAsync(target, cancellationToken: token);
        else await loader.OpenProjectAsync(target, cancellationToken: token);

        var failures = loader.Diagnostics.Where(d => d.Kind == WorkspaceDiagnosticKind.Failure).ToArray();
        if (failures.Length > 0)
            throw new InvalidOperationException("Trusted project loading failed; restore dependencies explicitly first: " + string.Join("; ", failures.Select(d => d.Message)));

        var projects = new List<ProjectInfo>();
        var count = 0;
        long totalBytes = 0;
        foreach (var project in loader.CurrentSolution.Projects)
        {
            token.ThrowIfCancellationRequested();
            if (projects.Count >= 256) throw new InvalidOperationException("Trusted workspace exceeds 256 projects");
            if (project.Language != LanguageNames.CSharp)
                throw new InvalidOperationException("Only C# projects are supported by this worker");
            var projectPath = checkPath(project.FilePath ?? throw new InvalidOperationException("Project has no path"));
            var sources = new List<DocumentInfo>();
            foreach (var document in project.Documents)
            {
                var path = checkPath(document.FilePath ?? throw new InvalidOperationException("Document has no path"));
                if (++count > 10000) throw new InvalidOperationException("Trusted workspace exceeds 10000 source documents");
                var length = new FileInfo(path).Length;
                totalBytes += length;
                if (length > 2 * 1024 * 1024 || totalBytes > 64L * 1024 * 1024)
                    throw new InvalidOperationException("Trusted workspace exceeds source size limits");
                // FileTextLoader does not execute code. SourceEngine replaces text with a
                // bounded byte snapshot before any compilation or semantic request.
                sources.Add(DocumentInfo.Create(document.Id, document.Name, document.Folders,
                    document.SourceCodeKind, new FileTextLoader(path, defaultEncoding: null), path));
            }
            // Do not retain AnalyzerReferences, including source generator assemblies.
            // Do not use MSBuildWorkspace.TryApplyChanges: it can write to project files.
            projects.Add(ProjectInfo.Create(project.Id, VersionStamp.Create(), project.Name,
                project.AssemblyName ?? project.Name, project.Language, projectPath,
                compilationOptions: project.CompilationOptions, parseOptions: project.ParseOptions,
                documents: sources, projectReferences: project.ProjectReferences,
                metadataReferences: project.MetadataReferences));
        }
        if (projects.Count == 0) throw new InvalidOperationException("No supported projects were loaded");
        return SolutionInfo.Create(SolutionId.CreateNewId(), VersionStamp.Create(), projects: projects);
    }
}
