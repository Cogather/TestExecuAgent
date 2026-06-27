#!/usr/bin/env python3
"""Aggregate multiple step execution.json files into a case-level summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def collect_step_results(case_dir: Path) -> list[dict]:
    """Scan step_N directories and collect all execution.json payloads."""
    results = []
    for step_dir in sorted(case_dir.glob("step_*")):
        if not step_dir.is_dir():
            continue
        exe_json = step_dir / "execution.json"
        if not exe_json.exists():
            results.append({
                "step": step_dir.name,
                "exit_code": None,
                "error_summary": "execution.json not found",
                "status": "missing",
            })
            continue
        try:
            payload = json.loads(exe_json.read_text(encoding="utf-8"))
            payload.setdefault("status", "passed" if payload.get("exit_code") == 0 else "failed")
            results.append(payload)
        except json.JSONDecodeError as exc:
            results.append({
                "step": step_dir.name,
                "exit_code": None,
                "error_summary": f"JSON parse error: {exc}",
                "status": "corrupted",
            })
    return results


def summarize(results: list[dict]) -> dict:
    """Produce a case-level summary from step results."""
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "passed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    missing = sum(1 for r in results if r.get("status") == "missing")
    corrupted = sum(1 for r in results if r.get("status") == "corrupted")
    timed_out = sum(1 for r in results if r.get("timed_out"))

    overall = "passed"
    if failed > 0 or corrupted > 0:
        overall = "failed"
    elif missing > 0:
        overall = "incomplete"

    return {
        "total_steps": total,
        "passed": passed,
        "failed": failed,
        "missing": missing,
        "corrupted": corrupted,
        "timed_out": timed_out,
        "overall": overall,
        "step_details": [
            {
                "step": r.get("step", r.get("step_order", "?")),
                "command_type": r.get("command_type", "playwright"),
                "exit_code": r.get("exit_code"),
                "duration_ms": r.get("duration_ms", r.get("duration_seconds", 0)),
                "error_summary": r.get("error_summary", r.get("error_message", "")),
                "status": r.get("status", "unknown"),
            }
            for r in results
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate step results into a case summary.")
    parser.add_argument("--case-dir", required=True, help="Path to ./<case_id>/ directory.")
    parser.add_argument("--output", "-o", help="Write summary JSON to file.")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case_dir = Path(args.case_dir).resolve()
    if not case_dir.is_dir():
        print(f"Directory not found: {case_dir}", file=sys.stderr)
        return 1

    results = collect_step_results(case_dir)
    summary = summarize(results)

    if args.json:
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        print(f"Steps: {summary['total_steps']} total, "
              f"{summary['passed']} passed, {summary['failed']} failed, "
              f"{summary['missing']} missing — overall: {summary['overall']}")

    if args.output:
        Path(args.output).write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")

    return 0 if summary["overall"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
