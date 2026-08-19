# Text-Safe Route

Read this file when a source contains `essential_scene_text` and the selected backend cannot demonstrate reliable text preservation in direct two-reference generation.

## Prepare The Base

Use the source containing the essential scene text as the edit base. Choose a target ratio and canvas that preserve the base dimensions and do not crop, resize, rotate, or perspective-transform any protected text region. If that is impossible, stop before generation.

Create the base copy and masks inside the managed run workspace:

```powershell
python scripts/prepare_text_safe_edit.py `
  --input bridge-base.png `
  --base run/base.png `
  --protected-mask run/protected.png `
  --allowed-change-mask run/allowed-change.png `
  --backend-mask run/backend-mask.png `
  --canvas-size WIDTHxHEIGHT `
  --protected-box x,y,w,h
```

Use one normalized `--protected-box` per essential text region. Box coordinates must be finite numbers. For an exact-pixel route, `--canvas-size` must equal the decoded source dimensions; the helper never resizes or crops the base. It checks resource limits before full decoding and refuses inputs larger than 128 MiB, 8192 pixels on either side, or 20 megapixels total. It also refuses non-PNG, multiframe, non-RGB/RGBA, unnormalized-orientation, invalid-box, fully protected canvas, dimension-change, and output-overwrite cases. The base copy remains byte-identical to the source.

## Mask Contract

Read the three mask definitions in `references/protected-editing.md`. The helper emits all three without requiring manual inversion:

- `run/protected.png` is the locked mask: `255` protects and `0` does not.
- `run/allowed-change.png` is the allowed-change mask: `255` may change and `0` must not.
- `run/backend-mask.png` is the RGBA backend mask for the currently documented route: opaque alpha protects and transparent alpha may be edited.

Verify the backend mask semantics with documentation or a dry-run before the first real edit; never assume a grayscale or alpha convention. Do not pass `run/backend-mask.png` directly to `verify_pixel_lock.py`.

Send the second image as a separate reference. Request the approved relationship in the editable area, keep the protected text region untouched, and request no new writing. Preserve the base canvas dimensions and color mode.

The relationship's transition zone must stay inside the editable area and must not cross an `exact_pixel` region. For a living subject, keep it away from the face, eyes, body, paws, and limb junctions as well. If the planned water, light, material, or media relay cannot fit around those regions, stop before generation and choose another relationship or base preparation.

## Acceptance

After the candidate decodes, run `scripts/verify_pixel_lock.py --locked-mask run/protected.png` against the protected source region and `--allowed-change-mask run/allowed-change.png` against the prepared editable area. A later localized repair requires a tighter allowed-change mask matching only that repair. Never reuse the backend mask for either check. Any protected-pixel, out-of-boundary, dimension, color-mode, frame, orientation, or display-metadata change fails. If the route cannot honor this contract, stop and report the incompatibility; do not fall back to direct whole-image generation.
