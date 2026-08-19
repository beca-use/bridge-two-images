#!/usr/bin/env python3
"""Validate the explicit source-anchor and omission manifest before generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class AnchorManifestError(ValueError):
    pass


def _nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AnchorManifestError(f"{label} must be a non-empty string.")
    return value.strip()


def _validate_source(source: object, index: int) -> None:
    if not isinstance(source, dict):
        raise AnchorManifestError(f"Source {index} must be an object.")
    _nonempty_text(source.get("source"), f"Source {index} id")
    subjects = source.get("primary_subjects")
    if not isinstance(subjects, list) or not subjects or not all(isinstance(item, str) and item.strip() for item in subjects):
        raise AnchorManifestError(f"Source {index} must list its primary subjects.")
    _nonempty_text(source.get("selected_anchor"), f"Source {index} selected anchor")
    evidence = source.get("retained_evidence")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item.strip() for item in evidence):
        raise AnchorManifestError(f"Source {index} must list retained source evidence.")
    omitted = source.get("omitted_content", [])
    if not isinstance(omitted, list):
        raise AnchorManifestError(f"Source {index} omitted_content must be a list.")
    for item in omitted:
        if not isinstance(item, dict):
            raise AnchorManifestError(f"Source {index} omitted content needs a label and reason.")
        _nonempty_text(item.get("label"), f"Source {index} omitted label")
        _nonempty_text(item.get("reason"), f"Source {index} omission reason")
    marks = source.get("identity_marks", [])
    if not isinstance(marks, list):
        raise AnchorManifestError(f"Source {index} identity_marks must be a list.")
    for mark in marks:
        if not isinstance(mark, dict):
            raise AnchorManifestError(f"Source {index} identity mark needs a label and action.")
        _nonempty_text(mark.get("label"), f"Source {index} identity mark label")
        action = _nonempty_text(mark.get("action"), f"Source {index} identity mark action")
        if action not in {"preserve", "omit"}:
            raise AnchorManifestError(f"Source {index} identity mark action must be preserve or omit.")
        if action == "omit":
            _nonempty_text(mark.get("reason"), f"Source {index} omitted identity mark reason")


def validate_anchor_manifest(manifest: object) -> list[dict[str, object]]:
    if not isinstance(manifest, list) or len(manifest) != 2:
        raise AnchorManifestError("Anchor manifest must contain exactly two sources.")
    for index, source in enumerate(manifest, start=1):
        _validate_source(source, index)
    source_ids = [source["source"].strip().lower() for source in manifest]
    if len(set(source_ids)) != 2:
        raise AnchorManifestError("The two manifest sources must be distinct.")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default="-", help="JSON file path, or - for standard input.")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.manifest == "-" else Path(args.manifest).read_text(encoding="utf-8")
        manifest = json.loads(raw)
        validate_anchor_manifest(manifest)
        print(json.dumps({"status": "ok", "sources": 2}, ensure_ascii=True))
        return 0
    except (AnchorManifestError, FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"validate_anchor_manifest: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
