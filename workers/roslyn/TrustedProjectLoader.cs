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
    internal sealed record Loaded(SolutionInfo Solution, string SelectedProject, List<LoadWarning> Warnings);

    public static Task<Loaded> Load(string root, string? requested,
        Func<string, string> checkPath, Func<string, string, string> compilerInput, ResourcePolicy resources, CancellationToken token)
    {
        var target = Select(root, requested, checkPath, resources, token);
        var selected = Path.GetRelativePath(root, target);
        if (!MSBuildLocator.IsRegistered)
        {
            // Registration is intentionally deferred: safe-source never searches for an SDK.
            try
            {
                var instance = MSBuildLocator.RegisterDefaults();
                Console.Error.WriteLine(System.Text.Json.JsonSerializer.Serialize(new
                {
                    kind = "freeflight.msbuild-toolset",
                    runtimeVersion = Environment.Version.ToString(),
                    instanceVersion = instance.Version.ToString(),
                    discoveryType = instance.DiscoveryType.ToString(),
                    msbuildPath = instance.MSBuildPath,
                    msbuildVersion = System.Diagnostics.FileVersionInfo.GetVersionInfo(
                        Path.Combine(instance.MSBuildPath, "Microsoft.Build.dll")).FileVersion
                }));
            }
            catch (InvalidOperationException exception)
            {
                throw new ProjectLoadException("sdk_not_found", "Cannot select an installed .NET SDK for trusted project evaluation", selected,
                    "Install/select a compatible .NET SDK (the bundled runtime is not an SDK), then restart FreeFlight.",
                    [new { message = exception.Message }]);
            }
        }
        return LoadRegistered(root, target, selected, checkPath, compilerInput, resources, token);
    }

    // Keep Framework/ILogger types out of the registration method's JIT body.
    // Locator must select the SDK before those assemblies are resolved.
    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    private static async Task<Loaded> LoadRegistered(string root, string target, string selected,
        Func<string, string> checkPath, Func<string, string, string> compilerInput, ResourcePolicy resources, CancellationToken token)
    {
        var extension = Path.GetExtension(target);
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
        using var logger = new ProjectErrorLogger();
        try
        {
            if (extension.Equals(".sln", StringComparison.OrdinalIgnoreCase)) await loader.OpenSolutionAsync(target, logger.Logger, cancellationToken: token);
            else await loader.OpenProjectAsync(target, logger.Logger, cancellationToken: token);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            throw new ProjectLoadException("project_load_failed", "Trusted project evaluation could not load the selected graph", selected,
                "Inspect the diagnostic and installed SDK/targeting packs. No automatic restore or build was requested.",
                [new { message = exception.Message }]);
        }
        var evaluatedAssets = logger.Read(root, selected, checkPath, token);
        var warnings = ProjectLoadDiagnostics.Classify(root, selected, loader.CurrentSolution, loader.Diagnostics,
            checkPath, resources, token, evaluatedAssets);

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
            if (project.MetadataReferences.Count == 0 || project.MetadataReferences.Any(reference =>
                reference is not PortableExecutableReference portable || portable.FilePath is null || !File.Exists(portable.FilePath)) ||
                project.ProjectReferences.Any(reference => loader.CurrentSolution.GetProject(reference.ProjectId) is null))
                throw new ProjectLoadException("project_load_failed", "Project graph has missing required references: " + Path.GetRelativePath(root, projectPath),
                    selected, "Inspect dependency resolution and the installed SDK/targeting packs; the partial graph is not usable.");
            var sources = new List<DocumentInfo>();
            foreach (var document in project.Documents)
            {
                var path = compilerInput(document.FilePath ?? throw new InvalidOperationException("Document has no path"), projectPath);
                ResourcePolicy.Check("maxFiles", root, path, ++count, resources.MaxFiles);
                var length = new FileInfo(path).Length;
                totalBytes += length;
                ResourcePolicy.Check("maxFileBytes", root, path, length, resources.MaxFileBytes);
                ResourcePolicy.Check("maxWorkspaceBytes", root, path, totalBytes, resources.MaxWorkspaceBytes);
                // Do not retain a filesystem-backed loader: comparing initial document
                // text during Refresh would otherwise trigger an additional, unbounded
                // read after the guarded snapshot. Refresh fills this inert placeholder
                // before any compilation or semantic request.
                sources.Add(DocumentInfo.Create(document.Id, document.Name, document.Folders,
                    document.SourceCodeKind, TextLoader.From(TextAndVersion.Create(
                        SourceText.From(string.Empty), VersionStamp.Create(), path)), path));
            }
            // Do not retain AnalyzerReferences, including source generator assemblies.
            // Do not use MSBuildWorkspace.TryApplyChanges: it can write to project files.
            projects.Add(ProjectInfo.Create(project.Id, VersionStamp.Create(), project.Name,
                project.AssemblyName ?? project.Name, project.Language, projectPath,
                compilationOptions: project.CompilationOptions, parseOptions: project.ParseOptions,
                documents: sources, projectReferences: project.ProjectReferences,
                metadataReferences: project.MetadataReferences));
        }
        if (projects.Count == 0) throw new ProjectLoadException("project_load_failed", "No supported projects were loaded", selected,
            "Select a solution or project containing supported C# projects.");
        return new(SolutionInfo.Create(SolutionId.CreateNewId(), VersionStamp.Create(), projects: projects), selected, warnings);
    }

    private static string Select(string root, string? requested, Func<string, string> checkPath,
        ResourcePolicy resources, CancellationToken token)
    {
        if (requested is not null)
        {
            if (Path.IsPathRooted(requested)) throw new ProjectLoadException("project_selection_required",
                "Project selection must be relative to the authorized workspace", requested, "Use a root-relative .sln or .csproj path.");
            var target = checkPath(requested);
            if (!new[] { ".sln", ".csproj" }.Contains(Path.GetExtension(target), StringComparer.OrdinalIgnoreCase))
                throw new ProjectLoadException("project_selection_required", "Trusted mode accepts only .sln or .csproj", requested,
                    "Select a root-relative .sln or .csproj path.");
            return target;
        }
        var pending = new Stack<string>();
        pending.Push(root);
        var solutions = new List<string>();
        var projects = new List<string>();
        var excluded = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ".git", ".hg", "node_modules", "bin", "obj", ".freeflight", ".dockpipe" };
        long entries = 0;
        while (pending.Count > 0)
        {
            token.ThrowIfCancellationRequested();
            foreach (var entry in Directory.EnumerateFileSystemEntries(pending.Pop()))
            {
                token.ThrowIfCancellationRequested();
                ResourcePolicy.Check("maxDirectoryEntries", root, entry, ++entries, resources.MaxDirectoryEntries);
                var attributes = File.GetAttributes(entry);
                if ((attributes & FileAttributes.ReparsePoint) != 0) continue;
                if ((attributes & FileAttributes.Directory) != 0)
                {
                    if (!excluded.Contains(Path.GetFileName(entry))) pending.Push(checkPath(entry));
                    continue;
                }
                if (Path.GetExtension(entry).Equals(".sln", StringComparison.OrdinalIgnoreCase)) solutions.Add(checkPath(entry));
                if (Path.GetExtension(entry).Equals(".csproj", StringComparison.OrdinalIgnoreCase)) projects.Add(checkPath(entry));
                if (solutions.Count + projects.Count > 1024)
                    throw new ProjectLoadException("project_selection_required", "Project discovery exceeds 1024 candidates", null,
                        "Set an explicit root-relative project path to avoid discovery.");
            }
        }
        var candidates = (solutions.Count > 0 ? solutions : projects).Order(StringComparer.Ordinal).ToArray();
        if (candidates.Length != 1)
            throw new ProjectLoadException("project_selection_required", candidates.Length == 0 ? "No .sln or .csproj found" : "Multiple project/solution candidates found", null,
                "Select project in workspace.open using a root-relative .sln/.csproj path and reload=true; no startup configuration change is required.",
                candidates.Take(32).Select(path => (object)new { candidate = Path.GetRelativePath(root, path) }).ToArray());
        return candidates[0];
    }

}
