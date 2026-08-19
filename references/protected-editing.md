# Protection Levels And Exact Editing

Read this file before generation when either source contains a living subject, an authentic logo, brand text, other identity-critical text, or an explicit unchanged-pixel request. Read it again before accepting any local edit.

## Protection Levels

Assign every required output region exactly one level before generation:

- `exact_pixel`: source pixels must remain identical. Use this for a required authentic logo, brand text, identity-critical text, or any region the user explicitly requires unchanged.
- `identity_faithful`: the generated result must remain recognizably the same subject at matched scale. Use this by default for faces, eyes, identity, and expression.
- `structural`: counts, attachments, pose, silhouette, continuity, and source-visible anatomy must remain correct. Use this for hands, feet, wings, limbs, joints, pose, and body silhouette.

Do not use "protected" without naming the level. `identity_faithful` and `structural` are strict visual release checks, but they do not imply byte-identical pixels. A user request for exact preservation upgrades the named region to `exact_pixel`.

## Exact-Pixel Preflight

For every `exact_pixel` region, record its source pixels, mask, and intended placement before generation.

`scene_text` is not `exact_pixel` merely because it contains writing. Apply the source-relative rules in `references/scene-text.md`. Upgrade it only when the user explicitly requires unchanged pixels or when it is a required identity mark; readable wording can require exact textual accuracy without requiring identical pixels.

- With one source containing `exact_pixel` regions, use that source as the edit base. Require mask editing that preserves canvas dimensions, color mode, and source bytes; declare the exact canvas size before preparation.
- With `exact_pixel` regions in both sources, continue only when deterministic masking or compositing can preserve both regions exactly.
- Stop before generation when the chosen ratio, crop, resize, perspective change, fold, reflection, or surface transformation would resample a protected region and deterministic canvas preparation cannot keep its pixels unchanged.
- State the exact incompatibility when reliable protection is impossible. Do not ask the model to redraw or repair a face, logo, or identity-critical text.

## Pixel Verification

Keep three binary mask types distinct:

- A `locked mask` is a single-channel `L` verification mask containing only `0` and `255`. Pixels at `255` must remain unchanged and are passed only to `--locked-mask`.
- An `allowed-change mask` is a separate single-channel `L` verification mask containing only `0` and `255`. Pixels at `255` may change and pixels at `0` must remain unchanged; it is passed only to `--allowed-change-mask`.
- A `backend mask` is a transport-specific edit mask whose channel and alpha meaning comes from the verified backend contract. Never infer its meaning from its filename or appearance, and never pass it to either verifier option unless it has first been converted to the exact corresponding verification-mask semantics.

A locked mask must select at least one protected pixel. A localized allowed-change mask must contain both an allowed region and an unchanged region; otherwise it does not prove edit locality.

Run this section only for `exact_pixel` regions and local-edit boundaries. Before and after images must be fully decodable, single-frame RGB or RGBA PNGs with orientation normalized into raster pixels. Each image and mask must be no larger than 128 MiB, 8192 pixels on either side, or 20 megapixels total; the verifier checks these limits before full decoding. Their dimensions, color mode, ICC profile, gamma, chromaticity, sRGB intent, and transparency metadata must match. The verifier rejects palette images, animation, ambiguous masks, and presentation-metadata changes rather than treating them as pixel-equivalent.

After an edit, run `scripts/verify_pixel_lock.py` at original resolution:

```powershell
python scripts/verify_pixel_lock.py --before SOURCE.png --after CANDIDATE.png --locked-mask PROTECTED.png
```

Every nonzero mask pixel is locked and must match exactly. A successful visual resemblance is not a substitute for this check.

For any localized repair, also verify that nothing outside the allowed-change mask changed:

```powershell
python scripts/verify_pixel_lock.py --before BEFORE_EDIT.png --after AFTER_EDIT.png --allowed-change-mask ALLOWED_CHANGE_MASK.png
```

Every zero mask pixel must match exactly. Any dimension or color-mode mismatch fails. Keep masks in the managed run workspace, keep verification results in memory, and do not deliver either.
