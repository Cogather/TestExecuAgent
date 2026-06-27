#!/usr/bin/env python3
"""Command safety checker — validates commands against whitelist and blacklist configs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

import yaml


def load_yaml(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        print(f"[safety] YAML parse error in {path}: {exc}", file=sys.stderr)
        return {}


def extract_basename(command: str) -> str:
    """Extract the first word (basename) from a command string, stripping paths."""
    stripped = command.strip()
    if not stripped:
        return ""
    # Handle shell redirections and pipes — take first token before | or > or <
    first_segment = re.split(r"[|><;]", stripped)[0].strip()
    parts = first_segment.split()
    if not parts:
        return ""
    basename = parts[0]
    return Path(basename).name  # strip path, keep only executable name


def check_whitelist(command: str, allowed_config: dict, command_type: str) -> tuple[bool, str]:
    """Check if command basename is in the allowed list for the given type."""
    basename = extract_basename(command)
    if not basename:
        return False, "empty command"

    allowed = allowed_config.get(command_type, [])
    if basename not in allowed:
        return False, f"'{basename}' not in {command_type} whitelist"

    return True, ""


def check_blacklist(command: str, dangerous_patterns: list[str]) -> tuple[bool, str]:
    """Check if command matches any dangerous pattern."""
    normalized = command.strip()
    for pattern in dangerous_patterns:
        if not pattern.strip():
            continue
        try:
            if re.search(pattern, normalized):
                return False, f"matches dangerous pattern: '{pattern}'"
        except re.error as exc:
            print(f"[safety] invalid regex pattern '{pattern}': {exc}", file=sys.stderr)
    return True, ""


def redact_sensitive(text: str) -> str:
    """Redact sensitive data from output text before logging."""
    patterns = [
        (r'(?:password|passwd|secret|token|api_key|api_secret)\s*[=:]\s*\S+', '[REDACTED]'),
        (r'-----BEGIN.*?PRIVATE KEY-----.*?-----END.*?PRIVATE KEY-----', '[REDACTED_KEY]'),
        (r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED_JWT]'),
    ]
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.DOTALL | re.IGNORECASE)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a command against safety configs.")
    parser.add_argument("--command", required=True, help="Full command string to validate.")
    parser.add_argument(
        "--command-type", required=True, choices=["local", "ssh"], help="Command execution type."
    )
    parser.add_argument(
        "--allowed-config",
        default=str(Path(__file__).resolve().parent.parent / "config" / "allowed-commands.yaml"),
        help="Path to allowed-commands.yaml.",
    )
    parser.add_argument(
        "--dangerous-config",
        default=str(Path(__file__).resolve().parent.parent / "config" / "dangerous-commands.yaml"),
        help="Path to dangerous-commands.yaml.",
    )
    parser.add_argument("--redact", action="store_true", help="Redact input command before printing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command
    command_type = args.command_type

    allowed_config = load_yaml(Path(args.allowed_config))
    dangerous_config = load_yaml(Path(args.dangerous_config))
    dangerous_patterns = dangerous_config.get("patterns", [])

    # Step 1: whitelist check
    ok, reason = check_whitelist(command, allowed_config, command_type)
    if not ok:
        display = redact_sensitive(command) if args.redact else command
        print(f"[BLOCKED] whitelist: {reason}  command: {display}")
        return 1

    # Step 2: blacklist check
    ok, reason = check_blacklist(command, dangerous_patterns)
    if not ok:
        display = redact_sensitive(command) if args.redact else command
        print(f"[BLOCKED] blacklist: {reason}  command: {display}")
        return 2

    display = redact_sensitive(command) if args.redact else command
    print(f"[PASS] command: {display}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
