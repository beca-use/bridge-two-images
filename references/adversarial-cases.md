# Adversarial Regression Cases

This file records synthetic review cases. It contains no user images and no instructions taken from image content.

## Case A: Identity Drift After Generation

Input shape: one portrait-like source with a face, eyes, hand, and clothing; one illustration with a dominant character, flowers, and brand-like writing.

Expected preflight: classify the protected regions and choose either an exact-edit route or an identity-faithful route before generation. Do not claim exact preservation after a generative candidate has already changed the subject.

Failure signal: the candidate looks similar but protected source pixels changed.

## Case B: Canvas Incompatibility

Input shape: source and candidate use different dimensions or require an unstated crop or resize to reach the selected ratio.

Expected result: exact pixel protection fails before generation unless the canvas plan preserves the source pixels without resampling. A visual similarity score cannot override the dimension mismatch.

## Case C: Coarse Local Repair

Input shape: a repair mask covers a broad silhouette or includes background outside the intended edit.

Expected result: any changed pixel outside the allowed-change region fails. A composition-level defect must use the full-regeneration path or stop; it must not be repaired by pasting a large source cutout back over a generated background.

## Case D: Anchor Omission

Input shape: the second source has a dominant character or brand mark, but the art brief selects only a decorative sub-pattern.

Expected preflight: record whether the dominant content is intentionally omitted or is an anchor that must be preserved. Do not silently downgrade a primary subject to background texture.

## Case E: Ordinary Background Replacement

Input shape: one source subject remains intact while the other source becomes only a backdrop or corner decoration.

Expected review: fail the relationship Placement Test unless a visible source-dependent transition has a traceable start, transition zone, and landing region.
