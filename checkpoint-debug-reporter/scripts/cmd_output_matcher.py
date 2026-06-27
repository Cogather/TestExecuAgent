#!/usr/bin/env python3
"""Match command stdout against expected output patterns for checkpoint verification."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


class OutputMatcher:
    """Match strategies for comparing command output against expected text."""

    @staticmethod
    def contains(stdout: str, expected: str) -> tuple[bool, str]:
        """Check if expected text is a substring of stdout."""
        if expected in stdout:
            return True, "contains: match"
        return False, f"contains: expected text not found in stdout ({len(stdout)} chars)"

    @staticmethod
    def regex(stdout: str, pattern: str) -> tuple[bool, str]:
        """Check if stdout matches a regex pattern."""
        try:
            if re.search(pattern, stdout, re.MULTILINE | re.DOTALL):
                return True, "regex: match"
            return False, "regex: no match"
        except re.error as exc:
            return False, f"regex: invalid pattern: {exc}"

    @staticmethod
    def json_path(stdout: str, jsonpath_expr: str) -> tuple[bool, str]:
        """Extract and compare a JSONPath expression against stdout (assumes stdout is JSON)."""
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            return False, f"json_path: stdout is not valid JSON: {exc}"

        # Simple dot-notation path traversal: "status.code" or "data[0].name"
        parts = re.split(r"\.|\[|\]", jsonpath_expr)
        parts = [p for p in parts if p]
        current = data
        for part in parts:
            if isinstance(current, list) and part.isdigit():
                idx = int(part)
                if idx < len(current):
                    current = current[idx]
                else:
                    return False, f"json_path: index {part} out of range"
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False, f"json_path: key '{part}' not found"
        return True, f"json_path: value = {json.dumps(current, ensure_ascii=False)[:200]}"

    @staticmethod
    def equals(stdout: str, expected: str) -> tuple[bool, str]:
        """Exact string equality (after stripping both sides)."""
        if stdout.strip() == expected.strip():
            return True, "equals: exact match"
        return False, "equals: strings differ"


MATCHERS = {
    "contains": OutputMatcher.contains,
    "regex": OutputMatcher.regex,
    "json_path": OutputMatcher.json_path,
    "equals": OutputMatcher.equals,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Match command stdout against expected output for checkpoint verification."
    )
    parser.add_argument("--stdout-file", required=True, help="Path to stdout.log.")
    parser.add_argument("--expected", required=True, help="Expected output text or pattern.")
    parser.add_argument(
        "--mode", choices=list(MATCHERS.keys()), default="contains",
        help="Matching strategy."
    )
    parser.add_argument("--output", "-o", help="Write result JSON to file.")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stdout_path = Path(args.stdout_file)

    if not stdout_path.exists():
        result = {"matched": False, "mode": args.mode, "reason": "stdout file not found"}
        print(json.dumps(result, ensure_ascii=True))
        return 1

    stdout_text = stdout_path.read_text(encoding="utf-8")
    matcher = MATCHERS[args.mode]
    matched, detail = matcher(stdout_text, args.expected)

    result = {
        "matched": matched,
        "mode": args.mode,
        "reason": detail,
        "stdout_size": len(stdout_text),
        "stdout_preview": stdout_text[:500],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        status = "PASS" if matched else "FAIL"
        print(f"[{status}] {detail}")

    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")

    return 0 if matched else 1


if __name__ == "__main__":
    sys.exit(main())
