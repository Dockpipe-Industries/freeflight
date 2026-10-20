using System.Text.Json;

namespace FreeFlight.Roslyn;

internal sealed record ResourcePolicy(long MaxFileBytes = 32L * 1024 * 1024,
    long MaxWorkspaceBytes = 512L * 1024 * 1024, long MaxFiles = 50000,
    long MaxDirectoryEntries = 500000)
{
    public static ResourcePolicy Parse(JsonElement args)
    {
        if (!args.TryGetProperty("resources", out var value)) return new();
        if (value.ValueKind != JsonValueKind.Object) throw new ArgumentException("resources must be an object");
        var limits = new Dictionary<string, (long Default, long Maximum)>
        {
            ["maxFileBytes"] = (32L * 1024 * 1024, 256L * 1024 * 1024),
            ["maxWorkspaceBytes"] = (512L * 1024 * 1024, 2L * 1024 * 1024 * 1024),
            ["maxFiles"] = (50000, 200000),
            ["maxDirectoryEntries"] = (500000, 2000000)
        };
        var selected = limits.ToDictionary(item => item.Key, item => item.Value.Default);
        foreach (var item in value.EnumerateObject())
        {
            if (!limits.TryGetValue(item.Name, out var range) || item.Value.ValueKind != JsonValueKind.Number ||
                !item.Value.TryGetInt64(out var number) || number < 1 || number > range.Maximum)
                throw new ArgumentException("Invalid resource setting: " + item.Name);
            selected[item.Name] = number;
        }
        if (selected["maxFileBytes"] > selected["maxWorkspaceBytes"])
            throw new ArgumentException("maxFileBytes must not exceed maxWorkspaceBytes");
        return new(selected["maxFileBytes"], selected["maxWorkspaceBytes"], selected["maxFiles"], selected["maxDirectoryEntries"]);
    }

    public static void Check(string resource, string root, string path, long observed, long limit)
    {
        if (observed > limit) throw new ResourceLimitException(resource, Path.GetRelativePath(root, path), observed, limit);
    }
}

internal sealed class ResourceLimitException(string resource, string path, long observed, long limit)
    : Exception($"Resource limit exceeded: {path} ({resource}: {observed} > {limit})")
{
    public object Detail => new
    {
        code = "resource_limit_exceeded", message = Message, resource, path, observed, limit,
        remediation = $"Increase resources.{resource} in the operator-owned FreeFlight startup configuration within its supported range, or open a smaller workspace."
    };
}
