import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from image_safety import ImageSafetyError, validate_image_dimensions, validate_input_file
from prepare_text_safe_edit import TextSafeEditError, prepare_edit
from render_caption import CaptionError, _load_master
from verify_pixel_lock import PixelLockError, _load_raster


class ImageSafetyTests(unittest.TestCase):
    @staticmethod
    def _oversized_png(path: Path) -> None:
        def chunk(kind: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
            )

        header = struct.pack(">IIBBBBB", 5000, 5000, 8, 2, 0, 0, 0)
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(b""))
            + chunk(b"IEND", b"")
        )

    def test_rejects_excessive_dimensions_and_pixel_count(self):
        for size in ((8193, 1), (5000, 5000), (0, 100)):
            with self.subTest(size=size), self.assertRaises(ImageSafetyError):
                validate_image_dimensions(size, "Test image")

        validate_image_dimensions((4096, 4096), "Test image")

    def test_rejects_oversized_input_file_before_decode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.png"
            with path.open("wb") as stream:
                stream.truncate(128 * 1024 * 1024 + 1)
            with self.assertRaises(ImageSafetyError):
                validate_input_file(path, "Test image")

    def test_all_decode_entrypoints_reject_oversized_canvas_before_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "oversized.png"
            self._oversized_png(source)

            with self.assertRaises(CaptionError):
                _load_master(source)
            with self.assertRaises(PixelLockError):
                _load_raster(source, "Before image")
            with self.assertRaises(TextSafeEditError):
                prepare_edit(
                    source,
                    root / "base.png",
                    root / "protected.png",
                    root / "allowed.png",
                    root / "backend.png",
                    [(0, 0, 0.1, 0.1)],
                )


if __name__ == "__main__":
    unittest.main()
