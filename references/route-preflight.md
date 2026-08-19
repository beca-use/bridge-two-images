# Route Preflight

Read this file before selecting a generation backend when any required region is `exact_pixel`.

Run the deterministic checker before generation:

```powershell
python scripts/validate_bridge_plan.py `
  --source-size WIDTHxHEIGHT `
  --source-size WIDTHxHEIGHT `
  --target-size WIDTHxHEIGHT `
  --protection-level exact_pixel|identity_faithful|structural `
  --protection-level exact_pixel|identity_faithful|structural `
  --canvas-operation same-size|contain-no-resize|resample|crop
```

The checker is a feasibility gate, not a visual approval. An `identity-faithful` route may resize or crop, subject to later visual review. An `exact_pixel` route cannot resample or crop the locked source region, and it requires a verified backend mask or deterministic compositing. Exact regions in both sources require deterministic compositing; a normal two-reference generation call is not enough. A blocked result must stop before backend selection, generation, caption rendering, or artistic retry.
