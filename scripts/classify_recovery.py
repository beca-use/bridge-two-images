#!/usr/bin/env python3
"""Choose the permitted recovery action for diagnosed bridge failures."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass


LOCAL_FAILURES = {"single_local_artifact", "single_overlay", "caption_space_optional"}
FULL_RETRY_FAILURES = {
    "identity_drift",
    "weak_relationship",
    "ordinary_staging",
    "missing_anchor",
    "wrong_identity_mark",
    "multiple_defects",
    "composition_defect",
}
BLOCKED_FAILURES = {
    "route_incompatible",
    "exact_pixel_incompatible",
    "backend_incompatible",
}


class RecoveryError(ValueError):
    pass


@dataclass(frozen=True)
class RecoveryDecision:
    action: str
    spends_artistic_retry: bool
    reason: str


def classify_recovery(failures: list[str], retry_available: bool = True) -> RecoveryDecision:
    normalized = [failure.strip().lower() for failure in failures if failure.strip()]
    if not normalized:
        raise RecoveryError("At least one diagnosed failure is required.")
    unknown = set(normalized) - LOCAL_FAILURES - FULL_RETRY_FAILURES - BLOCKED_FAILURES
    if unknown:
        raise RecoveryError(f"Unknown failure category: {sorted(unknown)[0]}")
    if any(failure in BLOCKED_FAILURES for failure in normalized):
        return RecoveryDecision(
            "stop", False, "The selected route is incompatible and must stop before another candidate."
        )
    if len(normalized) > 1 or any(failure in FULL_RETRY_FAILURES for failure in normalized):
        if not retry_available:
            return RecoveryDecision("stop", False, "A full retry is required but none remains.")
        return RecoveryDecision(
            "full_regeneration", True,
            "The failure affects identity, anchors, relationship, or overall composition.",
        )
    failure = normalized[0]
    if failure == "caption_space_optional":
        return RecoveryDecision("deliver_unlettered", False, "Optional caption failure does not alter the artwork.")
    if not retry_available:
        return RecoveryDecision("stop", False, "A local repair would spend the unavailable artistic retry.")
    return RecoveryDecision("local_edit", True, "One bounded local defect may use one local edit.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failure", action="append", required=True)
    parser.add_argument("--no-retry", action="store_true")
    args = parser.parse_args(argv)
    try:
        decision = classify_recovery(args.failure, not args.no_retry)
        print(json.dumps(asdict(decision), ensure_ascii=True))
        return 0
    except RecoveryError as exc:
        print(f"classify_recovery: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
