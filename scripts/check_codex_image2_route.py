#!/usr/bin/env python3
"""Check the configured codex-image2 API origin without exposing credentials."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit


DEFAULT_URL = "https://apinebula.com"


class RouteError(ValueError):
    pass


@dataclass(frozen=True)
class RouteReport:
    scheme: str
    hostname: str
    configured: bool
    key_present: bool


def _is_loopback(hostname: str) -> bool:
    normalized = hostname.rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def inspect_route(environment: dict[str, str], allow_default: bool) -> RouteReport:
    configured_url = environment.get("CODEX_API_URL", "").strip()
    if not configured_url and not allow_default:
        raise RouteError(
            "CODEX_API_URL is absent; the apinebula.com default is allowed only when the user explicitly named codex-image2."
        )
    route_url = configured_url or DEFAULT_URL
    if "\\" in route_url or any(character.isspace() or ord(character) < 32 for character in route_url):
        raise RouteError("CODEX_API_URL must not contain whitespace, control characters, or backslashes.")
    parsed = urlsplit(route_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RouteError("CODEX_API_URL must be an absolute HTTP or HTTPS URL.")
    if parsed.username is not None or parsed.password is not None:
        raise RouteError("CODEX_API_URL must not contain embedded credentials.")
    if parsed.query or parsed.fragment:
        raise RouteError("CODEX_API_URL must not contain a query string or fragment.")
    try:
        parsed.port
    except ValueError as exc:
        raise RouteError("CODEX_API_URL contains an invalid port.") from exc
    if parsed.scheme == "http" and not _is_loopback(parsed.hostname):
        raise RouteError("Remote CODEX_API_URL routes must use HTTPS; HTTP is allowed only for loopback.")
    key_present = bool(environment.get("CODEX_API_KEY", "").strip())
    return RouteReport(parsed.scheme, parsed.hostname, bool(configured_url), key_present)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-default", action="store_true",
        help="Allow apinebula.com only because the user explicitly named codex-image2.",
    )
    args = parser.parse_args(argv)
    try:
        report = inspect_route(dict(os.environ), args.allow_default)
        print(json.dumps({"status": "ok", **asdict(report)}))
        return 0
    except RouteError as exc:
        print(f"check_codex_image2_route: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
