#!/usr/bin/env python3
"""Detect case type and route to the correct pipeline path."""

from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Optional


class CaseType(str, Enum):
    WEB = "web"
    API = "api"
    MML = "mml"
    HYBRID = "hybrid"


def detect_case_type(
    steps: list[dict],
    explicit_type: Optional[str] = None,
) -> CaseType:
    """Detect the case type from step definitions.

    Priority:
    1. Explicit type override
    2. If any step has command_type='ssh', it's at least MML
    3. If mixed browser + command steps, it's hybrid
    4. Default to web
    """
    if explicit_type:
        try:
            return CaseType(explicit_type)
        except ValueError:
            print(f"Warning: unknown case_type '{explicit_type}', auto-detecting", file=sys.stderr)

    command_types = set()
    for step in steps:
        ct = step.get("command_type", step.get("type", "playwright"))
        command_types.add(ct)

    has_playwright = "playwright" in command_types or len(command_types) == 0
    has_ssh = "ssh" in command_types
    has_local_cmd = "local" in command_types

    if has_playwright and (has_ssh or has_local_cmd):
        return CaseType.HYBRID
    elif has_ssh and not has_playwright:
        return CaseType.MML
    elif has_local_cmd and not has_playwright:
        return CaseType.API

    return CaseType.WEB


def get_pipeline_stages(case_type: CaseType) -> list[str]:
    """Return the ordered pipeline stages for a case type."""
    base = ["bootstrap", "env-preparation"]
    tail = ["checkpoint-debug-reporter", "result-finalizer", "final-report"]

    type_stages = {
        CaseType.WEB: base + ["record-scripts", "fix-scripts"] + tail,
        CaseType.API: base + ["terminal-executor"] + tail,
        CaseType.MML: base + ["terminal-executor"] + tail,
        CaseType.HYBRID: base + ["record-scripts", "fix-scripts", "terminal-executor"] + tail,
    }
    return type_stages.get(case_type, type_stages[CaseType.WEB])


def validate_ssh_config(config: Optional[dict]) -> list[str]:
    """Validate SSH config completeness. Returns list of missing required fields."""
    if config is None:
        return ["ssh_config is missing"]
    required = ["host", "username"]
    missing = [f for f in required if not config.get(f)]
    auth_method = config.get("auth_method", "password")
    if auth_method == "password" and not config.get("password"):
        missing.append("password (for auth_method=password)")
    elif auth_method == "key" and not config.get("key_path"):
        missing.append("key_path (for auth_method=key)")
    return missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect case type and determine pipeline route.")
    parser.add_argument("--steps-file", help="JSON file with step definitions.")
    parser.add_argument("--case-type", choices=[t.value for t in CaseType], help="Explicit case type override.")
    parser.add_argument("--ssh-config", help="JSON file with SSH configuration.")
    parser.add_argument("--output", "-o", help="Write result JSON to file.")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    steps = []
    if args.steps_file:
        steps_path = Path(args.steps_file)
        if steps_path.exists():
            try:
                steps = json.loads(steps_path.read_text(encoding="utf-8"))
                if isinstance(steps, dict):
                    steps = steps.get("steps", [])
            except json.JSONDecodeError as exc:
                print(f"Invalid steps JSON: {exc}", file=sys.stderr)
                return 1
        else:
            print(f"Steps file not found: {args.steps_file}", file=sys.stderr)
            return 1

    case_type = detect_case_type(steps, args.case_type)
    stages = get_pipeline_stages(case_type)

    ssh_issues = []
    if case_type in (CaseType.MML, CaseType.HYBRID):
        ssh_config = None
        if args.ssh_config:
            ssh_path = Path(args.ssh_config)
            if ssh_path.exists():
                ssh_config = json.loads(ssh_path.read_text(encoding="utf-8"))
        ssh_issues = validate_ssh_config(ssh_config)

    result = {
        "case_type": case_type.value,
        "pipeline_stages": stages,
        "step_count": len(steps),
        "step_types": list({s.get("command_type", s.get("type", "playwright")) for s in steps}),
        "ssh_required": case_type in (CaseType.MML, CaseType.HYBRID),
        "ssh_config_valid": len(ssh_issues) == 0 if ssh_issues else None,
        "ssh_issues": ssh_issues,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"Case type: {result['case_type']}")
        print(f"Pipeline: {' → '.join(stages)}")
        print(f"Steps: {result['step_count']} ({', '.join(result['step_types'])})")
        if ssh_issues:
            print(f"SSH issues: {', '.join(ssh_issues)}")

    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
