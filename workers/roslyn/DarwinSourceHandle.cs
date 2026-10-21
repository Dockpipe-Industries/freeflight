using System.Buffers.Binary;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

namespace FreeFlight.Roslyn;

// Serial, request-local open: kernel path resolution rejects every symlink and
// descriptor metadata admits only regular files. No persistent authority/cache.
internal static class DarwinSourceHandle
{
    [StructLayout(LayoutKind.Sequential)]
    private struct Attributes
    {
        public ushort Count, Reserved;
        public uint Common, Volume, Directory, File, Fork;
    }

    [DllImport("libSystem.B.dylib", EntryPoint = "open", SetLastError = true)]
    private static extern int NativeOpen([MarshalAs(UnmanagedType.LPUTF8Str)] string path, int flags);
    [DllImport("libSystem.B.dylib", EntryPoint = "fgetattrlist", SetLastError = true)]
    private static extern int DescriptorAttributes(SafeFileHandle descriptor, ref Attributes attributes,
        byte[] buffer, nuint size, ulong options);

    internal static FileStream Open(string path, string root, Func<FileStream> fallback)
    {
        var full = Path.GetFullPath(path);
        var relative = Path.GetRelativePath(root, full);
        if (relative == ".." || relative.StartsWith("../", StringComparison.Ordinal) || Path.IsPathRooted(relative))
            throw new UnauthorizedAccessException("Path escapes workspace");
        // O_NOFOLLOW_ANY must not be combined with O_NOFOLLOW on Darwin.
        const int flags = 0x20000000 | 0x01000000 | 0x00000004;
        var fd = NativeOpen(full, flags);
        // Unsupported capability and ordinary open errors retain serial path/error
        // handling. Never retry with unchecked, weaker flags.
        if (fd < 0) return fallback();
        SafeFileHandle? handle = new((IntPtr)fd, ownsHandle: true);
        try
        {
            const uint common = 0x80000000 | 8; // returned attrs, object type
            var attributes = new Attributes { Count = 5, Common = common };
            var data = new byte[28];
            if (DescriptorAttributes(handle, ref attributes, data, 28, 8) != 0 ||
                BinaryPrimitives.ReadUInt32LittleEndian(data) != 28 ||
                (BinaryPrimitives.ReadUInt32LittleEndian(data.AsSpan(4)) & common) != common)
            {
                handle.Dispose(); handle = null;
                return fallback();
            }
            if (BinaryPrimitives.ReadUInt32LittleEndian(data.AsSpan(24)) != 1)
                throw new UnauthorizedAccessException("Compiler input is not a regular file");
            var stream = new FileStream(handle, FileAccess.Read);
            handle = null; // Stream owns the descriptor, including read failures.
            return stream;
        }
        finally { handle?.Dispose(); }
    }
}
