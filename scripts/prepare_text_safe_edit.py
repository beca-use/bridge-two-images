#!/usr/bin/env python3
"""Prepare a protected-source image and masks for a text-safe local edit."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from image_safety import ImageSafetyError, validate_image_dimensions, validate_input_file


class TextSafeEditError(ValueError):
    pass


@dataclass(frozen=True)
class TextSafeEditReport:
    input: str
    base: str
    protected_mask: str
    allowed_change_mask: str
    backend_mask: str
    image_size: tuple[int, int]
    image_mode: str
    protected_boxes: int


def parse_box(value: str) -> tuple[float, float, float, float]:
    try:
        parts = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Protected box must be x,y,w,h using normalized numbers.") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Protected box must contain exactly four numbers.")
    try:
        _validate_box(parts)
    except TextSafeEditError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return parts


def _parse_canvas_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError("Canvas size must use WIDTHxHEIGHT.") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Canvas dimensions must be positive.")
    return width, height


def _validate_box(box: tuple[float, float, float, float]) -> None:
    if len(box) != 4 or not all(math.isfinite(value) for value in box):
        raise TextSafeEditError("Protected box must contain four finite numbers: x,y,w,h.")
    x, y, width, height = box
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise TextSafeEditError("Protected box must stay within the normalized 0..1 canvas.")


def _pixel_box(box: tuple[float, float, float, float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    _validate_box(box)
    x, y, box_width, box_height = box
    left = math.floor(x * width)
    top = math.floor(y * height)
    right = math.ceil((x + box_width) * width) - 1
    bottom = math.ceil((y + box_height) * height) - 1
    if right < left or bottom < top:
        raise TextSafeEditError("Protected box is smaller than one pixel at this image size.")
    return left, top, right, bottom


def _ensure_distinct_new(input_path: Path, outputs: tuple[Path, ...]) -> None:
    paths = (input_path, *outputs)
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise TextSafeEditError("Input and output paths must be distinct.")
    existing = [path for path in outputs if path.exists()]
    if existing:
        raise TextSafeEditError(f"Refusing to overwrite existing output: {existing[0]}")


def _validate_exact_canvas_size(
    input_size: tuple[int, int], requested_size: tuple[int, int] | None
) -> None:
    if requested_size is not None and requested_size != input_size:
        raise TextSafeEditError(
            "Exact-pixel preparation cannot resize or crop the source canvas."
        )


def prepare_edit(
    input_path: Path,
    base_path: Path,
    protected_mask_path: Path,
    allowed_change_mask_path: Path,
    backend_mask_path: Path,
    protected_boxes: list[tuple[float, float, float, float]],
    canvas_size: tuple[int, int] | None = None,
) -> TextSafeEditReport:
    if not protected_boxes:
        raise TextSafeEditError("At least one protected box is required.")
    outputs = (base_path, protected_mask_path, allowed_change_mask_path, backend_mask_path)
    _ensure_distinct_new(input_path, outputs)
    try:
        validate_input_file(input_path, "Base PNG")
    except ImageSafetyError as exc:
        raise TextSafeEditError(str(exc)) from exc
    with Image.open(input_path) as opened:
        if opened.format != "PNG":
            raise TextSafeEditError("Text-safe editing requires a lossless PNG base image.")
        if getattr(opened, "n_frames", 1) != 1:
            raise TextSafeEditError("The base PNG must contain exactly one frame.")
        if opened.mode not in ("RGB", "RGBA"):
            raise TextSafeEditError("The base PNG must use RGB or RGBA color mode.")
        try:
            validate_image_dimensions(opened.size, "Base PNG")
        except ImageSafetyError as exc:
            raise TextSafeEditError(str(exc)) from exc
        _validate_exact_canvas_size(opened.size, canvas_size)
        try:
            orientation = int(opened.getexif().get(274, 1))
        except (TypeError, ValueError, SyntaxError) as exc:
            raise TextSafeEditError("The base PNG has invalid EXIF orientation metadata.") from exc
        if orientation != 1:
            raise TextSafeEditError("Normalize orientation into raster pixels before preparing masks.")
        opened.load()
        image_size = opened.size
        image_mode = opened.mode
    pixel_boxes = [_pixel_box(box, image_size) for box in protected_boxes]
    protected = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(protected)
    for box in pixel_boxes:
        draw.rectangle(box, fill=255)
    if protected.getextrema() == (255, 255):
        raise TextSafeEditError("Protected boxes leave no editable pixels on the canvas.")
    allowed_change = protected.point(lambda value: 255 - value)
    backend_mask = Image.new("RGBA", image_size, (0, 0, 0, 0))
    backend_mask.putalpha(protected)
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(input_path, base_path)
    protected.save(protected_mask_path, format="PNG")
    allowed_change.save(allowed_change_mask_path, format="PNG")
    backend_mask.save(backend_mask_path, format="PNG")
    return TextSafeEditReport(
        str(input_path), str(base_path), str(protected_mask_path),
        str(allowed_change_mask_path), str(backend_mask_path), image_size, image_mode,
        len(pixel_boxes)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="PNG source used as the edit base.")
    parser.add_argument("--base", required=True, type=Path, help="New untouched copy used as edit input.")
    parser.add_argument("--protected-mask", required=True, type=Path)
    parser.add_argument("--allowed-change-mask", required=True, type=Path)
    parser.add_argument(
        "--backend-mask", "--editable-mask", dest="backend_mask", required=True, type=Path,
        help="RGBA transport mask; --editable-mask is retained as a compatibility alias.",
    )
    parser.add_argument("--protected-box", action="append", required=True, type=parse_box)
    parser.add_argument(
        "--canvas-size", type=_parse_canvas_size,
        help="Exact target canvas WIDTHxHEIGHT; it must equal the source for pixel-safe preparation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = prepare_edit(
            args.input, args.base, args.protected_mask, args.allowed_change_mask,
            args.backend_mask, args.protected_box, args.canvas_size
        )
        print(json.dumps({"status": "ok", **asdict(report)}, ensure_ascii=False))
        return 0
    except (TextSafeEditError, FileNotFoundError, OSError) as exc:
        print(f"prepare_text_safe_edit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
