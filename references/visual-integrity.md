# Visual Integrity

Read this file for every task before generation and during the unlettered review.

## Build The Risk Inventory

Record only risks visible in the sources:

- exact count and arrangement of primary subjects;
- living anatomy, hands, faces, feet, wings, and limb junctions;
- repeated parts, symmetry, attachments, wheels, doors, handles, and structural joints;
- transparent, reflective, watery, glossy, overlapping, or partially occluded regions;
- perspective-sensitive buildings, vehicles, furniture, and rigid objects;
- `identity_marks`, `scene_text`, `capture_overlays`, `context_text`, and possible writing-like decoration.

Convert active risks into explicit invariants in the art brief. Use source-derived counts and structure. Do not invent hidden parts: an occluded part stays occluded unless the source clearly proves its continuation.

Assign every protected region one explicit level from `references/protected-editing.md`. Human faces, eyes, and expression are `identity_faithful` by default. Hands, pose, silhouette, and anatomy are `structural`. A required authentic logo, brand text, identity-critical text, or region the user explicitly requires unchanged is `exact_pixel`. Never use the unqualified word "protected" in the risk inventory.

## Mark Policy

- `identity_marks` belong to a primary subject and prove identity. Preserve the authentic spelling, symbol geometry, color, orientation, and source-relative position. A small mark need not become clearer than its source.
- `scene_text` is physically part of a place or built scene. Preserve and review it using `references/scene-text.md`; candidate blur never changes its class.
- `capture_overlays` were added by a camera, app, or later publishing step. Remove them unless the user explicitly asks to keep them.
- `context_text` belongs to the photographed environment. Preserve it only when it proves the selected scene or anchor; otherwise remove it cleanly.
- `forbidden_marks` did not exist in the source or incorrectly rewrite a source mark. They always fail review.

Never ask the image model to rewrite an `identity_mark`. When an authentic mark is required in the final image, keep its source pixels under `exact_pixel` protection; do not imitate or model-repair it. Review a face under `identity_faithful` protection against the source for recognizable identity, expression, eye placement, and facial proportions, but do not require byte-identical pixels unless the user explicitly requested them. If an exact mark cannot blend naturally into a curved, folded, reflective, or transformed surface, stop before generation or fail the candidate.

## Release Audit

Review at original resolution rather than relying on a fit-to-screen view. Make temporary close crops whenever a critical feature is small or visually crowded.

For every active risk, compare source and candidate and record `pass` or `fail` in memory. Check subject count, part count, attachment, continuity, symmetry, occlusion, perspective, reflections, text, and identity marks. Extra, missing, fused, disconnected, misspelled, or structurally impossible content fails. If the reviewer cannot decide confidently, record fail.

Visual inspection cannot approve an `exact_pixel` region or a local-edit boundary by itself. Run the exact pixel checks in `references/protected-editing.md`; any changed locked pixel or changed pixel outside the allowed-change mask fails. Do not run pixel equality against `identity_faithful` or `structural` regions unless they were explicitly upgraded to `exact_pixel` before generation.

One localized defect may be repaired locally. Two or more separated defects, or a defect caused by the overall composition, require full regeneration. Spend at most one retry for the task and never trade one passed invariant for another.
