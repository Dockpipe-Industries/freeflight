using System.Buffers;
using System.Buffers.Binary;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace FreeFlight.Roslyn;

// Fresh request-local metadata, not a watcher cache or permission to read contents.
// Unsupported filesystems, malformed/incomplete records and exhausted enumeration
// budgets fall back to the caller's original per-file validation in original order.
internal sealed class DarwinMetadataBatch : IDisposable
{
    internal readonly record struct Metadata(long Length, long Modified);
    private const uint Common = 0x80000000 | 0x20000000 | 1 | 8 | 0x400 | 0x40000;
    private const uint FileLength = 0x200;
    private const uint IdentityCommon = 0x80000000 | 4 | 8 | 0x02000000;
    private const int RecordSize = 68;
    private readonly IReadOnlyDictionary<string, Dictionary<string, string>> members;
    private readonly Action<string> validateParent;
    private readonly Dictionary<string, SafeFileHandle> handles = new(StringComparer.Ordinal);
    internal int RetainedHandles => handles.Count;
    private readonly Dictionary<string, Metadata> values = new(StringComparer.Ordinal);
    private readonly byte[] buffer = ArrayPool<byte>.Shared.Rent(65536);
    private static readonly UTF8Encoding Utf8 = new(false, true);
    private string? directory;
    private long remaining;
    internal long Calls { get; private set; }
    internal long Entries { get; private set; }
    internal long Hits { get; private set; }

    [StructLayout(LayoutKind.Sequential)]
    private struct Attributes
    {
        public ushort Count, Reserved;
        public uint Common, Volume, Directory, File, Fork;
    }
    [DllImport("libSystem.B.dylib", EntryPoint = "open", SetLastError = true)]
    private static extern int Open([MarshalAs(UnmanagedType.LPUTF8Str)] string path, int flags);
    [DllImport("libSystem.B.dylib", EntryPoint = "openat", SetLastError = true)]
    private static extern int OpenAt(SafeFileHandle parent, [MarshalAs(UnmanagedType.LPUTF8Str)] string name, int flags);
    [DllImport("libSystem.B.dylib", EntryPoint = "getattrlistbulk", SetLastError = true)]
    private static extern int Bulk(SafeFileHandle fd, ref Attributes attributes, byte[] buffer, nuint size, ulong options);
    [DllImport("libSystem.B.dylib", EntryPoint = "fgetattrlist", SetLastError = true)]
    private static extern int DescriptorAttributes(SafeFileHandle fd, ref Attributes attributes, byte[] buffer, nuint size, ulong options);
    [DllImport("libSystem.B.dylib", EntryPoint = "getattrlist", SetLastError = true)]
    private static extern int PathAttributes([MarshalAs(UnmanagedType.LPUTF8Str)] string path, ref Attributes attributes, byte[] buffer, nuint size, ulong options);

    internal DarwinMetadataBatch(IReadOnlyDictionary<string, Dictionary<string, string>> members, long budget, Action<string> validateParent)
    {
        this.members = members;
        this.validateParent = validateParent;
        remaining = Math.Max(0, budget);
    }

    internal bool TryGet(string file, string parent, CancellationToken token, out Metadata metadata)
    {
        token.ThrowIfCancellationRequested();
        if (!string.Equals(directory, parent, StringComparison.Ordinal))
        {
            directory = parent;
            values.Clear();
            if (remaining > 0 && members.TryGetValue(parent, out var selected) && selected.Count >= 32)
            {
                try { if (!Load(parent, selected, token)) values.Clear(); }
                catch (Exception error) when (error is DecoderFallbackException or OverflowException or ArgumentException)
                { values.Clear(); }
            }
        }
        var found = values.TryGetValue(file, out metadata);
        if (found) Hits++;
        return found;
    }

    private bool Load(string parent, Dictionary<string, string> selected, CancellationToken token)
    {
        var (handle, owned) = OpenDirectory(parent, token);
        using var temporaryHandle = owned ? handle : null;
        if (handle is null) return false;
        var identityAttributes = new Attributes { Count = 5, Common = IdentityCommon };
        var identity = new byte[44];
        if (DescriptorAttributes(handle, ref identityAttributes, identity, 44, 8) != 0 || !ValidIdentity(identity)) return false;
        var attributes = new Attributes { Count = 5, Common = Common, File = FileLength };
        // A crowded directory cannot cause unbounded work for a sparse trusted graph.
        long directoryBudget = Math.Min(remaining, selected.Count * 2L + 256);
        Span<char> nameBuffer = stackalloc char[1024];
        var names = selected.GetAlternateLookup<ReadOnlySpan<char>>();
        while (values.Count < selected.Count && directoryBudget > 0)
        {
            token.ThrowIfCancellationRequested();
            var capacity = (int)Math.Min(65536, directoryBudget * RecordSize);
            Calls++;
            var count = Bulk(handle, ref attributes, buffer, (nuint)capacity, 8); // PACK_INVAL_ATTRS
            if (count < 0) return false;
            if (count == 0) break;
            if (count > directoryBudget || count > remaining || count > capacity / RecordSize) return false;
            remaining -= count; directoryBudget -= count; Entries += count;
            var offset = 0;
            for (var i = 0; i < count; i++)
            {
                token.ThrowIfCancellationRequested();
                if (offset > capacity - RecordSize) return false;
                var recordLength = checked((int)U32(buffer, offset));
                if (recordLength < RecordSize || recordLength > capacity - offset) return false;
                var valid = U32(buffer, offset + 4);
                // Packed invalid attributes have fixed offsets, but never carry authority.
                if ((valid & Common) == Common && (U32(buffer, offset + 16) & FileLength) != 0 &&
                    U32(buffer, offset + 24) == 0 && U32(buffer, offset + 36) == 1 &&
                    (U32(buffer, offset + 56) & 0x00800000) == 0) // regular, not firmlink
                {
                    var nameOffset = checked(28 + I32(buffer, offset + 28));
                    var nameLength = checked((int)U32(buffer, offset + 32));
                    if (nameOffset < RecordSize || nameLength <= 1 || nameOffset > recordLength - nameLength ||
                        buffer[offset + nameOffset + nameLength - 1] != 0) return false;
                    if (nameLength - 1 > nameBuffer.Length) return false;
                    var chars = Utf8.GetChars(buffer.AsSpan(offset + nameOffset, nameLength - 1), nameBuffer);
                    var name = nameBuffer[..chars];
                    if (name.IndexOf('/') >= 0 || name.IndexOf('\0') >= 0) return false;
                    if (names.TryGetValue(name, out var full))
                    {
                        var length = I64(buffer, offset + 60);
                        var seconds = I64(buffer, offset + 40);
                        var nanos = I64(buffer, offset + 48);
                        if (length < 0 || nanos < 0 || nanos >= 1_000_000_000) return false;
                        var ticks = checked(DateTime.UnixEpoch.Ticks + seconds * TimeSpan.TicksPerSecond + nanos / 100);
                        if (ticks < DateTime.MinValue.Ticks || ticks > DateTime.MaxValue.Ticks ||
                            !values.TryAdd(full, new Metadata(length, ticks))) return false;
                    }
                }
                offset += recordLength;
            }
        }
        // The directory handle must still denote the same directory at this path.
        // A replacement, symlink, unsupported identity or missing directory discards
        // every prefetched value. The caller then checks each original path afresh.
        var current = new byte[44];
        token.ThrowIfCancellationRequested();
        var matches = PathAttributes(parent, ref identityAttributes, current, 44, 9) == 0 &&
            ValidIdentity(current) && identity.AsSpan(24, 20).SequenceEqual(current.AsSpan(24, 20));
        validateParent(parent); // Complete uncached validation immediately before admission.
        return matches;
    }

    private (SafeFileHandle? Handle, bool Owned) OpenDirectory(string path, CancellationToken token)
    {
        // At most 64 directory handles live for this request. Every opened
        // component uses O_NOFOLLOW, including the uncached fallback after the cap.
        // The caller still validates the current complete path and final identity.
        const int flags = 0x00100000 | 0x100 | 0x01000000;
        if (handles.TryGetValue(path, out var found)) return (found, false);
        SafeFileHandle? current = null;
        var owned = false;
        try
        {
            if (!handles.TryGetValue("/", out current))
            {
                var descriptor = Open("/", flags);
                if (descriptor < 0) return (null, false);
                current = new((IntPtr)descriptor, ownsHandle: true);
                if (handles.Count < 64) handles.Add("/", current); else owned = true;
            }
            var prefix = "";
            foreach (var component in path.Split('/', StringSplitOptions.RemoveEmptyEntries))
            {
                token.ThrowIfCancellationRequested();
                prefix += "/" + component;
                if (handles.TryGetValue(prefix, out var cached))
                {
                    if (owned) current.Dispose();
                    current = cached; owned = false; continue;
                }
                var descriptor = OpenAt(current, component, flags);
                if (descriptor < 0) return (null, false);
                var next = new SafeFileHandle((IntPtr)descriptor, ownsHandle: true);
                if (owned) current.Dispose();
                current = next;
                owned = handles.Count >= 64;
                if (!owned) handles.Add(prefix, current);
            }
            var result = (current, owned); current = null; owned = false; return result;
        }
        finally { if (owned) current?.Dispose(); }
    }

    private static bool ValidIdentity(byte[] data) => U32(data, 0) == 44 &&
        (U32(data, 4) & IdentityCommon) == IdentityCommon && U32(data, 32) == 2;
    private static uint U32(byte[] data, int offset) => BinaryPrimitives.ReadUInt32LittleEndian(data.AsSpan(offset, 4));
    private static int I32(byte[] data, int offset) => BinaryPrimitives.ReadInt32LittleEndian(data.AsSpan(offset, 4));
    private static long I64(byte[] data, int offset) => BinaryPrimitives.ReadInt64LittleEndian(data.AsSpan(offset, 8));
    public void Dispose()
    {
        foreach (var handle in handles.Values) handle.Dispose();
        handles.Clear();
        ArrayPool<byte>.Shared.Return(buffer);
    }
}
