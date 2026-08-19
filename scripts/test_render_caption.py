import argparse
import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from render_caption import (
    CaptionError,
    _bbox_within,
    _check_negative_space,
    _load_master,
    _publish_no_overwrite,
    _text_samples,
    parse_zone,
    render_caption,
)


class NegativeSpaceTests(unittest.TestCase):
    def test_uniform_zone_passes(self):
        _check_negative_space(Image.new("RGB", (200, 100), (245, 220, 230)), (0, 0, 200, 100))

    def test_busy_zone_fails(self):
        image = Image.new("RGB", (200, 100), (245, 220, 230))
        pixels = image.load()
        for y in range(0, 100, 4):
            for x in range(0, 200, 4):
                pixels[x, y] = (40, 40, 40)
        with self.assertRaises(CaptionError):
            _check_negative_space(image, (0, 0, 200, 100))

    def test_equal_luminance_color_pattern_fails(self):
        image = Image.new("RGB", (200, 100))
        pixels = image.load()
        for y in range(100):
            for x in range(200):
                pixels[x, y] = (255, 0, 0) if (x // 2 + y // 2) % 2 else (0, 130, 0)
        with self.assertRaises(CaptionError):
            _check_negative_space(image, (0, 0, 200, 100))


class CaptionBoundaryTests(unittest.TestCase):
    def test_zone_rejects_nonfinite_numbers(self):
        for value in ("nan,0,0.2,0.2", "0,inf,0.2,0.2", "0,0,-inf,0.2"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                parse_zone(value)

    def test_antialiased_text_cannot_touch_transparency(self):
        image = Image.new("RGBA", (2, 1), (255, 255, 255, 255))
        image.putpixel((1, 0), (255, 255, 255, 0))
        mask = Image.new("L", (2, 1))
        mask.putdata([255, 128])
        with self.assertRaises(CaptionError):
            _text_samples(image, mask)

    def test_text_bbox_must_stay_inside_zone(self):
        self.assertTrue(_bbox_within((10, 10, 20, 20), (5, 5, 25, 25)))
        self.assertFalse(_bbox_within((4, 10, 20, 20), (5, 5, 25, 25)))
        self.assertFalse(_bbox_within((10, 10, 26, 20), (5, 5, 25, 25)))


class CaptionFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_master_rejects_rgb_transparency_and_animation(self):
        transparent = self.root / "transparent.png"
        Image.new("RGB", (20, 20), (255, 0, 255)).save(
            transparent, format="PNG", transparency=(255, 0, 255)
        )
        with self.assertRaises(CaptionError):
            _load_master(transparent)

        animation = self.root / "animation.png"
        Image.new("RGB", (20, 20), "white").save(
            animation,
            format="PNG",
            save_all=True,
            append_images=[Image.new("RGB", (20, 20), "black")],
            duration=100,
            loop=0,
        )
        with self.assertRaises(CaptionError):
            _load_master(animation)

    def test_master_rejects_unnormalized_orientation(self):
        source = self.root / "rotated.png"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (20, 20), "white").save(source, format="PNG", exif=exif)
        with self.assertRaises(CaptionError):
            _load_master(source)

    def test_publish_never_overwrites_an_existing_path(self):
        temporary = self.root / "verified.png"
        output = self.root / "output.png"
        temporary.write_bytes(b"verified")
        output.write_bytes(b"existing")
        with self.assertRaises(CaptionError):
            _publish_no_overwrite(temporary, output)
        self.assertEqual(output.read_bytes(), b"existing")

    def test_render_strips_exif_and_preserves_required_metadata(self):
        source = self.root / "source.png"
        output = self.root / "output.png"
        exif = Image.Exif()
        exif[274] = 1
        exif[270] = "private source note"
        Image.new("RGB", (1600, 1200), (245, 235, 225)).save(
            source,
            format="PNG",
            dpi=(144, 144),
            icc_profile=b"test-profile",
            exif=exif,
        )

        render_caption(source, output, "Soft Bridge", "modern", [(0.05, 0.05, 0.9, 0.4)])

        with Image.open(source) as before, Image.open(output) as after:
            self.assertNotIn("exif", after.info)
            self.assertEqual(after.info.get("icc_profile"), before.info.get("icc_profile"))
            for actual, expected in zip(after.info["dpi"], before.info["dpi"]):
                self.assertTrue(math.isclose(actual, expected, abs_tol=0.02))


if __name__ == "__main__":
    unittest.main()
