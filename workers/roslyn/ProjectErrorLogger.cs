using System.Collections;
using Microsoft.Build.Framework;
using Microsoft.Build.Logging;

namespace FreeFlight.Roslyn;

/// <summary>
/// Roslyn's remote build host only honors BinaryLogger, not an arbitrary ILogger.
/// Replay private, short-lived logs to recover real error severity and evaluated
/// assets paths. Never publish logs or retain project imports in them.
/// </summary>
internal sealed class ProjectErrorLogger : IDisposable
{
    private readonly DirectoryInfo directory = Directory.CreateTempSubdirectory("freeflight-msbuild-");
    private readonly List<object> errors = [];
    private readonly Dictionary<string, string> assets = new(OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal);
    private bool restoreRequired;
    public BinaryLogger Logger { get; }

    public ProjectErrorLogger()
    {
        if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(directory.FullName, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
        // Roslyn forwards Parameters as the remote logger path before Initialize;
        // its generated numeric suffix preserves these logger options.
        Logger = new BinaryLogger { Parameters = Path.Combine(directory.FullName, "load.binlog") + ";ProjectImports=None;OmitInitialInfo" };
        // Roslyn prefers a non-null FileName property over Parameters if a future
        // SDK supplies one. That would discard our import-exclusion options.
        if (typeof(BinaryLogger).GetProperty("FileName")?.GetValue(Logger) is not null)
        {
            Dispose();
            throw new ProjectLoadException("project_load_failed", "The installed MSBuild binary logger is incompatible with private diagnostic capture", null,
                "Use a qualified SDK whose BinaryLogger forwards Parameters without a FileName override; project imports must remain excluded.");
        }
    }

    public Dictionary<string, string> Read(string root, string selected, Func<string, string> checkPath, CancellationToken token)
    {
        var logs = directory.GetFiles("*.binlog");
        if (logs.Length == 0 || logs.Length > 16)
            throw new ProjectLoadException("project_load_failed", "MSBuild did not provide bounded diagnostic evidence", selected,
                "Check compatibility of the installed SDK with the bundled Roslyn worker.");
        long bytes = 0;
        long events = 0;
        long characters = 0;
        foreach (var log in logs)
        {
            token.ThrowIfCancellationRequested();
            bytes += log.Length;
            if (log.Length > 64L * 1024 * 1024 || bytes > 256L * 1024 * 1024)
                throw new ProjectLoadException("project_load_failed", "MSBuild diagnostic log exceeded the replay budget", selected, "Open a smaller project graph.");
            var replay = new BinaryLogReplayEventSource();
            replay.AnyEventRaised += (_, value) =>
            {
                token.ThrowIfCancellationRequested();
                if (value is ProjectEvaluationFinishedEventArgs evaluated) CaptureProperties(evaluated.ProjectFile, evaluated.Properties);
                if (++events > 2_000_000) throw new InvalidDataException("MSBuild diagnostic event budget exceeded");
            };
            replay.ErrorRaised += (_, error) =>
            {
                characters += (error.Message?.Length ?? 0) + (error.ProjectFile?.Length ?? 0);
                if (errors.Count >= 2048 || characters > 256 * 1024) throw new InvalidDataException("MSBuild error budget exceeded");
                errors.Add(new { code = error.Code, message = error.Message, project = error.ProjectFile, severity = "Error" });
                restoreRequired |= error.Code is "NETSDK1004" or "NETSDK1064";
            };
            replay.ProjectStarted += (_, project) => CaptureProperties(project.ProjectFile, project.Properties);
            try { replay.Replay(log.FullName, token); }
            catch (Exception exception) when (exception is not OperationCanceledException)
            {
                throw new ProjectLoadException("project_load_failed", "Cannot verify MSBuild diagnostic evidence", selected,
                    "Inspect SDK compatibility or select a smaller project graph.", [new { message = exception.Message }]);
            }
        }
        if (errors.Count > 0)
            throw new ProjectLoadException(restoreRequired ? "restore_required" : "project_load_failed", "MSBuild reported project-load errors", selected,
                restoreRequired ? "Required restore assets or packages are missing. Explicitly restore the selected trusted project before reopening."
                    : "Resolve the reported MSBuild errors, including any warnings promoted to errors. No restore is automatically indicated.", errors.ToArray());
        foreach (var entry in assets)
        {
            checkPath(entry.Key);
            var relative = Path.GetRelativePath(root, entry.Value);
            if (Path.IsPathRooted(relative) || relative == ".." || relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal))
                throw new ProjectLoadException("project_load_failed", "Evaluated restore assets escape the authorized workspace", selected,
                    "Keep trusted project restore assets inside the authorized workspace.");
            if (!File.Exists(entry.Value))
                throw new ProjectLoadException("restore_required", "Evaluated restore assets are missing: " + relative, selected,
                    "Explicitly restore the selected trusted project before reopening; design-time loading can otherwise return an incomplete graph.");
            checkPath(entry.Value);
        }
        return assets;
    }

    private void CaptureProperties(string? projectFile, IEnumerable? properties)
    {
        if (projectFile is null || properties is null) return;
        foreach (var item in properties)
        {
            string? name = null, value = null;
            if (item is DictionaryEntry entry) { name = entry.Key as string; value = entry.Value as string; }
            else if (item is KeyValuePair<string, string> pair) { name = pair.Key; value = pair.Value; }
            if (name != "ProjectAssetsFile" || string.IsNullOrWhiteSpace(value)) continue;
            if (assets.Count >= 256 && !assets.ContainsKey(projectFile)) throw new InvalidDataException("MSBuild project evidence budget exceeded");
            var path = Path.GetFullPath(value, Path.GetDirectoryName(projectFile)!);
            if (assets.TryGetValue(projectFile, out var prior) && prior != path)
                throw new InvalidDataException("Conflicting evaluated restore asset paths");
            assets[projectFile] = path;
        }
    }

    public void Dispose()
    {
        try { directory.Delete(recursive: true); }
        catch (IOException) { Console.Error.WriteLine("Could not remove temporary MSBuild diagnostic directory: " + directory.FullName); }
        catch (UnauthorizedAccessException) { Console.Error.WriteLine("Could not remove temporary MSBuild diagnostic directory: " + directory.FullName); }
    }
}
