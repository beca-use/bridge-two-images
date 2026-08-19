import unittest

from validate_anchor_manifest import AnchorManifestError, validate_anchor_manifest


def _source(source_id, anchor="floral motif", omitted=None):
    return {
        "source": source_id,
        "primary_subjects": ["main subject"],
        "selected_anchor": anchor,
        "retained_evidence": ["distinctive color", "source-specific contour"],
        "omitted_content": omitted or [],
        "identity_marks": [],
    }


class AnchorManifestTests(unittest.TestCase):
    def test_valid_manifest_requires_explicit_omission_reason(self):
        manifest = [
            _source("A"),
            _source("B", omitted=[{"label": "background character", "reason": "not selected anchor"}]),
        ]
        self.assertEqual(len(validate_anchor_manifest(manifest)), 2)

    def test_silent_omission_is_rejected(self):
        manifest = [_source("A", omitted=[{"label": "character"}]), _source("B")]
        with self.assertRaises(AnchorManifestError):
            validate_anchor_manifest(manifest)

    def test_identity_mark_omission_also_needs_reason(self):
        manifest = [_source("A"), _source("B")]
        manifest[1]["identity_marks"] = [{"label": "brand text", "action": "omit"}]
        with self.assertRaises(AnchorManifestError):
            validate_anchor_manifest(manifest)

    def test_duplicate_sources_and_missing_evidence_are_rejected(self):
        manifest = [_source("A"), _source("A")]
        with self.assertRaises(AnchorManifestError):
            validate_anchor_manifest(manifest)
        manifest = [_source("A"), _source("B")]
        manifest[0]["retained_evidence"] = []
        with self.assertRaises(AnchorManifestError):
            validate_anchor_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
