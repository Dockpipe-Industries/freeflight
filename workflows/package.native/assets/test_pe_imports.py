# SPDX-License-Identifier: Apache-2.0
import struct
import tempfile
import unittest
from pathlib import Path
from pe_imports import core_imports, verify_core_runtime


def fixture(name='KERNEL32.dll', delay=False):
    """Small PE32+ layout with a section-backed import descriptor and DLL name."""
    data = bytearray(1024)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<H', data, 0x86, 1)
    struct.pack_into('<H', data, 0x94, 240)
    struct.pack_into('<H', data, 0x98, 0x20b)
    struct.pack_into('<I', data, 0x98 + 108, 16)
    directory, stride, index = (13, 32, 1) if delay else (1, 20, 3)
    struct.pack_into('<II', data, 0x98 + 112 + directory * 8, 0x1000, stride * 2)
    struct.pack_into('<IIII', data, 0x98 + 240 + 8, 512, 0x1000, 512, 512)
    if delay:
        struct.pack_into('<I', data, 512, 1)
    struct.pack_into('<I', data, 512 + index * 4, 0x1100)
    encoded = name.encode('ascii') + b'\0'
    data[768:768 + len(encoded)] = encoded
    return data


class PEImports(unittest.TestCase):
    def test_regular_and_delay_import_names(self):
        for delay in (False, True):
            self.assertEqual(core_imports(fixture(delay=delay)), ['kernel32.dll'])

    def test_dynamic_runtime_rejected_and_system_import_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / 'freeflight.exe'
            binary.write_bytes(fixture())
            self.assertEqual(verify_core_runtime(binary), ['kernel32.dll'])
            for name in ('VCRUNTIME140.dll', 'MSVCP140.dll', 'CONCRT140.dll', 'VCOMP140.dll'):
                for delay in (False, True):
                    binary.write_bytes(fixture(name, delay))
                    with self.assertRaisesRegex(RuntimeError, 'VC\\+\\+ runtime'):
                        verify_core_runtime(binary)

    def test_truncated_headers_and_unmapped_names_fail_closed(self):
        for data in (b'', fixture()[:180], fixture()[:530]):
            with self.assertRaises(ValueError):
                core_imports(data)
        data = fixture()
        struct.pack_into('<I', data, 512 + 12, 0xffffffff)
        with self.assertRaisesRegex(ValueError, 'RVA'):
            core_imports(data)

    def test_unterminated_import_directory_rejected(self):
        data = fixture()
        struct.pack_into('<I', data, 0x98 + 112 + 8 + 4, 20)
        with self.assertRaisesRegex(ValueError, 'Unterminated'):
            core_imports(data)

    def test_legacy_delay_addresses_rejected(self):
        data = fixture(delay=True)
        struct.pack_into('<I', data, 512, 0)
        with self.assertRaisesRegex(ValueError, 'non-RVA'):
            core_imports(data)


if __name__ == '__main__':
    unittest.main()
