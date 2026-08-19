#!/usr/bin/env python3
"""Create and safely remove one temporary Bridge Two Images run directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path


RUN_PREFIX = "bridge-two-images-"
MARKER_NAME = ".bridge-two-images-run.json"
MARKER_KIND = "bridge-two-images-managed-run"
MARKER_VERSION = 1
CLEANUP_PREFIX = f".{RUN_PREFIX}cleanup-"
CLEANUP_CLAIM_NAME = ".bridge-two-images-cleanup-claim"


class WorkspaceError(ValueError):
    pass


def _temporary_root() -> Path:
    return Path(tempfile.gettempdir()).resolve()


def create_run_directory() -> Path:
    run_dir = Path(tempfile.mkdtemp(prefix=RUN_PREFIX)).resolve()
    marker = run_dir / MARKER_NAME
    payload = {
        "kind": MARKER_KIND,
        "version": MARKER_VERSION,
        "run_dir": str(run_dir),
    }
    try:
        marker.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8", errors="strict")
    except OSError:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise
    return run_dir


def _validate_marker(directory: Path, expected_run_dir: Path) -> None:
    marker = directory / MARKER_NAME
    if not marker.is_file() or marker.is_symlink():
        raise WorkspaceError("Managed run marker is missing or invalid.")
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkspaceError("Managed run marker cannot be read.") from exc
    if payload != {
        "kind": MARKER_KIND,
        "version": MARKER_VERSION,
        "run_dir": str(expected_run_dir),
    }:
        raise WorkspaceError("Managed run marker does not match this directory.")


def _validated_run_directory(run_dir: Path) -> Path:
    if not run_dir.is_absolute():
        raise WorkspaceError("Run directory must be an absolute path.")
    if run_dir.is_symlink():
        raise WorkspaceError("Run directory cannot be a symbolic link.")
    try:
        resolved = run_dir.resolve(strict=True)
    except FileNotFoundError as exc:
        raise WorkspaceError("Run directory does not exist.") from exc
    if resolved.parent != _temporary_root() or not resolved.name.startswith(RUN_PREFIX):
        raise WorkspaceError("Refusing to remove a directory outside the managed temporary root.")

    _validate_marker(resolved, resolved)
    return resolved


def _restore_failed_claim(claimed: Path, original: Path) -> None:
    if os.path.lexists(claimed) and not os.path.lexists(original):
        try:
            os.rename(claimed, original)
        except OSError:
            pass


def cleanup_run_directory(run_dir: Path) -> bool:
    if not run_dir.exists():
        return False
    validated = _validated_run_directory(run_dir)
    claim_file = validated / CLEANUP_CLAIM_NAME
    try:
        descriptor = os.open(claim_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except (FileExistsError, FileNotFoundError):
        return False
    try:
        os.close(descriptor)
    except OSError:
        try:
            claim_file.unlink()
        except OSError:
            pass
        raise

    claimed = _temporary_root() / f"{CLEANUP_PREFIX}{uuid.uuid4().hex}"
    try:
        os.rename(validated, claimed)
    except FileNotFoundError:
        return False
    except OSError:
        try:
            claim_file.unlink()
        except OSError:
            pass
        raise

    try:
        if claimed.is_symlink():
            raise WorkspaceError("Claimed run directory cannot be a symbolic link.")
        resolved_claim = claimed.resolve(strict=True)
        if resolved_claim.parent != _temporary_root() or not resolved_claim.name.startswith(CLEANUP_PREFIX):
            raise WorkspaceError("Run directory changed during cleanup; refusing recursive deletion.")
        _validate_marker(resolved_claim, validated)
    except (WorkspaceError, OSError):
        try:
            (claimed / CLEANUP_CLAIM_NAME).unlink()
        except OSError:
            pass
        _restore_failed_claim(claimed, validated)
        raise

    shutil.rmtree(resolved_claim)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create", help="Create one managed temporary run directory.")
    cleanup = commands.add_parser("cleanup", help="Remove one validated managed run directory.")
    cleanup.add_argument("--run-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            run_dir = create_run_directory()
            print(json.dumps({"status": "ok", "run_dir": str(run_dir)}, ensure_ascii=True))
        else:
            removed = cleanup_run_directory(args.run_dir)
            print(json.dumps({"status": "ok", "removed": removed}, ensure_ascii=False))
        return 0
    except (WorkspaceError, OSError) as exc:
        print(f"manage_run_workspace: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
