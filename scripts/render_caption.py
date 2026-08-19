#!/usr/bin/env python3
"""Render a small editorial caption without repainting the source image."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except ImportError as exc:  # Stop clearly instead of falling back to another renderer.
    raise SystemExit("Pillow is required for deterministic caption rendering.") from exc

from image_safety import ImageSafetyError, validate_image_dimensions, validate_input_file


FONT_CHAINS = {
    "organic": ("Noto Serif SC", "Georgia", "Garamond", "DejaVu Serif"),
    "modern": ("Segoe UI Variable", "Noto Sans SC", "DejaVu Sans"),
}
CHINESE_FONT_CHAINS = {
    "organic": ("Noto Serif SC",),
    "modern": ("Noto Sans SC",),
}
FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
ENGLISH_CAPTION_RE = re.compile(r"^[A-Za-z]+(?: [A-Za-z]+){1,2}$")
CHINESE_CAPTION_RE = re.compile(r"^[\u3400-\u4DBF\u4E00-\u9FFF]+$")
MIN_FONT_RATIO = 0.018
DEFAULT_FONT_RATIO = 0.021
MAX_FONT_RATIO = 0.024
SAFE_EDGE_RATIO = 0.04
SOLID_TEXT_THRESHOLD = 224
MIN_CONTRAST_RATIO = 3.0
MAX_BACKGROUND_EDGE_DENSITY = 0.14
MAX_BACKGROUND_LUMINANCE_STDDEV = 42.0


class CaptionError(ValueError):
    pass


@dataclass(frozen=True)
class FontChoice:
    requested_name: str
    family: str
    path: str


@dataclass(frozen=True)
class RenderReport:
    input: str
    output: str
    caption: str
    style: str
    font_family: str
    font_path: str
    font_size: int
    letter_spacing: float
    opacity: float
    contrast_ratio: float
    zone_index: int
    zone: tuple[float, float, float, float]
    text_bbox: tuple[int, int, int, int]
    image_size: tuple[int, int]
    image_mode: str


def _caption_language(caption: str) -> str:
    if CHINESE_CAPTION_RE.fullmatch(caption):
        if 2 <= len(caption) <= 8:
            return "chinese"
        raise CaptionError("Chinese caption must contain two to eight Han characters.")
    if len(caption) > 18:
        raise CaptionError("English caption must contain at most 18 characters including spaces.")
    if not ENGLISH_CAPTION_RE.fullmatch(caption):
        raise CaptionError(
            "Caption must be two or three English words or two to eight Chinese characters, "
            "without punctuation, numbers, or mixed scripts."
        )
    if caption != caption.title():
        raise CaptionError("English caption must use Title Case.")
    return "english"


def validate_caption(caption: str) -> None:
    _caption_language(caption)


def parse_zone(value: str) -> tuple[float, float, float, float]:
    try:
        zone = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Zone must be x,y,w,h using normalized numbers.") from exc
    if len(zone) != 4:
        raise argparse.ArgumentTypeError("Zone must contain exactly four numbers: x,y,w,h.")
    try:
        _validate_zone(zone)
    except CaptionError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return zone


def _validate_zone(zone: tuple[float, float, float, float]) -> None:
    if len(zone) != 4 or not all(math.isfinite(value) for value in zone):
        raise CaptionError("Zone must contain four finite numbers: x,y,w,h.")
    x, y, width, height = zone
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise CaptionError("Zone must stay within the normalized 0..1 canvas.")


def _load_master(path: Path) -> Image.Image:
    try:
        validate_input_file(path, "Unlettered master")
    except ImageSafetyError as exc:
        raise CaptionError(str(exc)) from exc
    with Image.open(path) as opened:
        if opened.format != "PNG":
            raise CaptionError("The unlettered master must be a lossless PNG.")
        if getattr(opened, "n_frames", 1) != 1:
            raise CaptionError("The unlettered master must be a single-frame PNG.")
        if opened.mode not in ("RGB", "RGBA"):
            raise CaptionError("The PNG must use RGB or RGBA color mode.")
        try:
            validate_image_dimensions(opened.size, "Unlettered master")
        except ImageSafetyError as exc:
            raise CaptionError(str(exc)) from exc
        if opened.mode == "RGB" and "transparency" in opened.info:
            raise CaptionError("RGB PNG transparency is unsupported; use explicit RGBA instead.")
        if opened.getexif().get(274, 1) != 1:
            raise CaptionError("PNG orientation must be normalized into the pixels before captioning.")
        opened.load()
        image = opened.copy()
        image.info.update(opened.info)
        return image


def _font_directories() -> list[Path]:
    directories: list[Path] = []
    if os.name == "nt":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        directories.append(windir / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            directories.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    else:
        directories.extend(
            [
                Path.home() / ".fonts",
                Path.home() / ".local" / "share" / "fonts",
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
            ]
        )
    return [directory for directory in directories if directory.is_dir()]


def _font_files() -> list[Path]:
    files: list[Path] = []
    for directory in _font_directories():
        try:
            files.extend(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS
            )
        except OSError:
            continue
    return sorted(set(files), key=lambda path: str(path).lower())


def _normalized_font_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower()).removesuffix("text")


def _font_chain(style: str, caption: str) -> tuple[str, ...]:
    return CHINESE_FONT_CHAINS[style] if _caption_language(caption) == "chinese" else FONT_CHAINS[style]


def resolve_font(style: str, caption: str | None = None) -> FontChoice:
    chain = FONT_CHAINS[style] if caption is None else _font_chain(style, caption)
    files = _font_files()
    discovered: list[tuple[Path, str, str]] = []
    for path in files:
        try:
            family, font_style = ImageFont.truetype(str(path), 16).getname()
        except (OSError, ValueError):
            continue
        discovered.append((path, family, font_style))

    for requested in chain:
        wanted = _normalized_font_name(requested)
        for path, family, font_style in discovered:
            if _normalized_font_name(family) != wanted:
                continue
            style_name = font_style.lower()
            if any(weight in style_name for weight in ("bold", "italic", "semibold", "black")):
                continue
            return FontChoice(requested, family, str(path))
    raise CaptionError(f"No compatible {style} font is installed: {', '.join(chain)}.")


def load_font(choice: FontChoice, size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(choice.path, size)
    try:
        variation_names = [name.decode("ascii", "ignore") for name in font.get_variation_names()]
        regular = next((name for name in variation_names if name == "Regular"), None)
        if regular:
            font.set_variation_by_name(regular)
    except (AttributeError, OSError):
        pass
    return font


def _text_metrics(
    caption: str, font: ImageFont.FreeTypeFont, letter_spacing: float
) -> tuple[int, int, int, list[float]]:
    advances = [float(font.getlength(character)) for character in caption]
    width = int(math.ceil(sum(advances) + letter_spacing * max(0, len(caption) - 1)))
    left, top, right, bottom = font.getbbox(caption)
    height = int(math.ceil(bottom - top))
    return width, height, top, advances


def _usable_zone(
    zone: tuple[float, float, float, float], image_size: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    width, height = image_size
    safe_x = int(math.ceil(width * SAFE_EDGE_RATIO))
    safe_y = int(math.ceil(height * SAFE_EDGE_RATIO))
    x, y, zone_width, zone_height = zone
    left = max(int(math.ceil(x * width)), safe_x)
    top = max(int(math.ceil(y * height)), safe_y)
    right = min(int(math.floor((x + zone_width) * width)), width - safe_x)
    bottom = min(int(math.floor((y + zone_height) * height)), height - safe_y)
    return (left, top, right, bottom) if right > left and bottom > top else None


def _place_text(
    text_size: tuple[int, int], zone_box: tuple[int, int, int, int], image_size: tuple[int, int]
) -> tuple[int, int]:
    text_width, text_height = text_size
    left, top, right, bottom = zone_box
    if text_width > right - left or text_height > bottom - top:
        raise CaptionError("Caption does not fit this zone.")

    zone_center_x = (left + right) / 2 / image_size[0]
    if zone_center_x < 0.4:
        x = left
    elif zone_center_x > 0.6:
        x = right - text_width
    else:
        x = left + (right - left - text_width) // 2
    y = top + (bottom - top - text_height) // 2
    return x, y


def _draw_text_mask(
    image_size: tuple[int, int], caption: str, font: ImageFont.FreeTypeFont,
    origin: tuple[int, int], top_offset: int, advances: list[float], letter_spacing: float
) -> Image.Image:
    mask = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(mask)
    x, y = origin
    cursor = float(x)
    for character, advance in zip(caption, advances):
        draw.text((round(cursor), y - top_offset), character, font=font, fill=255)
        cursor += advance + letter_spacing
    return mask


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for value in rgb:
        channel = value / 255.0
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    bright, dark = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def _pixel_data(image: Image.Image) -> list[object]:
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def _text_samples(image: Image.Image, mask: Image.Image) -> list[tuple[tuple[int, int, int], int]]:
    bbox = mask.getbbox()
    if bbox is None:
        raise CaptionError("Font produced an empty text mask.")
    rgb_pixels = _pixel_data(image.convert("RGB").crop(bbox))
    mask_pixels = _pixel_data(mask.crop(bbox))
    all_text_indices = [index for index, coverage in enumerate(mask_pixels) if coverage > 0]
    indices = [index for index in all_text_indices if mask_pixels[index] >= SOLID_TEXT_THRESHOLD]
    if not indices:
        indices = all_text_indices
    if not indices:
        raise CaptionError("Caption has no sampleable text pixels.")
    if image.mode == "RGBA":
        alpha_pixels = _pixel_data(image.getchannel("A").crop(bbox))
        if any(alpha_pixels[index] < 255 for index in all_text_indices):
            raise CaptionError("Caption text must be placed on an opaque part of an RGBA image.")
    return [(rgb_pixels[index], mask_pixels[index]) for index in indices]


def _check_negative_space(image: Image.Image, zone_box: tuple[int, int, int, int]) -> None:
    """Reject busy zones before typography is considered."""
    left, top, right, bottom = zone_box
    crop = image.convert("RGB").crop((left, top, right, bottom))
    sample_width = max(8, min(96, crop.width))
    sample_height = max(8, min(48, crop.height))
    sample = crop.resize((sample_width, sample_height))
    pixels = _pixel_data(sample)
    if not pixels:
        raise CaptionError("Zone has no measurable background area.")
    channel_stddev = ImageStat.Stat(sample).stddev
    edge_count = 0
    comparisons = 0
    for y in range(sample_height):
        for x in range(sample_width):
            value = pixels[y * sample_width + x]
            if x + 1 < sample_width:
                neighbor = pixels[y * sample_width + x + 1]
                edge_count += max(abs(a - b) for a, b in zip(value, neighbor)) >= 24
                comparisons += 1
            if y + 1 < sample_height:
                neighbor = pixels[(y + 1) * sample_width + x]
                edge_count += max(abs(a - b) for a, b in zip(value, neighbor)) >= 24
                comparisons += 1
    edge_density = edge_count / max(1, comparisons)
    if edge_density > MAX_BACKGROUND_EDGE_DENSITY:
        raise CaptionError("Zone is too visually busy for a caption.")
    if max(channel_stddev) > MAX_BACKGROUND_LUMINANCE_STDDEV:
        raise CaptionError("Zone has insufficient continuous negative space.")


def _bbox_within(
    inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]
) -> bool:
    return (
        inner[0] >= outer[0]
        and inner[1] >= outer[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _choose_color_and_opacity(
    samples: list[tuple[tuple[int, int, int], int]]
) -> tuple[tuple[int, int, int], float, float]:
    backgrounds = [background for background, _ in samples]
    local_value = round(median(round(sum(background) / 3) for background in backgrounds))
    dark = (min(local_value, 56),) * 3
    light = (max(local_value, 224),) * 3
    colors = sorted(
        (dark, light),
        key=lambda color: min(_contrast(color, background) for background in backgrounds),
        reverse=True,
    )
    for opacity_percent in range(78, 89):
        opacity = opacity_percent / 100
        for color in colors:
            ratios = []
            for background, coverage in samples:
                effective_opacity = opacity * coverage / 255
                composited = tuple(
                    round(foreground * effective_opacity + base * (1 - effective_opacity))
                    for foreground, base in zip(color, background)
                )
                ratios.append(_contrast(composited, background))
            minimum_ratio = min(ratios)
            if minimum_ratio >= MIN_CONTRAST_RATIO:
                return color, opacity, minimum_ratio
    raise CaptionError("Caption cannot reach 3:1 contrast across all solid text pixels in this zone.")


def _compose(image: Image.Image, mask: Image.Image, color: tuple[int, int, int], opacity: float) -> Image.Image:
    alpha = mask.point(lambda value: round(value * opacity))
    base = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, color + (0,))
    overlay.putalpha(alpha)
    composed = Image.alpha_composite(base, overlay)
    return composed if image.mode == "RGBA" else composed.convert("RGB")


def assert_unchanged_outside_mask(before: Image.Image, after: Image.Image, mask: Image.Image) -> None:
    if before.size != after.size or before.mode != after.mode:
        raise CaptionError("Caption rendering changed the canvas size or color mode.")
    before_bytes = before.tobytes()
    after_bytes = after.tobytes()
    mask_bytes = mask.tobytes()
    channels = len(before.getbands())
    for pixel_index, mask_value in enumerate(mask_bytes):
        if mask_value:
            continue
        start = pixel_index * channels
        if before_bytes[start : start + channels] != after_bytes[start : start + channels]:
            raise CaptionError("A pixel outside the actual text mask changed.")


def _png_metadata(image: Image.Image) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for key in ("dpi", "icc_profile"):
        value = image.info.get(key)
        if value is not None:
            metadata[key] = value
    return metadata


def _publish_no_overwrite(temporary_path: Path, output_path: Path) -> None:
    try:
        os.link(temporary_path, output_path)
    except FileExistsError as exc:
        raise CaptionError("Output path was created during rendering; refusing to overwrite it.") from exc
    temporary_path.unlink()


def render_caption(
    input_path: Path, output_path: Path, caption: str, style: str,
    zones: list[tuple[float, float, float, float]]
) -> RenderReport:
    validate_caption(caption)
    if input_path.resolve() == output_path.resolve():
        raise CaptionError("Input and output paths must be different; the unlettered master cannot be overwritten.")
    if output_path.exists():
        raise CaptionError("Output path already exists; choose a new path instead of overwriting it.")
    if not 1 <= len(zones) <= 3:
        raise CaptionError("Provide one to three candidate zones.")
    for zone in zones:
        _validate_zone(zone)

    image = _load_master(input_path)
    choice = resolve_font(style, caption)

    short_edge = min(image.size)
    default_size = max(1, round(short_edge * DEFAULT_FONT_RATIO))
    minimum_size = max(1, math.ceil(short_edge * MIN_FONT_RATIO))
    maximum_size = max(1, math.floor(short_edge * MAX_FONT_RATIO))
    start_size = min(default_size, maximum_size)
    failures: list[str] = []

    for zone_index, zone in enumerate(zones, start=1):
        zone_box = _usable_zone(zone, image.size)
        if zone_box is None:
            failures.append(f"zone {zone_index}: no area remains after the 4% safe margin")
            continue
        try:
            _check_negative_space(image, zone_box)
        except CaptionError as exc:
            failures.append(f"zone {zone_index}: {exc}")
            continue
        for font_size in range(start_size, minimum_size - 1, -1):
            font = load_font(choice, font_size)
            letter_spacing = font_size * 0.02
            text_width, text_height, top_offset, advances = _text_metrics(caption, font, letter_spacing)
            try:
                origin = _place_text((text_width, text_height), zone_box, image.size)
            except CaptionError:
                continue
            mask = _draw_text_mask(
                image.size, caption, font, origin, top_offset, advances, letter_spacing
            )
            mask_bbox = mask.getbbox()
            if mask_bbox is None:
                failures.append(f"zone {zone_index}: font produced an empty text mask")
                break
            if not _bbox_within(mask_bbox, zone_box):
                failures.append(f"zone {zone_index}: rendered text extends outside the candidate zone")
                continue
            try:
                samples = _text_samples(image, mask)
                color, opacity, contrast_ratio = _choose_color_and_opacity(samples)
            except CaptionError as exc:
                failures.append(f"zone {zone_index}: {exc}")
                break
            result = _compose(image, mask, color, opacity)
            assert_unchanged_outside_mask(image, result, mask)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            metadata = _png_metadata(image)
            temporary_name: str | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    prefix=f".{output_path.stem}-", suffix=".png", dir=output_path.parent, delete=False
                ) as temporary:
                    temporary_name = temporary.name
                result.save(temporary_name, format="PNG", **metadata)
                with Image.open(temporary_name) as verified:
                    if verified.size != image.size or verified.mode != image.mode:
                        raise CaptionError("Saved PNG changed the canvas size or color mode.")
                    if verified.info.get("icc_profile") != metadata.get("icc_profile"):
                        raise CaptionError("Saved PNG changed the ICC profile.")
                    if "exif" in verified.info:
                        raise CaptionError("Saved PNG retained EXIF metadata.")
                    assert_unchanged_outside_mask(image, verified.copy(), mask)
                _publish_no_overwrite(Path(temporary_name), output_path)
            finally:
                if temporary_name and os.path.exists(temporary_name):
                    os.unlink(temporary_name)

            return RenderReport(
                str(input_path), str(output_path), caption, style, choice.family, choice.path,
                font_size, round(letter_spacing, 4), opacity, round(contrast_ratio, 3), zone_index,
                zone, mask_bbox, image.size, image.mode
            )
        failures.append(f"zone {zone_index}: caption does not fit at the minimum font size")

    raise CaptionError("No safe negative-space zone passed: " + "; ".join(dict.fromkeys(failures)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="Validate caption and report the selected font.")
    parser.add_argument("--input", type=Path, help="Lossless unlettered PNG master.")
    parser.add_argument("--output", type=Path, help="Different path for the captioned PNG.")
    parser.add_argument("--caption", required=True)
    parser.add_argument("--style", required=True, choices=tuple(FONT_CHAINS))
    parser.add_argument("--zone", action="append", type=parse_zone, default=[], help="Normalized x,y,w,h; repeat up to three times.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_caption(args.caption)
        choice = resolve_font(args.style, args.caption)
        if args.probe:
            print(json.dumps({"status": "ok", "style": args.style, **asdict(choice)}, ensure_ascii=False))
            return 0
        if args.input is None or args.output is None:
            raise CaptionError("--input and --output are required unless --probe is used.")
        report = render_caption(args.input, args.output, args.caption, args.style, args.zone)
        print(json.dumps({"status": "ok", **asdict(report)}, ensure_ascii=False))
        return 0
    except (CaptionError, FileNotFoundError, OSError) as exc:
        if str(exc).startswith("No safe negative-space zone passed:"):
            print(json.dumps({"status": "skipped", "reason": str(exc)}, ensure_ascii=False))
            return 0
        print(f"render_caption: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
