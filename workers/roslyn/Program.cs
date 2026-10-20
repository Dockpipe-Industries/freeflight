using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.Rename;
using Microsoft.CodeAnalysis.Text;

namespace FreeFlight.Roslyn;

internal static class Program
{
    private static readonly JsonSerializerOptions Json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public static async Task Main(string[] commandLine)
    {
        // Worker pipes are UTF-8 on every platform, independent of console code pages.
        var utf8 = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);
        using var input = new StreamReader(Console.OpenStandardInput(), utf8,
            detectEncodingFromByteOrderMarks: false, bufferSize: 4096, leaveOpen: true);
        using var output = new StreamWriter(Console.OpenStandardOutput(), utf8,
            bufferSize: 4096, leaveOpen: true) { AutoFlush = true, NewLine = "\n" };
        if (commandLine.Any(argument => argument != "--trusted-msbuild"))
            throw new ArgumentException("Only --trusted-msbuild is accepted");
        var trustedMsbuild = commandLine.Contains("--trusted-msbuild", StringComparer.Ordinal);
        if (trustedMsbuild)
            Console.Error.WriteLine("WARNING: trusted MSBuild mode can execute repository code during project evaluation. This process is not a sandbox. No restore or production build is requested.");
        using var engine = new SourceEngine(trustedMsbuild);
        using var gate = new SemaphoreSlim(1);
        var active = new ConcurrentDictionary<string, CancellationTokenSource>();
        var jobs = new List<Task>();
        var outputGate = new object();
        void Reply(object value)
        {
            lock (outputGate) output.WriteLine(JsonSerializer.Serialize(value, Json));
        }
        while (true)
        {
            string? line;
            try { line = ReadBoundedLine(input, 1024 * 1024); }
            catch (DecoderFallbackException) { Reply(new { id = (object?)null, error = new { message = "Invalid UTF-8 input" } }); break; }
            catch (Exception ex) { Reply(new { id = (object?)null, error = new { message = ex.Message } }); break; }
            if (line is null) break;
            JsonElement request;
            try { using var json = JsonDocument.Parse(line); request = json.RootElement.Clone(); }
            catch (JsonException) { Reply(new { id = (object?)null, error = new { message = "Invalid JSON" } }); continue; }
            if (request.ValueKind != JsonValueKind.Object)
            {
                Reply(new { id = (object?)null, error = new { message = "Request must be an object" } });
                continue;
            }
            var id = request.TryGetProperty("id", out var suppliedId) ? suppliedId.Clone() : JsonSerializer.SerializeToElement<object?>(null);
            try
            {
                var method = request.GetProperty("method").GetString() ?? throw new ArgumentException("method is required");
                var args = request.TryGetProperty("params", out var parameters) ? parameters.Clone() : JsonSerializer.SerializeToElement(new { });
                if (method == "cancel")
                {
                    if (args.TryGetProperty("id", out var target) && active.TryGetValue(target.GetRawText(), out var cancellation)) cancellation.Cancel();
                    continue;
                }
                if (method == "shutdown") break;
                if (active.Count >= 32) throw new InvalidOperationException("Worker request queue is full");
                var key = id.GetRawText();
                var cts = new CancellationTokenSource(TimeSpan.FromSeconds(60));
                if (!active.TryAdd(key, cts)) { cts.Dispose(); throw new ArgumentException("Duplicate request id"); }
                jobs.RemoveAll(t => t.IsCompleted);
                jobs.Add(Task.Run(async () =>
                {
                    try
                    {
                        await gate.WaitAsync(cts.Token);
                        try { Reply(new { id, result = await engine.Invoke(method, args, cts.Token) }); }
                        finally { gate.Release(); }
                    }
                    catch (OperationCanceledException) { Reply(new { id, error = new { message = "Request cancelled" } }); }
                    catch (ProjectLoadException ex) { Reply(new { id, error = ex.Detail }); }
                    catch (ResourceLimitException ex) { Reply(new { id, error = ex.Detail }); }
                    catch (Exception ex) { Reply(new { id, error = new { message = ex.Message } }); }
                    finally { active.TryRemove(key, out _); cts.Dispose(); }
                }));
            }
            catch (Exception ex) { Reply(new { id, error = new { message = ex.Message } }); }
        }
        foreach (var cancellation in active.Values) cancellation.Cancel();
        await Task.WhenAll(jobs);
    }

    private static string? ReadBoundedLine(TextReader reader, int limit)
    {
        var result = new StringBuilder();
        for (var value = reader.Read(); value != -1; value = reader.Read())
        {
            if (value == '\n') return result.ToString();
            if (result.Length >= limit) throw new InvalidDataException("Request exceeds 1 MiB");
            result.Append((char)value);
        }
        return result.Length == 0 ? null : result.ToString();
    }
}

internal sealed class SourceEngine : IDisposable
{
    private ResourcePolicy resources = new();
    private readonly Dictionary<string, FileSnapshot> snapshots = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<string, long> dirtyFiles = new(StringComparer.Ordinal);
    private FileSystemWatcher? watcher;
    private long invalidationGeneration;
    private long changeSequence;
    private long bytesRead;
    private long reusedSnapshots;
    private sealed record FileSnapshot(long Length, long Modified, long Dirty, long Generation, long ValidatedAt);

    private void Watch(string directory)
    {
        watcher?.Dispose();
        watcher = null;
        snapshots.Clear();
        dirtyFiles.Clear();
        Interlocked.Increment(ref invalidationGeneration);
        try
        {
            watcher = new FileSystemWatcher(directory)
            {
                IncludeSubdirectories = true,
                NotifyFilter = NotifyFilters.FileName | NotifyFilters.DirectoryName | NotifyFilters.LastWrite | NotifyFilters.Size
            };
            watcher.Changed += (_, e) => MarkDirty(e.FullPath);
            watcher.Created += (_, e) => MarkDirty(e.FullPath);
            watcher.Deleted += (_, e) => MarkDirty(e.FullPath);
            watcher.Renamed += (_, e) => { MarkDirty(e.OldFullPath); MarkDirty(e.FullPath); };
            watcher.Error += (_, _) => Interlocked.Increment(ref invalidationGeneration);
            watcher.EnableRaisingEvents = true;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or PlatformNotSupportedException or ArgumentException)
        {
            watcher?.Dispose();
            watcher = null; // Unsupported watchers fall back to validating every request.
        }
    }

    private void MarkDirty(string path)
    {
        dirtyFiles[path] = Interlocked.Increment(ref changeSequence);
        if (dirtyFiles.Count > 4096)
        {
            Interlocked.Increment(ref invalidationGeneration);
            dirtyFiles.Clear();
        }
    }
    private readonly AdhocWorkspace workspace = new();
    private readonly Dictionary<string, DocumentId> documents = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> fingerprints = new(StringComparer.Ordinal);
    private readonly HashSet<string> externalCompilerInputs = new(StringComparer.Ordinal);
    private readonly Dictionary<string, List<DocumentId>> externalDocuments = new(StringComparer.Ordinal);
    private readonly bool trustedMsbuild;
    private string Mode => trustedMsbuild ? "trusted-msbuild" : "safe-source";
    public SourceEngine(bool trustedMsbuild) => this.trustedMsbuild = trustedMsbuild;
    private string? selectedProject;
    private List<LoadWarning> loadWarnings = [];
    private ProjectId? projectId;
    private string? root;
    private static readonly HashSet<string> Excluded = new(StringComparer.OrdinalIgnoreCase) { ".git", ".hg", "node_modules", "bin", "obj", ".freeflight" };
    private static readonly StringComparison PathComparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;

    public async Task<object> Invoke(string method, JsonElement args, CancellationToken token)
    {
        if (method != "open" && new[] { "mode", "project", "trustedMsbuild", "trusted-msbuild", "csharp" }.Any(name => args.TryGetProperty(name, out _)))
            throw new ArgumentException("Project selection and trust cannot be changed by semantic requests");
        if (method != "open" && args.TryGetProperty("resources", out _))
            throw new ArgumentException("Resource settings may only be supplied by the core when opening a workspace");
        if (method == "capabilities") return new
        {
            languages = new[] { "csharp" },
            operations = new[] { "symbols", "definition", "references", "hover", "diagnostics", "rename", "implementations", "typeInfo", "signatureHelp", "workspaceSymbols", "callHierarchy", "typeHierarchy" },
            mode = Mode,
            fidelity = Mode,
            projectEvaluation = trustedMsbuild,
            selectedProject,
            loadWarnings,
            degradedFidelity = !trustedMsbuild || loadWarnings.Count > 0,
            edits = "preview-only",
            refreshStats = new { bytesRead, reusedSnapshots, invalidationGeneration }
        };
        if (method == "open")
        {
            var requested = Path.GetFullPath(args.GetProperty("root").GetString() ?? throw new ArgumentException("root is required"));
            if (!Directory.Exists(requested)) throw new DirectoryNotFoundException(requested);
            if (args.TryGetProperty("mode", out var mode) && mode.GetString() != Mode)
                throw new ArgumentException("Workspace mode must match the operator-owned startup mode; requests cannot change trust");
            var selectedResources = ResourcePolicy.Parse(args);
            root = ResolveRoot(requested);
            resources = selectedResources;
            Watch(root);
            workspace.ClearSolution();
            documents.Clear();
            fingerprints.Clear();
            projectId = null;
            selectedProject = null;
            externalCompilerInputs.Clear();
            externalDocuments.Clear();
            loadWarnings = [];
            if (trustedMsbuild)
            {
                var requestedProject = args.TryGetProperty("project", out var selected) ? selected.GetString() : null;
                var graph = await TrustedProjectLoader.Load(root, requestedProject, CheckPath, RegisterCompilerInput, resources, token);
                workspace.AddSolution(graph.Solution);
                selectedProject = graph.SelectedProject;
                loadWarnings = graph.Warnings;
                var loadedDocuments = new Dictionary<string, DocumentId>(StringComparer.Ordinal);
                foreach (var project in workspace.CurrentSolution.Projects)
                {
                    foreach (var loadedDocument in project.Documents)
                    {
                        var path = CheckCompilerInput(loadedDocument.FilePath!);
                        if (externalCompilerInputs.Contains(path))
                        {
                            if (!externalDocuments.TryGetValue(path, out var contexts))
                                externalDocuments[path] = contexts = [];
                            contexts.Add(loadedDocument.Id);
                            loadedDocuments.TryAdd(path, loadedDocument.Id);
                            continue;
                        }
                        if (!loadedDocuments.TryAdd(path, loadedDocument.Id))
                            throw new ProjectLoadException("project_selection_required",
                                "Document belongs to multiple compilation contexts: " + Path.GetRelativePath(root, path),
                                selectedProject, "Select a project with workspace.open project and reload=true; no startup configuration change is required.",
                                workspace.CurrentSolution.Projects.Where(candidate => candidate.Documents.Any(document =>
                                    string.Equals(document.FilePath, path, StringComparison.Ordinal)))
                                    .Select(candidate => (object)new { candidate = Path.GetRelativePath(root, candidate.FilePath!) }).ToArray());
                    }
                }
                foreach (var entry in loadedDocuments) documents.Add(entry.Key, entry.Value);
                projectId = workspace.CurrentSolution.ProjectIds[0];
                await Refresh(token);
                // Compilation is now safe to inspect: all source text came through
                // the bounded snapshot reader, and analyzer/generator references
                // were removed. A partial graph without core types is not usable.
                foreach (var project in workspace.CurrentSolution.Projects)
                {
                    var compilation = await project.GetCompilationAsync(token);
                    if (compilation is null || compilation.GetSpecialType(SpecialType.System_Object).TypeKind == TypeKind.Error)
                        throw new ProjectLoadException("project_load_failed", "Project graph cannot resolve System.Object: " + project.Name,
                            selectedProject, "Inspect the installed targeting packs and required references; the partial graph is not usable.");
                }
                return new
                {
                    root,
                    mode = Mode,
                    fidelity = Mode,
                    selectedProject,
                    loadWarnings,
                    degradedFidelity = loadWarnings.Count > 0,
                    projects = workspace.CurrentSolution.ProjectIds.Count,
                    files = documents.Count,
                    externalCompilerInputCount = externalCompilerInputs.Count,
                    externalCompilerInputs = externalCompilerInputs.Order(StringComparer.Ordinal).Take(32).ToArray(),
                    externalCompilerInputsReadOnly = true,
                    limitations = "Trusted design-time project evaluation; no analyzers or generators. Restore must already be completed by the operator. Reopen after project graph changes."
                };
            }
            projectId = ProjectId.CreateNewId();
            // Only trusted platform assemblies from the worker's own runtime are references.
            var trusted = ((string?)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES") ?? typeof(object).Assembly.Location)
                .Split(Path.PathSeparator).Where(path => File.Exists(path) &&
                    Path.GetDirectoryName(path) == Path.GetDirectoryName(typeof(object).Assembly.Location))
                .Select(path => MetadataReference.CreateFromFile(path));
            workspace.AddProject(ProjectInfo.Create(projectId, VersionStamp.Create(), "FreeFlight source view", "FreeFlight.Source", LanguageNames.CSharp,
                compilationOptions: new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary),
                parseOptions: new CSharpParseOptions(LanguageVersion.CSharp12), metadataReferences: trusted));
            await Refresh(token);
            return new { root, mode = "safe-source", fidelity = Mode, selectedProject, loadWarnings, degradedFidelity = true, files = documents.Count, limitations = "One source compilation; project settings, dependencies, generated sources and analyzers are not evaluated." };
        }
        if (root is null || projectId is null) throw new InvalidOperationException("Open a workspace first");
        if (method is not ("symbols" or "definition" or "references" or "hover" or "diagnostics" or "rename" or "implementations" or "typeInfo" or "signatureHelp" or "workspaceSymbols" or "callHierarchy" or "typeHierarchy"))
            throw new ArgumentException($"Unsupported operation: {method}");
        var requestedFile = args.TryGetProperty("file", out var queryFile) ? CheckPath(queryFile.GetString()!) : null;
        await Refresh(token, requestedFile, method == "rename");
        if (method == "workspaceSymbols")
            return await SemanticQueries.WorkspaceSymbols(workspace.CurrentSolution,
                args.GetProperty("query").GetString() ?? "", token);
        var file = CheckPath(args.GetProperty("file").GetString() ?? throw new ArgumentException("file is required"));
        if (!documents.TryGetValue(file, out var documentId)) throw new ArgumentException("File is not in the C# workspace");
        var document = workspace.CurrentSolution.GetDocument(documentId)!;
        var text = await document.GetTextAsync(token);
        var syntax = await document.GetSyntaxRootAsync(token) ?? throw new InvalidOperationException("Syntax unavailable");
        var model = await document.GetSemanticModelAsync(token) ?? throw new InvalidOperationException("Semantic model unavailable");
        if (method == "symbols")
        {
            var found = new List<object>();
            foreach (var node in syntax.DescendantNodes())
            {
                token.ThrowIfCancellationRequested();
                if (node is not (MemberDeclarationSyntax or VariableDeclaratorSyntax)) continue;
                var symbol = model.GetDeclaredSymbol(node, token);
                if (symbol is null || symbol.IsImplicitlyDeclared) continue;
                // Namespace and partial-type symbols merge declarations across files.
                // An outline location belongs to this declaration, not whichever
                // location happens to be first on the shared semantic symbol.
                var location = symbol.Locations.FirstOrDefault(l => l.IsInSource &&
                    l.SourceTree == node.SyntaxTree && node.Span.Contains(l.SourceSpan));
                if (location is not null) found.Add(new { name = symbol.Name, kind = symbol.Kind.ToString(), detail = symbol.ToDisplayString(), location = Location(location) });
            }
            return found;
        }
        if (method == "diagnostics") return model.GetDiagnostics(cancellationToken: token).Select(d => new
        {
            code = d.Id,
            severity = d.Severity.ToString().ToLowerInvariant(),
            message = d.GetMessage(System.Globalization.CultureInfo.InvariantCulture),
            location = d.Location.IsInSource ? Location(d.Location) : null,
            source = "roslyn-" + Mode
        }).ToArray();
        var line = args.GetProperty("line").GetInt32();
        var character = args.GetProperty("character").GetInt32();
        if (line < 0 || line >= text.Lines.Count || character < 0 || character > text.Lines[line].Span.Length) throw new ArgumentException("Position is outside document");
        var position = text.Lines[line].Start + character;
        var symbolAt = await SymbolFinder.FindSymbolAtPositionAsync(document, position, token);
        if (method == "typeInfo") return SemanticQueries.TypeInfo(model, syntax, position, symbolAt, token);
        if (method == "signatureHelp") return SemanticQueries.SignatureHelp(model, syntax, position, token);
        if (symbolAt is null) return method == "hover" ? new { contents = "" } : Array.Empty<object>();
        switch (method)
        {
            case "implementations": return await SemanticQueries.Implementations(symbolAt, workspace.CurrentSolution, token);
            case "typeHierarchy": return await SemanticQueries.TypeHierarchy(symbolAt, workspace.CurrentSolution, token);
            case "callHierarchy":
                var sourceMethod = await SymbolFinder.FindSourceDefinitionAsync(symbolAt, workspace.CurrentSolution, token) ?? symbolAt;
                return await SemanticQueries.CallHierarchy(sourceMethod, workspace.CurrentSolution, token);
            case "hover": return new { contents = symbolAt.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat), kind = symbolAt.Kind.ToString(), documentation = symbolAt.GetDocumentationCommentXml(cancellationToken: token) };
            case "definition":
                var sourceDefinition = await SymbolFinder.FindSourceDefinitionAsync(symbolAt, workspace.CurrentSolution, token) ?? symbolAt;
                return sourceDefinition.Locations.Where(l => l.IsInSource).Select(Location).ToArray();
            case "references":
                var references = await SymbolFinder.FindReferencesAsync(symbolAt, workspace.CurrentSolution, token);
                return references.SelectMany(r => r.Locations).Select(r => Location(r.Location)).OrderBy(l => JsonSerializer.Serialize(l), StringComparer.Ordinal).ToArray();
            case "rename":
                var name = args.GetProperty("newName").GetString() ?? throw new ArgumentException("newName is required");
                if (!SyntaxFacts.IsValidIdentifier(name)) throw new ArgumentException("newName must be a valid C# identifier");
                if (!symbolAt.Locations.Any(l => l.IsInSource)) throw new ArgumentException("Cannot rename a metadata symbol");
                foreach (var location in symbolAt.Locations.Where(location => location.IsInSource))
                    CheckEditableInput(location.SourceTree!.FilePath);
                var before = workspace.CurrentSolution;
                var after = await Renamer.RenameSymbolAsync(before, symbolAt, new SymbolRenameOptions(), name, token);
                var edits = new List<object>();
                foreach (var changed in after.GetChanges(before).GetProjectChanges().SelectMany(p => p.GetChangedDocuments()))
                {
                    var oldDocument = before.GetDocument(changed)!;
                    var newDocument = after.GetDocument(changed)!;
                    var oldText = await oldDocument.GetTextAsync(token);
                    var oldFile = CheckEditableInput(oldDocument.FilePath!);
                    var changes = await newDocument.GetTextChangesAsync(oldDocument, token);
                    edits.Add(new
                    {
                        file = oldFile,
                        expectedSha256 = fingerprints[oldFile],
                        edits = changes.Select(change => new { range = Range(oldText.Lines.GetLinePositionSpan(change.Span)), newText = change.NewText ?? "" }).ToArray()
                    });
                }
                return new { preview = true, edits };
            default: throw new ArgumentException($"Unsupported operation: {method}");
        }
    }

    private async Task Refresh(CancellationToken token, string? forceFile = null, bool forceAll = false)
    {
        var files = new List<string>();
        var pending = new Stack<string>();
        if (!trustedMsbuild) pending.Push(root!);
        else files.AddRange(documents.Keys);
        long bytes = 0;
        var entries = 0;
        while (pending.TryPop(out var directory))
        {
            foreach (var entry in Directory.EnumerateFileSystemEntries(directory))
            {
                token.ThrowIfCancellationRequested();
                ResourcePolicy.Check("maxDirectoryEntries", root!, entry, ++entries, resources.MaxDirectoryEntries);
                var attributes = File.GetAttributes(entry);
                if ((attributes & FileAttributes.ReparsePoint) != 0) continue;
                if ((attributes & FileAttributes.Directory) != 0)
                {
                    if (!Excluded.Contains(Path.GetFileName(entry))) pending.Push(CheckPath(entry));
                    continue;
                }
                if (!entry.EndsWith(".cs", StringComparison.OrdinalIgnoreCase)) continue;
                var path = CheckPath(entry);
                var length = new FileInfo(path).Length;
                ResourcePolicy.Check("maxFileBytes", root!, path, length, resources.MaxFileBytes);
                bytes += length;
                ResourcePolicy.Check("maxWorkspaceBytes", root!, path, bytes, resources.MaxWorkspaceBytes);
                ResourcePolicy.Check("maxFiles", root!, path, files.Count + 1L, resources.MaxFiles);
                files.Add(path);
            }
        }
        ResourcePolicy.Check("maxFiles", root!, root!, files.Count, resources.MaxFiles);
        bytes = 0; // Count actual bytes again; stat values can change during a read.
        files.Sort(StringComparer.Ordinal);
        var solution = workspace.CurrentSolution;
        var nextDocuments = new Dictionary<string, DocumentId>(documents, StringComparer.Ordinal);
        var nextFingerprints = new Dictionary<string, string>(fingerprints, StringComparer.Ordinal);
        var nextSnapshots = new Dictionary<string, FileSnapshot>(snapshots, StringComparer.Ordinal);
        var present = files.ToHashSet(StringComparer.Ordinal);
        foreach (var removed in documents.Keys.Where(path => !present.Contains(path)).ToArray())
        {
            solution = solution.RemoveDocument(documents[removed]);
            nextDocuments.Remove(removed);
            nextFingerprints.Remove(removed);
            nextSnapshots.Remove(removed);
        }
        foreach (var file in files)
        {
            token.ThrowIfCancellationRequested();
            CheckCompilerInput(file);
            var info = new FileInfo(file);
            var length = info.Length;
            var modified = info.LastWriteTimeUtc.Ticks;
            var generation = Interlocked.Read(ref invalidationGeneration);
            var dirty = dirtyFiles.GetValueOrDefault(file);
            var now = Environment.TickCount64;
            ResourcePolicy.Check("maxFileBytes", root!, file, length, resources.MaxFileBytes);
            if (!forceAll && !string.Equals(file, forceFile, PathComparison) && watcher is not null &&
                snapshots.TryGetValue(file, out var cached) && cached.Length == length && cached.Modified == modified &&
                cached.Generation == generation && cached.Dirty == dirty && now - cached.ValidatedAt < 5000 &&
                documents.ContainsKey(file))
            {
                bytes += length;
                ResourcePolicy.Check("maxWorkspaceBytes", root!, file, bytes, resources.MaxWorkspaceBytes);
                reusedSnapshots++;
                continue;
            }
            // Bounded read even when the file grows after enumeration.
            using var stream = OpenCompilerInput(file);
            using var memory = new MemoryStream();
            using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            var buffer = new byte[8192];
            int count;
            while ((count = await stream.ReadAsync(buffer.AsMemory(), token)) != 0)
            {
                ResourcePolicy.Check("maxFileBytes", root!, file, memory.Length + count, resources.MaxFileBytes);
                bytes += count;
                bytesRead += count;
                ResourcePolicy.Check("maxWorkspaceBytes", root!, file, bytes, resources.MaxWorkspaceBytes);
                hash.AppendData(buffer, 0, count);
                await memory.WriteAsync(buffer.AsMemory(0, count), token);
            }
            memory.Position = 0;
            nextFingerprints[file] = Convert.ToHexString(hash.GetHashAndReset()).ToLowerInvariant();
            nextSnapshots[file] = new FileSnapshot(memory.Length, modified, dirty, generation, now);
            var source = SourceText.From(memory, encoding: Encoding.UTF8);
            if (!documents.TryGetValue(file, out var id))
            {
                id = DocumentId.CreateNewId(projectId!);
                nextDocuments.Add(file, id);
                solution = solution.AddDocument(id, Path.GetFileName(file), source, filePath: file);
            }
            else if (!fingerprints.ContainsKey(file) ||
                !(await solution.GetDocument(id)!.GetTextAsync(token)).ContentEquals(source))
                if (externalDocuments.TryGetValue(file, out var contexts))
                    foreach (var context in contexts)
                        solution = solution.WithDocumentText(context, source);
                else
                    solution = solution.WithDocumentText(id, source);
        }
        if (!workspace.TryApplyChanges(solution)) throw new InvalidOperationException("Could not update workspace");
        snapshots.Clear();
        foreach (var entry in nextSnapshots) snapshots.Add(entry.Key, entry.Value);
        documents.Clear();
        foreach (var entry in nextDocuments) documents.Add(entry.Key, entry.Value);
        fingerprints.Clear();
        foreach (var entry in nextFingerprints) fingerprints.Add(entry.Key, entry.Value);
    }

    // Only documents returned by the explicitly trusted MSBuild graph may enter
    // this exact-file catalogue. Queries cannot register paths or directory grants.
    private string RegisterCompilerInput(string path, string project)
    {
        var full = Path.GetFullPath(path);
        var relative = Path.GetRelativePath(root!, full);
        if (relative != ".." && !relative.StartsWith(".." + Path.DirectorySeparatorChar, PathComparison) && !Path.IsPathRooted(relative))
            return CheckPath(full);
        try
        {
            if (!trustedMsbuild || !Path.IsPathRooted(path)) throw new UnauthorizedAccessException();
            ValidateExternalInput(full);
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            throw new ProjectLoadException("external_compiler_input_rejected", "External compiler input cannot be read safely", selectedProject,
                "Inspect the evaluated Compile item and its path components; symlinks, missing files and directories are rejected. Workspace trust has not been expanded.",
                [new { operation = "register_compiler_input", file = full, project }]);
        }
        externalCompilerInputs.Add(full);
        return full;
    }

    private static void ValidateExternalInput(string path)
    {
        var cursor = Path.GetPathRoot(path)!;
        foreach (var part in path[cursor.Length..].Split(Path.DirectorySeparatorChar, StringSplitOptions.RemoveEmptyEntries))
        {
            cursor = Path.Combine(cursor, part);
            if ((File.GetAttributes(cursor) & FileAttributes.ReparsePoint) != 0)
                throw new UnauthorizedAccessException("External compiler inputs cannot traverse symlinks/reparse points");
        }
        if ((File.GetAttributes(path) & (FileAttributes.Directory | FileAttributes.Device)) != 0)
            throw new UnauthorizedAccessException("Compiler input is not a regular file");
    }

    private string CheckCompilerInput(string path)
    {
        var full = Path.GetFullPath(path);
        if (!externalCompilerInputs.Contains(full)) return CheckPath(full);
        ValidateExternalInput(full);
        return full;
    }

    [DllImport("libc", EntryPoint = "open", SetLastError = true)]
    private static extern int OpenNonBlocking([MarshalAs(UnmanagedType.LPUTF8Str)] string path, int flags);

    private FileStream OpenCompilerInput(string path)
    {
        if (!externalCompilerInputs.Contains(path) || OperatingSystem.IsWindows())
            return new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        // A declared FIFO must not block open before cancellation can be observed.
        // Use platform POSIX flags; descriptors are owned by SafeFileHandle.
        var flags = OperatingSystem.IsMacOS() ? 0x0004 | 0x0100 | 0x1000000 : 0x0800 | 0x20000 | 0x80000;
        var descriptor = OpenNonBlocking(path, flags); // O_RDONLY | NONBLOCK | NOFOLLOW | CLOEXEC
        if (descriptor < 0) throw new IOException("Cannot open external compiler input");
        var handle = new SafeFileHandle((IntPtr)descriptor, ownsHandle: true);
        try
        {
            var stream = new FileStream(handle, FileAccess.Read);
            if (stream.CanSeek) return stream;
            stream.Dispose();
            throw new ProjectLoadException("external_compiler_input_rejected", "External compiler input is not seekable", selectedProject,
                "Use a source file, not a pipe or stream device.", [new { operation = "read_compiler_input", file = path }]);
        }
        catch { handle.Dispose(); throw; }
    }

    private string CheckEditableInput(string path)
    {
        var full = Path.GetFullPath(path);
        if (externalCompilerInputs.Contains(full))
            throw new ProjectLoadException("external_input_read_only", "Rename would modify an external compiler input", selectedProject,
                "External compiler inputs are analysis-only. No partial edit preview is returned.",
                [new { operation = "rename", file = full }]);
        return CheckPath(full);
    }

    private string CheckPath(string path)
    {
        var full = Path.GetFullPath(Path.IsPathRooted(path) ? path : Path.Combine(root!, path));
        var relative = Path.GetRelativePath(root!, full);
        if (relative == ".." || relative.StartsWith(".." + Path.DirectorySeparatorChar, PathComparison) || Path.IsPathRooted(relative)) throw new UnauthorizedAccessException("Path escapes workspace");
        var current = root!;
        foreach (var segment in relative.Split(Path.DirectorySeparatorChar))
        {
            current = Path.Combine(current, segment);
            if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0) throw new UnauthorizedAccessException("Symlink/reparse paths are not supported");
        }
        return full;
    }

    private static string ResolveRoot(string path)
    {
        var current = Path.GetPathRoot(path)!;
        foreach (var segment in path[current.Length..].Split(Path.DirectorySeparatorChar, StringSplitOptions.RemoveEmptyEntries))
        {
            current = Path.Combine(current, segment);
            var info = new DirectoryInfo(current);
            if ((info.Attributes & FileAttributes.ReparsePoint) != 0) current = info.ResolveLinkTarget(true)?.FullName ?? throw new UnauthorizedAccessException("Cannot resolve workspace root");
        }
        return Path.TrimEndingDirectorySeparator(current);
    }

    private static object Location(Location location) => new { file = location.SourceTree?.FilePath, range = Range(location.GetLineSpan().Span) };
    private static object Range(LinePositionSpan span) => new { start = new { line = span.Start.Line, character = span.Start.Character }, end = new { line = span.End.Line, character = span.End.Character } };
    public void Dispose()
    {
        watcher?.Dispose();
        workspace.Dispose();
    }
}
