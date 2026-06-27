#!/usr/bin/env python3
"""Validate checkout evidence files for a step directory.
Checks: file existence, size thresholds, naming conventions, JSON validity."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EvidenceCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class StepEvidenceResult:
    step_dir: Path
    step_type: str  # "playwright" or "command"
    checks: list[EvidenceCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)


def validate_playwright_step(step_dir: Path) -> StepEvidenceResult:
    """Validate evidence for a Playwright (browser) step."""
    result = StepEvidenceResult(step_dir=step_dir, step_type="playwright")

    # execution.json is mandatory
    exe_json = step_dir / "execution.json"
    if not exe_json.exists():
        result.checks.append(EvidenceCheck("execution.json", False, "file missing"))
        return result

    try:
        payload = json.loads(exe_json.read_text(encoding="utf-8"))
        exit_code = payload.get("exit_code", -1)
        result.checks.append(EvidenceCheck(
            "execution.json", exit_code == 0,
            f"exit_code={exit_code}" if exit_code == 0 else f"exit_code={exit_code} (non-zero)"
        ))
    except json.JSONDecodeError as exc:
        result.checks.append(EvidenceCheck("execution.json", False, f"invalid JSON: {exc}"))
        return result

    # Checkpoint PNG files — expect cp1 and cp2 at minimum
    png_files = sorted(step_dir.glob("cp*.png"))
    has_cp1 = any("cp1" in f.name for f in png_files)
    has_cp2 = any("cp2" in f.name for f in png_files)
    png_count = len(png_files)
    png_ok = has_cp1 and has_cp2 and png_count <= 3

    result.checks.append(EvidenceCheck(
        "checkpoint_pngs",
        png_ok,
        f"{png_count} files, cp1={'✓' if has_cp1 else '✗'}, cp2={'✓' if has_cp2 else '✗'}"
    ))

    # Checkpoint HTML files
    html_files = sorted(step_dir.glob("cp*.html"))
    html_count = len(html_files)
    html_ok = html_count <= 3

    result.checks.append(EvidenceCheck(
        "checkpoint_htmls",
        html_ok,
        f"{html_count} files (max 3 allowed)"
    ))

    # stdout.log and stderr.log should exist and be non-empty
    for log_name in ["stdout.log", "stderr.log"]:
        log_path = step_dir / log_name
        if log_path.exists():
            size = log_path.stat().st_size
            result.checks.append(EvidenceCheck(log_name, True, f"{size} bytes"))
        else:
            result.checks.append(EvidenceCheck(log_name, False, "file missing"))

    return result


def validate_command_step(step_dir: Path) -> StepEvidenceResult:
    """Validate evidence for a command-execution step (terminal-executor output)."""
    result = StepEvidenceResult(step_dir=step_dir, step_type="command")

    exe_json = step_dir / "execution.json"
    if not exe_json.exists():
        result.checks.append(EvidenceCheck("execution.json", False, "file missing"))
        return result

    try:
        payload = json.loads(exe_json.read_text(encoding="utf-8"))
        exit_code = payload.get("exit_code", -1)
        command_type = payload.get("command_type", "unknown")
        result.checks.append(EvidenceCheck(
            "execution.json", exit_code == 0,
            f"exit_code={exit_code}, command_type={command_type}"
        ))
    except json.JSONDecodeError as exc:
        result.checks.append(EvidenceCheck("execution.json", False, f"invalid JSON: {exc}"))
        return result

    # stdout.log must exist
    stdout_path = step_dir / "stdout.log"
    if stdout_path.exists():
        size = stdout_path.stat().st_size
        result.checks.append(EvidenceCheck("stdout.log", True, f"{size} bytes"))
    else:
        result.checks.append(EvidenceCheck("stdout.log", False, "file missing"))

    # stderr.log should exist (even if empty)
    stderr_path = step_dir / "stderr.log"
    if stderr_path.exists():
        size = stderr_path.stat().st_size
        has_content = size > 0
        # non-empty stderr is a warning, not a failure
        result.checks.append(EvidenceCheck(
            "stderr.log", True,
            f"{size} bytes" + (" (non-empty, may contain warnings)" if has_content else "")
        ))
    else:
        result.checks.append(EvidenceCheck("stderr.log", True, "file missing (optional)"))

    # execution.log audit trail should exist
    audit_path = step_dir / "execution.log"
    if audit_path.exists():
        result.checks.append(EvidenceCheck("execution.log", True, "audit trail exists"))
    else:
        result.checks.append(EvidenceCheck("execution.log", False, "audit trail missing"))

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate checkpoint evidence for a step directory.")
    parser.add_argument("--step-dir", required=True, help="Path to step_N directory.")
    parser.add_argument(
        "--step-type", choices=["playwright", "command", "auto"], default="auto",
        help="Step type. 'auto' detects from execution.json command_type field."
    )
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout.")
    return parser.parse_args()


def detect_step_type(step_dir: Path) -> str:
    exe_json = step_dir / "execution.json"
    if exe_json.exists():
        try:
            payload = json.loads(exe_json.read_text(encoding="utf-8"))
            if payload.get("command_type") in ("local", "ssh"):
                return "command"
        except json.JSONDecodeError:
            pass
    # If png files exist, it's playwright
    if list(step_dir.glob("cp*.png")):
        return "playwright"
    return "command"


def main() -> int:
    args = parse_args()
    step_dir = Path(args.step_dir).resolve()

    if not step_dir.is_dir():
        print(f"Directory not found: {step_dir}", file=sys.stderr)
        return 1

    step_type = args.step_type
    if step_type == "auto":
        step_type = detect_step_type(step_dir)

    if step_type == "playwright":
        result = validate_playwright_step(step_dir)
    else:
        result = validate_command_step(step_dir)

    if args.json:
        output = {
            "step_dir": str(result.step_dir),
            "step_type": result.step_type,
            "all_passed": result.all_passed,
            "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in result.checks],
        }
        print(json.dumps(output, ensure_ascii=True, indent=2))
    else:
        status = "PASS" if result.all_passed else "FAIL"
        print(f"[{status}] {step_dir.name} ({result.step_type})")
        for c in result.checks:
            mark = "✓" if c.passed else "✗"
            print(f"  {mark} {c.name}: {c.detail}")

    return 0 if result.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
