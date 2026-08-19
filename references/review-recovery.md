# Review And Recovery

Read this file only when the unlettered candidate fails a release check or contains an ambiguous writing-like mark.

## Classify Marks Against The Sources

Reload the matching source region before deciding what a mark is:

- A source-matching logo, brand name, clothing print, or emblem belonging to a primary subject is an `identity_mark`; preserve it accurately when required in the final image. A face is reviewed separately under `identity_faithful`, not classified as a textual or graphic identity mark.
- A plaque, storefront sign, road sign, or architectural inscription physically belonging to a place is `scene_text`; classify it from the source and apply matched-scale review.
- Camera watermarks, timestamps, UI, and later-added signatures are `capture_overlays`; remove them by default.
- Incidental background writing is `context_text`; keep it only when required to prove the scene or anchor.
- Source writing regenerated as different recognizable wording is a `forbidden_mark`; natural loss of `scene_text` legibility is allowed only under `references/scene-text.md`.
- Character-like strokes absent from the source are invented lettering; reject them.
- The intended caption inside the generated candidate is still forbidden because the script must add it later.

Clean removal of text never compensates for erasing an `identity_mark` or `scene_text` region.

## Classify Before Recovery

Record every confirmed failure category, then run the deterministic classifier before any repair or retry:

```powershell
python scripts/classify_recovery.py --failure <category> [--failure <category>] [--no-retry]
```

Use only these categories: `single_local_artifact`, `single_overlay`, `caption_space_optional`, `identity_drift`, `weak_relationship`, `ordinary_staging`, `missing_anchor`, `wrong_identity_mark`, `multiple_defects`, `composition_defect`, `route_incompatible`, `exact_pixel_incompatible`, and `backend_incompatible`.

Follow its action exactly. `local_edit` is allowed only for one bounded defect. `full_regeneration` spends the one artistic retry. `stop` creates no candidate and does not spend a retry for a route incompatibility. `deliver_unlettered` is only for an optional caption failure. Never paste a broad source silhouette over a candidate to repair identity drift, missing anchors, ordinary staging, or a composition defect.

## Diagnose Failures

Choose only the principal failed check:

- **Weak relationship or ordinary staging:** Always use full regeneration with the backup relationship selected before generation. The replacement must show its start region, transition zone, and landing region and pass source dependence, visual continuity, counterfactual review, and the Placement Test. Never use a local edit, decorative connector, or explanation to repair ordinary staging.
- **Protected-route relationship conflict:** If the planned or generated transition crosses an essential scene-text region or living anatomy, treat the route as incompatible. Reprepare the base or choose the backup relationship before the one artistic retry; never repaint the protected region to make the connection fit.
- **Missing anchor evidence:** restore only the lost silhouette, material, color, direction, or source-proving detail.
- **Collage-like composition:** rebuild through one shared field, gesture, material, or medium.
- **Living-subject defect:** use `identity_drift` when the subject no longer reads as the same identity, and `composition_defect` when pose, silhouette, or multiple anatomical regions drift. These require full regeneration. A single small structural artifact may use `single_local_artifact`. Pixel equality is not required unless that region was classified `exact_pixel` before generation.
- **Identity-mark defect:** use a localized edit only when the authentic source pixels can be preserved exactly and verified; never redraw, approximate, or model-repair the mark.
- **Text defect:** remove only unwanted overlays, disallowed context text, or writing absent from the source while locking all allowed identity marks and preserving classified scene text; never remove all text. Restore a compatible source-derived scene-text region or use full regeneration when the generated wording is wrong.
- **Caption space failure:** in `optional` mode, keep the accepted unlettered artwork and skip the caption without spending a retry. In `required` mode, rebuild once around valid edge negative space only when the artistic retry remains; never repaint or flatten the accepted artwork locally just to fit text.
- **Other artifact or ratio defect:** make one correction limited to that defect.

Prefer a local edit only when the classifier returns `local_edit` and the backend supports a tight allowed-change mask. Two or more separated defects require full regeneration while retaining the passing anchors, marks, relationship, composition, palette, and ratio according to their protection levels.

When the relationship and scene-text checks both fail, treat them as separate composition-level defects and use full regeneration. Do not spend the retry removing text from an otherwise ordinary staged scene.

## Retry Limit And Cleanup

Spend at most one artistic retry for the entire task. Count only decoded raster candidates; bounded retries for timeout, connection failure, HTTP 429, or HTTP 5xx do not spend it. Do not retry authentication, validation, or other ordinary HTTP 4xx failures. A suspected mark does not trigger an artistic retry until source comparison confirms a real text defect. Review the retry from scratch against the six core checks in `SKILL.md`.

If the retry fails, deliver no image and state the principal failure. Keep rejected candidates, reference boards, and temporary transport artifacts inside the managed run workspace so the standard cleanup removes them.
