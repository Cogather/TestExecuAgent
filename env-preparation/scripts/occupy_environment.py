#!/usr/bin/env python3
"""Placeholder for environment lock logic."""

import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Occupy and lock the target environment before test execution."
    )
    parser.add_argument("--platform-env-id", required=True, help="Environment id.")
    parser.add_argument("--operator", required=True, help="Operator identity.")
    parser.add_argument(
        "--lock-reason",
        default="test agent preparation",
        help="Lock reason shown in records.",
    )
    parser.add_argument(
        "--expect-unlock-time",
        default="",
        help="Expected unlock timestamp in RFC3339 format.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = {
        "status": "not_implemented",
        "step": "occupy_environment",
        "platform_env_id": args.platform_env_id,
        "operator": args.operator,
        "lock_reason": args.lock_reason,
        "expect_unlock_time": args.expect_unlock_time,
        "message": "TODO: implement environment locking logic.",
    }
    print(json.dumps(result, ensure_ascii=True))
    return 2


if __name__ == "__main__":
    sys.exit(main())
