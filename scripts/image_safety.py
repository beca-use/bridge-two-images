"""Shared limits for untrusted raster inputs used by deterministic helpers."""

from __future__ import annotations

from pathlib import Path


MAX_IMAGE_DIMENSION = 8192
MAX_IMAGE_PIXELS = 20_000_000
MAX_INPUT_BYTES = 128 * 1024 * 1024


class ImageSafetyError(ValueError):
    pass


def validate_input_file(path: Path, label: str) -> None:
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise ImageSafetyError(f"{label} exceeds the 128 MiB input limit.")


def validate_image_dimensions(size: tuple[int, int], label: str) -> None:
    width, height = size
    if width <= 0 or height <= 0:
        raise ImageSafetyError(f"{label} must have positive dimensions.")
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ImageSafetyError(f"{label} exceeds the 8192-pixel side limit.")
    if width * height > MAX_IMAGE_PIXELS:
        raise ImageSafetyError(f"{label} exceeds the 20-megapixel limit.")
