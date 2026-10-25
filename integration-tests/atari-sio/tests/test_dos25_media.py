import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'boot-app/make-dos25-atr.py'
spec = importlib.util.spec_from_file_location('dos25_media', path)
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)


class MediaTests(unittest.TestCase):
    def test_missing_and_changed_source_leave_outputs_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'out'
            out.mkdir()
            sentinel = out / 'dos25-clean.atr'
            sentinel.write_bytes(b'unchanged')
            with self.assertRaises(OSError):
                media.build(root / 'missing', out)
            source = root / 'bad'
            source.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                media.build(source, out)
            self.assertEqual(sentinel.read_bytes(), b'unchanged')
            self.assertEqual(source.read_bytes(), b'changed')

    def test_successful_build_contents_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = bytearray(16 + 720 * 128)
            image[:2] = b'\x96\x02'
            vtoc = media.sector(image, 360)
            vtoc[3:5] = (32).to_bytes(2, 'little')
            for n in range(4, 36):
                vtoc[10 + n // 8] |= 0x80 >> (n % 8)
            source = root / 'source.atr'
            source.write_bytes(image)
            contents = [bytes([i]) * (i * 80 + 1) for i in range(1, 6)]
            for directory in ('a', 'b'):
                out = root / directory
                out.mkdir()
                for (local, _), content in zip(media.FILES, contents):
                    (out / local).write_bytes(content)
                with patch.object(media, 'SOURCE_SHA256', hashlib.sha256(image).hexdigest()):
                    media.build(source, out)
                self.assertEqual((out / 'dos25-clean.atr').read_bytes(), image)
                result = (out / 'dos25-resident.atr').read_bytes()
                used = sum((len(x) + 124) // 125 for x in contents)
                self.assertEqual(int.from_bytes(media.sector(result, 360)[3:5], 'little'), 32 - used)
                for i, ((_, name), expected) in enumerate(zip(media.FILES, contents)):
                    entry = media.sector(result, 361)[i * 16:(i + 1) * 16]
                    stem, ext = name.split('.')
                    self.assertEqual(bytes(entry[5:16]), (stem.ljust(8) + ext.ljust(3)).encode())
                    n = int.from_bytes(entry[3:5], 'little')
                    data = bytearray()
                    while n:
                        self.assertFalse(media.sector(result, 360)[10 + n // 8] & (0x80 >> (n % 8)))
                        block = media.sector(result, n)
                        self.assertEqual(block[125] >> 2, i)
                        data.extend(block[:block[127]])
                        n = ((block[125] & 3) << 8) | block[126]
                    self.assertEqual(data, expected)
            self.assertEqual((root / 'a/dos25-resident.atr').read_bytes(), (root / 'b/dos25-resident.atr').read_bytes())
            self.assertEqual(source.read_bytes(), image)

    def test_aliases_and_disk_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.write_bytes(b'unchanged')
            alias = root / 'alias'
            alias.hardlink_to(source)
            with self.assertRaises(ValueError):
                media.guard_aliases([source], [alias])
            with self.assertRaises(ValueError):
                media.guard_aliases([], [source, alias])
            image = bytearray(16 + 720 * 128)
            with self.assertRaisesRegex(ValueError, 'disk full'):
                media.add_file(image, 'TEST.BAS', b'x')
            self.assertEqual(source.read_bytes(), b'unchanged')

    def test_sector_chain_and_alias_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = bytearray(16 + 720 * 128)
            image[:2] = b'\x96\x02'
            vtoc = media.sector(image, 360)
            vtoc[3:5] = (2).to_bytes(2, 'little')
            vtoc[10] = 0x0c  # sectors 4 and 5
            media.add_file(image, 'TEST.BAS', bytes(range(200)))
            entry = media.sector(image, 361)[:16]
            self.assertEqual(bytes(entry[:5]), b'\x42\x02\x00\x04\x00')
            self.assertEqual(bytes(media.sector(image, 4)[125:]), b'\x00\x05\x7d')
            self.assertEqual(bytes(media.sector(image, 5)[125:]), b'\x00\x00\x4b')
            self.assertEqual(int.from_bytes(vtoc[3:5], 'little'), 0)
            with self.assertRaises(ValueError):
                media.add_file(image, 'TEST.BAS', b'x')
            source = root / 'dos25-clean.atr'
            source.write_bytes(image)
            import hashlib
            with patch.object(media, 'SOURCE_SHA256', hashlib.sha256(image).hexdigest()):
                with self.assertRaises(ValueError):
                    media.build(source, root)
            self.assertEqual(source.read_bytes(), image)

if __name__ == '__main__':
    unittest.main()
