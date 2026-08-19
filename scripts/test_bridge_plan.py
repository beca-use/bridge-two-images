import argparse
import unittest

from validate_bridge_plan import BridgePlanError, assess_plan, parse_size


class BridgePlanTests(unittest.TestCase):
    def test_identity_faithful_route_allows_normal_canvas_change(self):
        report = assess_plan(
            [(1279, 1706), (716, 1439)], (1024, 1536),
            ["identity_faithful", "structural"], canvas_operation="resample",
        )
        self.assertEqual((report.status, report.route), ("ok", "identity-faithful"))

    def test_exact_route_blocks_resampling_before_generation(self):
        report = assess_plan(
            [(1279, 1706), (716, 1439)], (1024, 1536),
            ["exact_pixel", "structural"], canvas_operation="resample",
            backend_mask_supported=True,
        )
        self.assertEqual(report.status, "blocked")
        self.assertIn("resampled", report.reason)

    def test_exact_route_requires_matching_canvas_for_same_size(self):
        report = assess_plan(
            [(1279, 1706), (716, 1439)], (1279, 1706),
            ["exact_pixel", "structural"], backend_mask_supported=True,
        )
        self.assertEqual((report.status, report.route), ("ok", "exact-edit"))

    def test_two_exact_sources_need_deterministic_compositing(self):
        report = assess_plan(
            [(100, 100), (100, 100)], (100, 100),
            ["exact_pixel", "exact_pixel"], backend_mask_supported=True,
        )
        self.assertEqual(report.status, "blocked")
        self.assertIn("deterministic compositing", report.reason)

        report = assess_plan(
            [(100, 100), (100, 100)], (100, 100),
            ["exact_pixel", "exact_pixel"], deterministic_composite=True,
        )
        self.assertEqual((report.status, report.route), ("ok", "exact-composite"))

    def test_exact_route_requires_verified_mask_or_composite(self):
        report = assess_plan(
            [(100, 100), (100, 100)], (100, 100),
            ["exact_pixel", "structural"],
        )
        self.assertEqual(report.status, "blocked")

    def test_invalid_source_count_and_size_are_rejected(self):
        with self.assertRaises(BridgePlanError):
            assess_plan([(100, 100)], (100, 100), ["structural"])
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_size("1024x0")


if __name__ == "__main__":
    unittest.main()
