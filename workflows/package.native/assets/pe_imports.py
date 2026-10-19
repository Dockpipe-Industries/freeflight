"""Inspect the native core's direct PE imports without executing it or needing VS tools.

Layout: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
This is a packaging gate, not a general PE parser or transitive dependency audit.
"""
import struct


def core_imports(data):
    def fields(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(data):
            raise ValueError("Truncated PE structure")
        return struct.unpack_from(fmt, data, offset)

    if data[:2] != b'MZ':
        raise ValueError("Missing DOS signature")
    pe, = fields('<I', 0x3c)
    if data[pe:pe + 4] != b'PE\0\0':
        raise ValueError("Missing PE signature")
    sections, = fields('<H', pe + 6)
    optional_size, = fields('<H', pe + 20)
    optional = pe + 24
    magic, = fields('<H', optional)
    if magic != 0x20b or optional_size < 112:
        raise ValueError("Expected PE32+ native core")
    directory_count, = fields('<I', optional + 108)
    if directory_count < 14 or optional_size < 112 + directory_count * 8:
        raise ValueError("Missing PE import directories")
    section_table = optional + optional_size
    ranges = []
    for index in range(sections):
        _, rva, raw_size, raw_offset = fields('<IIII', section_table + index * 40 + 8)
        ranges.append((rva, raw_size, raw_offset))

    def offset(rva, size):
        matches = [raw + rva - base for base, length, raw in ranges
                   if base <= rva and rva + size <= base + length]
        if len(matches) != 1 or matches[0] + size > len(data):
            raise ValueError("Unmapped or ambiguous PE RVA")
        return matches[0]

    def dll_name(rva):
        name = bytearray()
        for index in range(256):
            char = data[offset(rva + index, 1)]
            if char == 0:
                if not name:
                    raise ValueError("Empty PE import name")
                return name.decode('ascii').lower()
            name.append(char)
        raise ValueError("Unterminated PE import name")

    names = set()
    for directory, stride, name_index in ((1, 20, 3), (13, 32, 1)):
        rva, size = fields('<II', optional + 112 + directory * 8)
        if rva == 0 and size == 0:
            continue
        if not rva or size < stride:
            raise ValueError("Invalid PE import directory")
        for position in range(0, size - stride + 1, stride):
            descriptor = fields('<' + 'I' * (stride // 4), offset(rva + position, stride))
            if not any(descriptor):
                break
            if directory == 13 and descriptor[0] != 1:
                raise ValueError("Unsupported non-RVA delay import")
            names.add(dll_name(descriptor[name_index]))
        else:
            raise ValueError("Unterminated PE import directory")
    if not names:
        raise ValueError("Native core has no inspectable imports")
    return sorted(names)


def verify_core_runtime(binary):
    imports = core_imports(binary.read_bytes())
    forbidden = [name for name in imports if name.startswith(('vcruntime', 'msvcp', 'concrt', 'vcomp'))]
    if forbidden:
        raise RuntimeError("Native core requires unbundled VC++ runtime DLLs: " + ', '.join(forbidden))
    return imports
