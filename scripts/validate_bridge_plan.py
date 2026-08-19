#!/usr/bin/env python3
"""Validate canvas and exact-protection prerequisites before image generation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

from protection_policy import ProtectionLevel


class BridgePlanError(ValueError):
    pass


@dataclass(frozen=True)
class BridgePlanReport:
    status: str
    route: str | None
    reason: str


def parse_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError("Size must use WIDTHxHEIGHT, for example 1024x1536.") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Size dimensions must be positive.")
    return width, height


def assess_plan(
    source_sizes: list[tuple[int, int]],
    target_size: tuple[int, int],
    protection_levels: list[str],
    *,
    canvas_operation: str = "same-size",
    backend_mask_supported: bool = False,
    deterministic_composite: bool = False,
) -> BridgePlanReport:
    if len(source_sizes) != 2:
        raise BridgePlanError("Exactly two source sizes are required.")
    if len(protection_levels) != 2:
        raise BridgePlanError("Provide one protection level for each source.")
    if canvas_operation not in {"same-size", "contain-no-resize", "resample", "crop"}:
        raise BridgePlanError("Unknown canvas operation.")
    exact_indices = [
        index for index, level in enumerate(protection_levels)
        if level == ProtectionLevel.EXACT_PIXEL.value
    ]
    if exact_indices:
        if canvas_operation in {"resample", "crop"}:
            return BridgePlanReport(
                "blocked", None,
                "An exact-pixel region cannot be resampled or cropped before generation.",
            )
        if not backend_mask_supported and not deterministic_composite:
            return BridgePlanReport(
                "blocked", None,
                "Exact-pixel protection requires a verified mask route or deterministic compositing.",
            )
        if len(exact_indices) == 2 and not deterministic_composite:
            return BridgePlanReport(
                "blocked", None,
                "Exact-pixel regions in both sources require deterministic compositing.",
            )
        if canvas_operation == "same-size" and source_sizes[exact_indices[0]] != target_size:
            return BridgePlanReport(
                "blocked", None,
                "The exact-pixel source and target canvas dimensions differ.",
            )
        route = "exact-composite" if len(exact_indices) == 2 else "exact-edit"
        return BridgePlanReport("ok", route, "Exact-pixel prerequisites are compatible.")

    return BridgePlanReport(
        "ok", "identity-faithful", "No exact-pixel region requires a deterministic lock route."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-size", action="append", required=True, type=parse_size)
    parser.add_argument("--target-size", required=True, type=parse_size)
    parser.add_argument(
        "--protection-level", action="append", required=True,
        choices=tuple(level.value for level in ProtectionLevel),
    )
    parser.add_argument(
        "--canvas-operation", choices=("same-size", "contain-no-resize", "resample", "crop"),
        default="same-size",
    )
    parser.add_argument("--backend-mask-supported", action="store_true")
    parser.add_argument("--deterministic-composite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = assess_plan(
            args.source_size, args.target_size, args.protection_level,
            canvas_operation=args.canvas_operation,
            backend_mask_supported=args.backend_mask_supported,
            deterministic_composite=args.deterministic_composite,
        )
        print(json.dumps(asdict(report), ensure_ascii=True))
        return 0 if report.status == "ok" else 2
    except BridgePlanError as exc:
        print(f"validate_bridge_plan: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
