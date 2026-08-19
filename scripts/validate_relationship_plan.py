#!/usr/bin/env python3
"""Reject ordinary staging before a bridge relationship reaches generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ALLOWED_TYPES = {
    "contour_translation",
    "material_translation",
    "light_reflection_passage",
    "media_relay",
    "shared_distilled_scene",
}
REJECTED_TYPES = {"background_replacement", "co_location", "decorative_connector"}


class RelationshipPlanError(ValueError):
    pass


def _text(plan: dict[str, object], key: str) -> str:
    value = plan.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RelationshipPlanError(f"{key} must be a non-empty string.")
    return value.strip()


def validate_relationship_plan(plan: object) -> dict[str, object]:
    if not isinstance(plan, dict):
        raise RelationshipPlanError("Relationship plan must be an object.")
    relationship_type = _text(plan, "relationship_type")
    if relationship_type in REJECTED_TYPES:
        raise RelationshipPlanError("Ordinary staging and decorative connectors are not bridge relationships.")
    if relationship_type not in ALLOWED_TYPES:
        raise RelationshipPlanError("Unknown relationship type.")
    source_a = _text(plan, "source_a_evidence")
    source_b = _text(plan, "source_b_evidence")
    if source_a.casefold() == source_b.casefold():
        raise RelationshipPlanError("The two endpoints need distinct source-specific evidence.")
    _text(plan, "start_region")
    _text(plan, "transition_zone")
    _text(plan, "transition_carrier")
    _text(plan, "state_change")
    _text(plan, "landing_region")
    if plan.get("breaks_without_source_a") is not True or plan.get("breaks_without_source_b") is not True:
        raise RelationshipPlanError("Removing either source must break the planned relationship.")
    if plan.get("ordinary_staging") is not False:
        raise RelationshipPlanError("The plan must explicitly fail the ordinary-staging description.")
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", nargs="?", default="-", help="JSON file path, or - for standard input.")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.plan == "-" else Path(args.plan).read_text(encoding="utf-8")
        validate_relationship_plan(json.loads(raw))
        print(json.dumps({"status": "ok"}, ensure_ascii=True))
        return 0
    except (RelationshipPlanError, FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"validate_relationship_plan: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
