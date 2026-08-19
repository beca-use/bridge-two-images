import unittest

from validate_relationship_plan import RelationshipPlanError, validate_relationship_plan


def _plan(**updates):
    plan = {
        "relationship_type": "media_relay",
        "source_a_evidence": "portrait hat fibers",
        "source_b_evidence": "pink flower contours",
        "start_region": "upper edge of the source hat",
        "transition_zone": "air above and beside the hat",
        "transition_carrier": "soft fibers becoming paper petals",
        "state_change": "fibers separate into source-shaped flower contours",
        "landing_region": "flower cluster derived from source B",
        "breaks_without_source_a": True,
        "breaks_without_source_b": True,
        "ordinary_staging": False,
    }
    plan.update(updates)
    return plan


class RelationshipPlanTests(unittest.TestCase):
    def test_complete_source_dependent_relationship_passes(self):
        self.assertEqual(validate_relationship_plan(_plan())["relationship_type"], "media_relay")

    def test_background_replacement_and_co_location_fail(self):
        for kind in ("background_replacement", "co_location", "decorative_connector"):
            with self.subTest(kind=kind), self.assertRaises(RelationshipPlanError):
                validate_relationship_plan(_plan(relationship_type=kind))

    def test_missing_transition_component_fails(self):
        for key in ("start_region", "transition_zone", "transition_carrier", "state_change", "landing_region"):
            with self.subTest(key=key), self.assertRaises(RelationshipPlanError):
                validate_relationship_plan(_plan(**{key: ""}))

    def test_shared_color_is_not_distinct_source_evidence(self):
        with self.assertRaises(RelationshipPlanError):
            validate_relationship_plan(_plan(source_a_evidence="pink", source_b_evidence="pink"))

    def test_counterfactual_must_break_without_either_source(self):
        with self.assertRaises(RelationshipPlanError):
            validate_relationship_plan(_plan(breaks_without_source_b=False))
        with self.assertRaises(RelationshipPlanError):
            validate_relationship_plan(_plan(ordinary_staging=True))


if __name__ == "__main__":
    unittest.main()
