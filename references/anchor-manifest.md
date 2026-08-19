# Anchor Manifest

Before generation, keep one manifest for the two sources in memory. When deterministic validation is needed, pass its JSON through standard input; do not create a plan file:

```powershell
$manifestJson | python scripts/validate_anchor_manifest.py -
```

Each source entry must record:

- `primary_subjects`: the visible main subjects, including a dominant character or branded object;
- `selected_anchor`: the one subject or bounded region chosen for the relationship;
- `retained_evidence`: at least one source-specific property that will remain visible;
- `omitted_content`: every intentionally omitted visible item, with a reason;
- `identity_marks`: each relevant mark with `preserve` or `omit`; an omitted mark also needs a reason.

Choosing a decorative sub-region does not silently erase a dominant subject. It is allowed only when the manifest explicitly records that subject as omitted and the output does not rewrite or imitate its identity marks. The manifest is a planning contract, not a visual approval; the final review still checks that retained evidence is present and omitted marks did not reappear.
