import unittest

from classify_recovery import RecoveryError, classify_recovery


class RecoveryPolicyTests(unittest.TestCase):
    def test_identity_drift_and_weak_relationship_require_full_regeneration(self):
        for failure in ("identity_drift", "weak_relationship", "ordinary_staging", "missing_anchor"):
            with self.subTest(failure=failure):
                decision = classify_recovery([failure])
                self.assertEqual(decision.action, "full_regeneration")
                self.assertTrue(decision.spends_artistic_retry)

    def test_multiple_defects_never_use_local_edit(self):
        decision = classify_recovery(["single_local_artifact", "single_overlay"])
        self.assertEqual(decision.action, "full_regeneration")

    def test_incompatible_route_stops_without_spending_retry(self):
        for failure in ("route_incompatible", "exact_pixel_incompatible", "backend_incompatible"):
            with self.subTest(failure=failure):
                decision = classify_recovery([failure])
                self.assertEqual(decision.action, "stop")
                self.assertFalse(decision.spends_artistic_retry)

    def test_only_one_bounded_defect_may_use_local_edit(self):
        decision = classify_recovery(["single_local_artifact"])
        self.assertEqual(decision.action, "local_edit")
        self.assertTrue(decision.spends_artistic_retry)

    def test_optional_caption_failure_delivers_unlettered_without_retry(self):
        decision = classify_recovery(["caption_space_optional"])
        self.assertEqual(decision.action, "deliver_unlettered")
        self.assertFalse(decision.spends_artistic_retry)

    def test_no_retry_remaining_stops_required_recovery(self):
        self.assertEqual(classify_recovery(["identity_drift"], False).action, "stop")
        self.assertEqual(classify_recovery(["single_overlay"], False).action, "stop")

    def test_unknown_or_empty_failure_is_rejected(self):
        with self.assertRaises(RecoveryError):
            classify_recovery([])
        with self.assertRaises(RecoveryError):
            classify_recovery(["looks_bad"])


if __name__ == "__main__":
    unittest.main()
