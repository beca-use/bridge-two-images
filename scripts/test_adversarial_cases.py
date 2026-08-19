import tempfile
import unittest
from pathlib import Path

from PIL import Image

from verify_pixel_lock import PixelLockError, verify_allowed_change_mask, verify_locked_mask


class AdversarialBridgeCasesTests(unittest.TestCase):
    """Small synthetic cases mirroring observed bridge-review failures."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _image(self, name, size, color):
        path = self.root / name
        Image.new("RGB", size, color).save(path, format="PNG")
        return path

    def _mask(self, name, size, allowed_box):
        path = self.root / name
        mask = Image.new("L", size, 0)
        left, top, right, bottom = allowed_box
        for y in range(top, bottom):
            for x in range(left, right):
                mask.putpixel((x, y), 255)
        mask.save(path, format="PNG")
        return path

    def test_resized_or_cropped_candidate_cannot_claim_exact_source_pixels(self):
        before = self._image("source.png", (8, 10), (20, 40, 60))
        after = self._image("different-canvas.png", (6, 8), (20, 40, 60))
        locked = self._mask("locked.png", (6, 8), (1, 1, 5, 7))

        with self.assertRaises(PixelLockError):
            verify_locked_mask(before, after, locked)

    def test_coarse_local_repair_cannot_change_outside_allowed_region(self):
        before = self._image("before.png", (16, 16), (20, 40, 60))
        after = self._image("after.png", (16, 16), (20, 40, 60))
        with Image.open(after) as opened:
            changed = opened.copy()
        changed.putpixel((7, 7), (220, 30, 40))
        changed.putpixel((1, 1), (220, 30, 40))
        changed.save(after, format="PNG")
        allowed = self._mask("allowed.png", (16, 16), (4, 4, 12, 12))

        with self.assertRaises(PixelLockError):
            verify_allowed_change_mask(before, after, allowed)

    def test_clean_local_edit_is_distinguished_from_coarse_repair(self):
        before = self._image("clean-before.png", (16, 16), (20, 40, 60))
        after = self._image("clean-after.png", (16, 16), (20, 40, 60))
        with Image.open(after) as opened:
            changed = opened.copy()
        changed.putpixel((7, 7), (220, 30, 40))
        changed.save(after, format="PNG")
        allowed = self._mask("clean-allowed.png", (16, 16), (4, 4, 12, 12))

        report = verify_allowed_change_mask(before, after, allowed)
        self.assertEqual(report.changed_locked_pixels, 0)


if __name__ == "__main__":
    unittest.main()
