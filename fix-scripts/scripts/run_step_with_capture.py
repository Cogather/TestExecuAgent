#!/usr/bin/env python3
"""Run a step script through a wrapper and persist execution logs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_env_pairs(pairs: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Invalid --env item: {item!r}. Use KEY=VALUE.")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid --env item: {item!r}. KEY is empty.")
        result[key] = value
    return result


def step_dir_name(step: str) -> str:
    step = step.strip()
    if step.isdigit():
        return f"step_{int(step)}"
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in step)
    return f"step_{safe or 'unknown'}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute one step script and capture stdout/stderr/execution metadata."
    )
    parser.add_argument("--case-id", required=True, help="Case id.")
    parser.add_argument("--step", required=True, help="Step index or label.")
    parser.add_argument("--script", required=True, help="Path of step script to execute.")
    parser.add_argument(
        "--output-dir", required=True, help="Base output directory for captured artifacts."
    )
    parser.add_argument(
        "--python-path",
        default=sys.executable,
        help="Python interpreter used to run the step script.",
    )
    parser.add_argument(
        "--timeout-seconds", type=int, default=900, help="Execution timeout in seconds."
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        help="Extra environment variable in KEY=VALUE format. Repeatable.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = Path(args.script).resolve()
    base_output_dir = Path(args.output_dir).resolve()
    step_dir = base_output_dir / step_dir_name(args.step)
    step_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = step_dir / "stdout.log"
    stderr_path = step_dir / "stderr.log"
    execution_path = step_dir / "execution.json"

    if not script_path.exists():
        payload = {
            "case_id": args.case_id,
            "step": args.step,
            "script": str(script_path),
            "exit_code": 127,
            "error_message": f"Script not found: {script_path}",
            "start_time": utc_now(),
            "end_time": utc_now(),
            "duration_seconds": 0.0,
            "timed_out": False,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        }
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(payload["error_message"], encoding="utf-8")
        execution_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=True))
        return 127

    command = [args.python_path, str(script_path)]
    start = time.time()
    start_time = utc_now()

    run_env = os.environ.copy()
    run_env.update(parse_env_pairs(args.env))
    run_env.setdefault("STEP_CAPTURE_DIR", str(step_dir / "reports" / "checkpoints"))
    (step_dir / "reports" / "checkpoints").mkdir(parents=True, exist_ok=True)

    exit_code = 1
    timed_out = False
    stdout_text = ""
    stderr_text = ""
    error_message = ""

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=args.timeout_seconds,
            env=run_env,
        )
        exit_code = completed.returncode
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout_text = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr_text = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        error_message = f"Execution timed out after {args.timeout_seconds}s."
    except Exception as exc:  # pragma: no cover
        exit_code = 1
        error_message = f"Wrapper execution failed: {exc}"

    end_time = utc_now()
    duration = round(time.time() - start, 3)

    if error_message and error_message not in stderr_text:
        stderr_text = (stderr_text + "\n" + error_message).strip() + "\n"

    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")

    payload = {
        "case_id": args.case_id,
        "step": args.step,
        "script": str(script_path),
        "command": command,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "error_message": error_message,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "execution_path": str(execution_path),
    }
    execution_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
