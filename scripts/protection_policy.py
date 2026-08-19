"""Deterministic protection levels for required output regions."""

from __future__ import annotations

from enum import Enum


class ProtectionLevel(str, Enum):
    EXACT_PIXEL = "exact_pixel"
    IDENTITY_FAITHFUL = "identity_faithful"
    STRUCTURAL = "structural"


IDENTITY_KINDS = {"face", "eyes", "expression"}
STRUCTURAL_KINDS = {"hand", "foot", "wing", "pose", "silhouette", "limb_junction"}
EXACT_KINDS = {"logo", "brand_text", "identity_critical_text"}
KNOWN_KINDS = IDENTITY_KINDS | STRUCTURAL_KINDS | EXACT_KINDS


def classify_protection(kind: str, exact_requested: bool = False) -> ProtectionLevel:
    normalized = kind.strip().lower()
    if normalized not in KNOWN_KINDS:
        raise ValueError(f"Unknown protection kind: {kind}")
    if exact_requested or normalized in EXACT_KINDS:
        return ProtectionLevel.EXACT_PIXEL
    if normalized in IDENTITY_KINDS:
        return ProtectionLevel.IDENTITY_FAITHFUL
    return ProtectionLevel.STRUCTURAL


def requires_pixel_verification(level: ProtectionLevel) -> bool:
    return level is ProtectionLevel.EXACT_PIXEL
