#!/usr/bin/env python3
"""Step dispatcher — route individual steps to Playwright or command execution based on step type."""

from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Optional


class StepType(str, Enum):
    PLAYWRIGHT = "playwright"
    LOCAL = "local"
    SSH = "ssh"


def classify_step(step: dict) -> StepType:
    """Classify a step as playwright, local command, or SSH command."""
    ct = step.get("command_type", step.get("type", "playwright")).lower()
    if ct in ("local", "cmd", "shell", "bash"):
        return StepType.LOCAL
    elif ct in ("ssh", "mml", "cli"):
        return StepType.SSH
    return StepType.PLAYWRIGHT


def group_steps_by_type(steps: list[dict]) -> dict[StepType, list[dict]]:
    """Group steps by type, preserving original order within each group."""
    groups: dict[StepType, list[dict]] = {
        StepType.PLAYWRIGHT: [],
        StepType.LOCAL: [],
        StepType.SSH: [],
    }
    for step in sorted(steps, key=lambda s: int(s.get("step_order", 0))):
        step_type = classify_step(step)
        groups[step_type].append(step)
    return groups


def interleave_steps(steps: list[dict]) -> list[tuple[int, StepType, dict]]:
    """Sort steps by step_order, tagging each with its type for sequential execution."""
    tagged = []
    for step in steps:
        order = int(step.get("step_order", 0))
        step_type = classify_step(step)
        tagged.append((order, step_type, step))
    tagged.sort(key=lambda x: x[0])
    return tagged


def build_execution_plan(
    steps: list[dict],
    case_id: str,
) -> dict:
    """Build an execution plan that maps each step to its execution engine."""
    tagged_steps = interleave_steps(steps)
    playwright_steps = 0
    local_steps = 0
    ssh_steps = 0

    plan = {
        "case_id": case_id,
        "total_steps": len(steps),
        "step_sequence": [],
        "engine_transitions": [],
    }

    prev_type = None
    for order, step_type, step in tagged_steps:
        plan["step_sequence"].append({
            "step_order": order,
            "step_type": step_type.value,
            "engine": "fix-scripts" if step_type == StepType.PLAYWRIGHT else "terminal-executor",
            "command": step.get("command", ""),
            "command_type": step.get("command_type", step_type.value),
            "expected_output": step.get("expected_output"),
        })

        if step_type == StepType.PLAYWRIGHT:
            playwright_steps += 1
        elif step_type == StepType.LOCAL:
            local_steps += 1
        elif step_type == StepType.SSH:
            ssh_steps += 1

        if prev_type and prev_type != step_type:
            plan["engine_transitions"].append({
                "at_step": order,
                "from": prev_type.value,
                "to": step_type.value,
            })
        prev_type = step_type

    plan["summary"] = {
        "playwright_steps": playwright_steps,
        "local_command_steps": local_steps,
        "ssh_command_steps": ssh_steps,
        "engine_switches": len(plan["engine_transitions"]),
        "is_hybrid": playwright_steps > 0 and (local_steps + ssh_steps) > 0,
    }

    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch steps to Playwright or command engines.")
    parser.add_argument("--case-id", required=True, help="Case identifier.")
    parser.add_argument("--steps-file", help="JSON file with step definitions.")
    parser.add_argument("--steps-json", help="JSON string with step definitions.")
    parser.add_argument("--output", "-o", help="Write execution plan to file.")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    steps_data = args.steps_json
    if args.steps_file:
        steps_data = Path(args.steps_file).read_text(encoding="utf-8")

    if not steps_data:
        print("No steps provided. Use --steps-file or --steps-json.", file=sys.stderr)
        return 1

    try:
        steps = json.loads(steps_data)
        if isinstance(steps, dict):
            steps = steps.get("steps", [])
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    plan = build_execution_plan(steps, args.case_id)

    if args.json:
        print(json.dumps(plan, ensure_ascii=True, indent=2))
    else:
        s = plan["summary"]
        print(f"Case: {plan['case_id']}  Steps: {plan['total_steps']}")
        print(f"  Playwright: {s['playwright_steps']} | Local: {s['local_command_steps']} | SSH: {s['ssh_command_steps']}")
        print(f"  Hybrid: {s['is_hybrid']}  Engine switches: {s['engine_switches']}")
        for t in plan["engine_transitions"]:
            print(f"  Step {t['at_step']}: {t['from']} → {t['to']}")

    if args.output:
        Path(args.output).write_text(json.dumps(plan, ensure_ascii=True, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
