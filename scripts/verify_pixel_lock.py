#!/usr/bin/env python3
"""Verify that protected PNG pixels were not changed by an image edit."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from image_safety import ImageSafetyError, validate_image_dimensions, validate_input_file


DISPLAY_METADATA_KEYS = ("icc_profile", "gamma", "chromaticity", "srgb", "transparency")
ORIENTATION_TAG = 274


class PixelLockError(ValueError):
    pass


@dataclass(frozen=True)
class PixelLockReport:
    mode: str
    width: int
    height: int
    checked_pixels: int
    changed_locked_pixels: int


def _pixel_data(image: Image.Image):
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def _load_raster(path: Path, label: str) -> tuple[Image.Image, tuple[object, ...]]:
    try:
        validate_input_file(path, label)
    except ImageSafetyError as exc:
        raise PixelLockError(str(exc)) from exc
    with Image.open(path) as opened:
        if opened.format != "PNG":
            raise PixelLockError(f"{label} must be a PNG image.")
        if getattr(opened, "n_frames", 1) != 1:
            raise PixelLockError(f"{label} must contain exactly one frame.")
        if opened.mode not in ("RGB", "RGBA"):
            raise PixelLockError(f"{label} must use RGB or RGBA color mode.")
        try:
            validate_image_dimensions(opened.size, label)
        except ImageSafetyError as exc:
            raise PixelLockError(str(exc)) from exc
        try:
            orientation = int(opened.getexif().get(ORIENTATION_TAG, 1))
        except (TypeError, ValueError, SyntaxError) as exc:
            raise PixelLockError(f"{label} has invalid EXIF orientation metadata.") from exc
        if orientation != 1:
            raise PixelLockError(f"{label} must have orientation normalized into its raster pixels.")
        opened.load()
        image = opened.copy()
        display_metadata = tuple(opened.info.get(key) for key in DISPLAY_METADATA_KEYS)
    return image, display_metadata


def _load_mask(path: Path) -> Image.Image:
    try:
        validate_input_file(path, "Verification mask")
    except ImageSafetyError as exc:
        raise PixelLockError(str(exc)) from exc
    with Image.open(path) as opened:
        if opened.format != "PNG":
            raise PixelLockError("Verification mask must be a PNG image.")
        if getattr(opened, "n_frames", 1) != 1:
            raise PixelLockError("Verification mask must contain exactly one frame.")
        if opened.mode != "L":
            raise PixelLockError("Verification mask must use single-channel L mode.")
        try:
            validate_image_dimensions(opened.size, "Verification mask")
        except ImageSafetyError as exc:
            raise PixelLockError(str(exc)) from exc
        opened.load()
        mask = opened.copy()
    values = set(_pixel_data(mask))
    if not values.issubset({0, 255}):
        raise PixelLockError("Verification mask must contain only binary values 0 and 255.")
    return mask


def _load(before_path: Path, after_path: Path, mask_path: Path) -> tuple[Image.Image, Image.Image, Image.Image]:
    before, before_metadata = _load_raster(before_path, "Before image")
    after, after_metadata = _load_raster(after_path, "After image")
    mask = _load_mask(mask_path)
    mask_size = mask.size
    if before.size != after.size or before.size != mask_size:
        raise PixelLockError("Before, after, and mask dimensions must match exactly.")
    if before.mode != after.mode:
        raise PixelLockError("Before and after color mode must match exactly.")
    if before_metadata != after_metadata:
        raise PixelLockError("Before and after display metadata must match exactly.")
    return before, after, mask


def _verify(before_path: Path, after_path: Path, mask_path: Path, lock_nonzero: bool) -> PixelLockReport:
    before, after, mask = _load(before_path, after_path, mask_path)
    mask_values = set(_pixel_data(mask))
    if lock_nonzero:
        if 255 not in mask_values:
            raise PixelLockError("Locked mask must select at least one protected pixel.")
    elif mask_values != {0, 255}:
        raise PixelLockError("Allowed-change mask must contain both allowed and unchanged regions.")

    changed = 0
    checked = 0
    for before_pixel, after_pixel, mask_value in zip(
        _pixel_data(before), _pixel_data(after), _pixel_data(mask)
    ):
        selected = mask_value == 255 if lock_nonzero else mask_value == 0
        if not selected:
            continue
        checked += 1
        changed += before_pixel != after_pixel
    if changed:
        label = "protected pixel" if lock_nonzero else "pixel outside the allowed-change mask"
        plural = "" if changed == 1 else "s"
        raise PixelLockError(f"{changed} {label}{plural} changed.")
    return PixelLockReport(before.mode, before.width, before.height, checked, changed)


def verify_locked_mask(before: Path, after: Path, mask: Path) -> PixelLockReport:
    return _verify(before, after, mask, True)


def verify_allowed_change_mask(before: Path, after: Path, mask: Path) -> PixelLockReport:
    return _verify(before, after, mask, False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--locked-mask", type=Path)
    group.add_argument("--allowed-change-mask", type=Path)
    args = parser.parse_args(argv)
    try:
        report = (
            verify_locked_mask(args.before, args.after, args.locked_mask)
            if args.locked_mask else
            verify_allowed_change_mask(args.before, args.after, args.allowed_change_mask)
        )
        print(json.dumps({"status": "ok", **asdict(report)}))
        return 0
    except (PixelLockError, FileNotFoundError, OSError) as exc:
        print(f"verify_pixel_lock: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
