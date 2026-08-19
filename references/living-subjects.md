# Living Subjects

Read this file only when a source contains a person, visible hand, or animal.

## Before Generation

Record the exact number of living subjects and the source-visible anatomy of each. Mark faces, eyes, identity, and expression as `identity_faithful`; compare them to the source rather than demanding identical pixels. Mark pose, silhouette, hands, feet, wings, and limb junctions as `structural`. Upgrade a named region to `exact_pixel` only when the user explicitly requires unchanged pixels. Use the source rather than generic anatomy when a part is genuinely cropped, hidden, or absent.

- A complete visible human hand has one palm and five digits total, including one thumb on the correct side. Fingers must attach naturally, keep plausible order and joints, and remain hidden where the source hides them.
- A normally visible pigeon has one head, one beak, two eyes when the view shows both, two wings, two legs, and two feet. Toes attach to feet and feet attach to legs; perspective or overlap may hide a part but may not create another one.
- Apply equivalent species-appropriate checks to other animals. Do not use the pigeon counts for a different species.

Transparent glass, water, reflections, patterned fabric, foliage, shadows, and media strokes must not be interpreted as extra anatomy. Keep connection paths away from hands, faces, feet, wings, and limb junctions.

## Unlettered Review

Inspect every living subject separately at original resolution. Use temporary close crops for each face, hand, foot, wing, and joint that is not immediately clear. Count visible parts and trace each one back to the body.

Fail on extra, missing, fused, duplicated, disconnected, anatomically reversed, or implausibly joined parts. Fail when the artwork replaces a living part with water, light, paper texture, or another medium. Uncertainty is a failure, not permission to pass.

Keep review crops inside the managed run workspace; never deliver or package them.
