# Relationship Quality

Read this file after selecting both anchors and again during the unlettered review.

## Require A Visible Evidence Path

Before generation, identify all three parts of the primary relationship:

1. a **start region** containing source-specific evidence from Image A;
2. a visible **transition zone** where contour, material, light, reflection, or medium changes state;
3. a **landing region** containing source-specific evidence from Image B.

Each part must have an intended canvas location and remain visually traceable without the delivery explanation. The backup relationship may be simpler, but it must define the same three parts.

Use material translation, media relay, a contour that visibly changes state across a boundary, a source-caused light or reflection passage, or a shared distilled field as the primary relationship. Shared color, matching perspective, realistic scale, contact shadow, common lighting, proximity, and gaze or direction without a visible carrier are supporting evidence only. They cannot serve as the primary relationship alone.

For a living subject, keep the transition zone outside the body. Start from source-specific gaze, pose, nearby fabric, furniture, light, shadow, or another nonliving carrier; never transform anatomy to make the relationship stronger.

When an `exact_pixel` scene-text region is present, the start region, transition zone, and landing region must be planned around it. The transition must not cross that region or living anatomy; a relationship that requires repainting either is incompatible with the text-safe route.

Before generation, keep the relationship plan in memory and validate its JSON through standard input; do not create a plan file:

```powershell
$relationshipJson | python scripts/validate_relationship_plan.py -
```

The plan must name its relationship type, distinct source-specific evidence at both ends, start region, transition zone, carrier, visible state change, and landing region. It must explicitly confirm that removing either source breaks the relationship and that the literal composition is not ordinary staging. A rejected plan does not consume an artistic retry because generation has not started.

## Placement Test

Describe the candidate literally before interpreting it. If the description reduces to "Image A is in, on, or in front of Image B," ordinary travel staging, background replacement, or a subject pasted into the other scene, it always fails. Natural perspective, scale, lighting, and contact shadow do not rescue it.

Remove either anchor mentally. If the remaining image still reads as a complete ordinary scene and no transition path is broken, the relationship fails. Decorative lines, ribbons, frames, labels, or an explanation cannot supply the missing relationship.

## Review The Path

At original resolution, point to the start region, transition zone, and landing region in the candidate. Fail when any part is missing, generic, hidden, disconnected, or visible only after reading the explanation. A failed Placement Test is an overall composition defect and requires full regeneration with the backup relationship; never repair it locally.
