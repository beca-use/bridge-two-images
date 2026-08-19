import argparse
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from prepare_text_safe_edit import (
    TextSafeEditError,
    _pixel_box,
    parse_box,
    prepare_edit,
)
from verify_pixel_lock import PixelLockError, verify_allowed_change_mask, verify_locked_mask


class PixelProtectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_protected_box_rejects_nonfinite_numbers(self):
        for value in ("nan,0,0.2,0.2", "0,inf,0.2,0.2", "0,0,-inf,0.2"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                parse_box(value)
        with self.assertRaises(TextSafeEditError):
            _pixel_box((float("nan"), 0, 0.2, 0.2), (100, 100))

    def _rgb(self, name, color=(30, 60, 90), **save_options):
        path = self.root / name
        Image.new("RGB", (4, 4), color).save(path, format="PNG", **save_options)
        return path

    def _mask(self, name, values, mode="L"):
        path = self.root / name
        image = Image.new(mode, (4, 4), 0)
        if mode == "L":
            image.putdata(values)
        image.save(path, format="PNG")
        return path

    def _changed(self, source, name, position):
        path = self.root / name
        with Image.open(source) as opened:
            image = opened.copy()
        image.putpixel(position, (220, 30, 40))
        image.save(path, format="PNG")
        return path

    def test_prepared_masks_enforce_the_same_boundary(self):
        source = self._rgb("source.png")
        base = self.root / "base.png"
        protected = self.root / "protected.png"
        allowed = self.root / "allowed.png"
        backend = self.root / "backend.png"

        report = prepare_edit(
            source, base, protected, allowed, backend,
            [(0.25, 0.25, 0.5, 0.5)],
        )

        self.assertEqual(report.allowed_change_mask, str(allowed))
        self.assertEqual(report.backend_mask, str(backend))
        with Image.open(protected) as image:
            protected_values = list(image.get_flattened_data())
            self.assertEqual(image.mode, "L")
        with Image.open(allowed) as image:
            allowed_values = list(image.get_flattened_data())
            self.assertEqual(image.mode, "L")
        with Image.open(backend) as image:
            backend_alpha = list(image.getchannel("A").get_flattened_data())
            self.assertEqual(image.mode, "RGBA")

        self.assertEqual(allowed_values, [255 - value for value in protected_values])
        self.assertEqual(backend_alpha, protected_values)

        outside_change = self._changed(base, "outside.png", (0, 0))
        verify_locked_mask(base, outside_change, protected)
        verify_allowed_change_mask(base, outside_change, allowed)

        protected_change = self._changed(base, "protected-change.png", (1, 1))
        with self.assertRaises(PixelLockError):
            verify_locked_mask(base, protected_change, protected)
        with self.assertRaises(PixelLockError):
            verify_allowed_change_mask(base, protected_change, allowed)

    def test_exact_canvas_size_must_be_declared_without_resizing(self):
        source = self._rgb("canvas-source.png")
        outputs = [self.root / name for name in ("base.png", "protected.png", "allowed.png", "backend.png")]
        with self.assertRaises(TextSafeEditError):
            prepare_edit(source, *outputs, [(0.25, 0.25, 0.5, 0.5)], (8, 8))

        report = prepare_edit(source, *outputs, [(0.25, 0.25, 0.5, 0.5)], (4, 4))
        self.assertEqual(report.image_size, (4, 4))
        self.assertEqual(source.read_bytes(), outputs[0].read_bytes())

    def test_verifier_rejects_empty_ambiguous_and_backend_masks(self):
        before = self._rgb("before.png")
        after = self._rgb("after.png")
        all_zero = self._mask("all-zero.png", [0] * 16)
        all_white = self._mask("all-white.png", [255] * 16)
        nonbinary = self._mask("nonbinary.png", [0] * 15 + [1])
        backend = self._mask("backend.png", [], mode="RGBA")

        with self.assertRaises(PixelLockError):
            verify_locked_mask(before, after, all_zero)
        with self.assertRaises(PixelLockError):
            verify_allowed_change_mask(before, after, all_zero)
        with self.assertRaises(PixelLockError):
            verify_allowed_change_mask(before, after, all_white)
        with self.assertRaises(PixelLockError):
            verify_locked_mask(before, after, nonbinary)
        with self.assertRaises(PixelLockError):
            verify_allowed_change_mask(before, after, backend)

    def test_verifier_rejects_palette_and_multiframe_pngs(self):
        palette_before = self.root / "palette-before.png"
        palette_after = self.root / "palette-after.png"
        first = Image.new("P", (4, 4), 0)
        second = Image.new("P", (4, 4), 0)
        first.putpalette([0, 0, 0, 255, 255, 255] + [0] * 762)
        second.putpalette([255, 0, 0, 255, 255, 255] + [0] * 762)
        first.save(palette_before, format="PNG")
        second.save(palette_after, format="PNG")
        locked = self._mask("locked.png", [255] * 16)

        with self.assertRaises(PixelLockError):
            verify_locked_mask(palette_before, palette_after, locked)

        animation = self.root / "animation.png"
        Image.new("RGB", (4, 4), "black").save(
            animation,
            format="PNG",
            save_all=True,
            append_images=[Image.new("RGB", (4, 4), "white")],
            duration=100,
            loop=0,
        )
        with self.assertRaises(PixelLockError):
            verify_locked_mask(animation, animation, locked)
        with self.assertRaises(TextSafeEditError):
            prepare_edit(
                animation,
                self.root / "base.png",
                self.root / "protected.png",
                self.root / "allowed.png",
                self.root / "backend-mask.png",
                [(0.25, 0.25, 0.5, 0.5)],
            )

    def test_verifier_rejects_display_metadata_changes(self):
        before = self._rgb("icc-before.png", icc_profile=b"profile-a")
        after = self._rgb("icc-after.png", icc_profile=b"profile-b")
        locked = self._mask("locked.png", [255] * 16)
        with self.assertRaises(PixelLockError):
            verify_locked_mask(before, after, locked)

    def test_prepare_rejects_unnormalized_orientation(self):
        source = self.root / "rotated.png"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (4, 4), "white").save(source, format="PNG", exif=exif)
        with self.assertRaises(TextSafeEditError):
            prepare_edit(
                source,
                self.root / "base.png",
                self.root / "protected.png",
                self.root / "allowed.png",
                self.root / "backend.png",
                [(0.25, 0.25, 0.5, 0.5)],
            )

    def test_prepare_rejects_a_fully_protected_canvas(self):
        source = self._rgb("source.png")
        with self.assertRaises(TextSafeEditError):
            prepare_edit(
                source,
                self.root / "base.png",
                self.root / "protected.png",
                self.root / "allowed.png",
                self.root / "backend.png",
                [(0.0, 0.0, 1.0, 1.0)],
            )


if __name__ == "__main__":
    unittest.main()
