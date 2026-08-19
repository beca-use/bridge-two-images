import unittest

from protection_policy import ProtectionLevel, classify_protection, requires_pixel_verification


class ProtectionPolicyTests(unittest.TestCase):
    def test_faces_default_to_identity_faithful_not_pixel_exact(self):
        for kind in ("face", "eyes", "expression"):
            with self.subTest(kind=kind):
                level = classify_protection(kind)
                self.assertEqual(level, ProtectionLevel.IDENTITY_FAITHFUL)
                self.assertFalse(requires_pixel_verification(level))

    def test_anatomy_defaults_to_structural_review(self):
        for kind in ("hand", "foot", "wing", "pose", "silhouette", "limb_junction"):
            with self.subTest(kind=kind):
                self.assertEqual(classify_protection(kind), ProtectionLevel.STRUCTURAL)

    def test_selected_identity_marks_require_exact_pixels(self):
        for kind in ("logo", "brand_text", "identity_critical_text"):
            with self.subTest(kind=kind):
                level = classify_protection(kind)
                self.assertEqual(level, ProtectionLevel.EXACT_PIXEL)
                self.assertTrue(requires_pixel_verification(level))

    def test_explicit_exact_request_upgrades_any_required_region(self):
        self.assertEqual(
            classify_protection("face", exact_requested=True),
            ProtectionLevel.EXACT_PIXEL,
        )

    def test_unknown_region_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_protection("important-looking-area")


if __name__ == "__main__":
    unittest.main()
