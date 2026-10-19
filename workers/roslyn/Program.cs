using System.Collections.Concurrent;
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

    public static async Task Main()
    {
        using var engine = new SourceEngine();
        using var gate = new SemaphoreSlim(1);
        var active = new ConcurrentDictionary<string, CancellationTokenSource>();
        var jobs = new List<Task>();
        var outputGate = new object();
        void Reply(object value)
        {
            lock (outputGate) Console.WriteLine(JsonSerializer.Serialize(value, Json));
        }
        while (true)
        {
            string? line;
            try { line = ReadBoundedLine(Console.In, 1024 * 1024); }
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
    private const int MaximumFiles = 10000;
    private const int MaximumFileBytes = 2 * 1024 * 1024;
    private const long MaximumWorkspaceBytes = 64L * 1024 * 1024;
    private readonly AdhocWorkspace workspace = new();
    private readonly Dictionary<string, DocumentId> documents = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> fingerprints = new(StringComparer.Ordinal);
    private ProjectId? projectId;
    private string? root;
    private static readonly HashSet<string> Excluded = new(StringComparer.OrdinalIgnoreCase) { ".git", ".hg", "node_modules", "bin", "obj", ".freeflight" };
    private static readonly StringComparison PathComparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;

    public async Task<object> Invoke(string method, JsonElement args, CancellationToken token)
    {
        if (method == "capabilities") return new
        {
            languages = new[] { "csharp" },
            operations = new[] { "symbols", "definition", "references", "hover", "diagnostics", "rename" },
            mode = "safe-source", projectEvaluation = false, edits = "preview-only"
        };
        if (method == "open")
        {
            var requested = Path.GetFullPath(args.GetProperty("root").GetString() ?? throw new ArgumentException("root is required"));
            if (!Directory.Exists(requested)) throw new DirectoryNotFoundException(requested);
            if (args.TryGetProperty("mode", out var mode) && mode.GetString() != "safe-source")
                throw new ArgumentException("Only safe-source mode is supported; MSBuild evaluation is disabled");
            root = ResolveRoot(requested);
            workspace.ClearSolution();
            documents.Clear();
            fingerprints.Clear();
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
            return new { root, mode = "safe-source", files = documents.Count, limitations = "One source compilation; project settings, dependencies, generated sources and analyzers are not evaluated." };
        }
        if (root is null || projectId is null) throw new InvalidOperationException("Open a workspace first");
        if (method is not ("symbols" or "definition" or "references" or "hover" or "diagnostics" or "rename"))
            throw new ArgumentException($"Unsupported operation: {method}");
        await Refresh(token);
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
                var location = symbol.Locations.FirstOrDefault(l => l.IsInSource);
                if (location is not null) found.Add(new { name = symbol.Name, kind = symbol.Kind.ToString(), detail = symbol.ToDisplayString(), location = Location(location) });
            }
            return found;
        }
        if (method == "diagnostics") return model.GetDiagnostics(cancellationToken: token).Select(d => new
        {
            code = d.Id, severity = d.Severity.ToString().ToLowerInvariant(), message = d.GetMessage(System.Globalization.CultureInfo.InvariantCulture),
            location = d.Location.IsInSource ? Location(d.Location) : null, source = "roslyn-safe-source"
        }).ToArray();
        var line = args.GetProperty("line").GetInt32();
        var character = args.GetProperty("character").GetInt32();
        if (line < 0 || line >= text.Lines.Count || character < 0 || character > text.Lines[line].Span.Length) throw new ArgumentException("Position is outside document");
        var position = text.Lines[line].Start + character;
        var symbolAt = await SymbolFinder.FindSymbolAtPositionAsync(document, position, token);
        if (symbolAt is null) return method == "hover" ? new { contents = "" } : Array.Empty<object>();
        switch (method)
        {
            case "hover": return new { contents = symbolAt.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat), kind = symbolAt.Kind.ToString(), documentation = symbolAt.GetDocumentationCommentXml(cancellationToken: token) };
            case "definition": return symbolAt.Locations.Where(l => l.IsInSource).Select(Location).ToArray();
            case "references":
                var references = await SymbolFinder.FindReferencesAsync(symbolAt, workspace.CurrentSolution, token);
                return references.SelectMany(r => r.Locations).Select(r => Location(r.Location)).OrderBy(l => JsonSerializer.Serialize(l), StringComparer.Ordinal).ToArray();
            case "rename":
                var name = args.GetProperty("newName").GetString() ?? throw new ArgumentException("newName is required");
                if (!SyntaxFacts.IsValidIdentifier(name)) throw new ArgumentException("newName must be a valid C# identifier");
                if (!symbolAt.Locations.Any(l => l.IsInSource)) throw new ArgumentException("Cannot rename a metadata symbol");
                var before = workspace.CurrentSolution;
                var after = await Renamer.RenameSymbolAsync(before, symbolAt, new SymbolRenameOptions(), name, token);
                var edits = new List<object>();
                foreach (var changed in after.GetChanges(before).GetProjectChanges().SelectMany(p => p.GetChangedDocuments()))
                {
                    var oldDocument = before.GetDocument(changed)!;
                    var newDocument = after.GetDocument(changed)!;
                    var oldText = await oldDocument.GetTextAsync(token);
                    var oldFile = CheckPath(oldDocument.FilePath!);
                    var changes = await newDocument.GetTextChangesAsync(oldDocument, token);
                    edits.Add(new { file = oldFile, expectedSha256 = fingerprints[oldFile],
                        edits = changes.Select(change => new { range = Range(oldText.Lines.GetLinePositionSpan(change.Span)), newText = change.NewText ?? "" }).ToArray() });
                }
                return new { preview = true, edits };
            default: throw new ArgumentException($"Unsupported operation: {method}");
        }
    }

    private async Task Refresh(CancellationToken token)
    {
        var files = new List<string>();
        var pending = new Stack<string>();
        pending.Push(root!);
        long bytes = 0;
        var entries = 0;
        while (pending.TryPop(out var directory))
        {
            foreach (var entry in Directory.EnumerateFileSystemEntries(directory))
            {
                token.ThrowIfCancellationRequested();
                if (++entries > 100000) throw new InvalidOperationException("Workspace exceeds 100000 directory entries");
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
                if (length > MaximumFileBytes) throw new InvalidOperationException("C# file exceeds 2 MiB limit");
                bytes += length;
                if (bytes > MaximumWorkspaceBytes || files.Count >= MaximumFiles) throw new InvalidOperationException("Workspace exceeds safe-source limits");
                files.Add(path);
            }
        }
        files.Sort(StringComparer.Ordinal);
        var solution = workspace.CurrentSolution;
        var nextDocuments = new Dictionary<string, DocumentId>(documents, StringComparer.Ordinal);
        var nextFingerprints = new Dictionary<string, string>(fingerprints, StringComparer.Ordinal);
        var present = files.ToHashSet(StringComparer.Ordinal);
        foreach (var removed in documents.Keys.Where(path => !present.Contains(path)).ToArray())
        {
            solution = solution.RemoveDocument(documents[removed]);
            nextDocuments.Remove(removed);
            nextFingerprints.Remove(removed);
        }
        foreach (var file in files)
        {
            token.ThrowIfCancellationRequested();
            CheckPath(file);
            // Bounded read even when the file grows after enumeration.
            using var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
            using var memory = new MemoryStream();
            var buffer = new byte[8192];
            int count;
            while ((count = await stream.ReadAsync(buffer.AsMemory(), token)) != 0)
            {
                if (memory.Length + count > MaximumFileBytes) throw new InvalidOperationException("C# file exceeds 2 MiB limit");
                await memory.WriteAsync(buffer.AsMemory(0, count), token);
            }
            memory.Position = 0;
            nextFingerprints[file] = Convert.ToHexString(SHA256.HashData(memory.ToArray())).ToLowerInvariant();
            var source = SourceText.From(memory, encoding: Encoding.UTF8);
            if (!documents.TryGetValue(file, out var id))
            {
                id = DocumentId.CreateNewId(projectId!);
                nextDocuments.Add(file, id);
                solution = solution.AddDocument(id, Path.GetFileName(file), source, filePath: file);
            }
            else if (!(await solution.GetDocument(id)!.GetTextAsync(token)).ContentEquals(source)) solution = solution.WithDocumentText(id, source);
        }
        if (!workspace.TryApplyChanges(solution)) throw new InvalidOperationException("Could not update workspace");
        documents.Clear();
        foreach (var entry in nextDocuments) documents.Add(entry.Key, entry.Value);
        fingerprints.Clear();
        foreach (var entry in nextFingerprints) fingerprints.Add(entry.Key, entry.Value);
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
    public void Dispose() => workspace.Dispose();
}
