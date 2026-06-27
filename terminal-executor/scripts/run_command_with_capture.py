#!/usr/bin/env python3
"""Execute a command (local or SSH) with full log capture, mirroring fix-scripts capture format."""

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


def step_dir_name(step: str) -> str:
    step = step.strip()
    if step.isdigit():
        return f"step_{int(step)}"
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in step)
    return f"step_{safe or 'unknown'}"


def redact_sensitive(text: str) -> str:
    import re
    patterns = [
        (r'(?:password|passwd|secret|token|api_key|api_secret)\s*[=:]\s*\S+', '***=***'),
        (r'-----BEGIN.*?PRIVATE KEY-----.*?-----END.*?PRIVATE KEY-----', '[REDACTED_KEY]'),
        (r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED_JWT]'),
    ]
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.DOTALL | re.IGNORECASE)
    return result


def build_command(args: argparse.Namespace) -> list[str]:
    """Build the shell command list. SSH commands include ssh prefix."""
    command_type = args.command_type
    raw_command = args.command

    if command_type == "local":
        return ["bash", "-c", raw_command]
    elif command_type == "ssh":
        port_flag = ["-p", str(args.ssh_port)] if args.ssh_port else []
        strict_check = "-o StrictHostKeyChecking=no"
        batch_mode = "-o BatchMode=yes"
        connect_timeout = "-o ConnectTimeout=10"

        ssh_prefix = [
            "ssh", strict_check, batch_mode, connect_timeout, *port_flag,
            f"{args.ssh_user}@{args.ssh_host}",
        ]
        return ssh_prefix + [raw_command]
    else:
        raise ValueError(f"Unknown command_type: {command_type}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute a command and capture stdout/stderr/execution metadata."
    )
    parser.add_argument("--case-id", required=True, help="Case identifier.")
    parser.add_argument("--step", required=True, help="Step index or label.")
    parser.add_argument("--command", required=True, help="Full command string to execute.")
    parser.add_argument(
        "--command-type", required=True, choices=["local", "ssh"], help="Execution mode."
    )
    parser.add_argument(
        "--output-dir", required=True, help="Base output directory (./<case_id>)."
    )
    parser.add_argument("--timeout-seconds", type=int, default=120, help="Execution timeout.")
    # SSH options
    parser.add_argument("--ssh-host", help="SSH remote host.")
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port.")
    parser.add_argument("--ssh-user", help="SSH username.")
    parser.add_argument(
        "--env", action="append", default=[],
        help="Extra env var in KEY=VALUE format. Repeatable."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir = Path(args.output_dir).resolve()
    step_dir = base_dir / step_dir_name(args.step)
    step_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = step_dir / "stdout.log"
    stderr_path = step_dir / "stderr.log"
    execution_path = step_dir / "execution.json"
    audit_path = step_dir / "execution.log"

    command = build_command(args)
    start = time.time()
    start_time = utc_now()

    run_env = os.environ.copy()
    for pair in args.env:
        if "=" in pair:
            k, v = pair.split("=", 1)
            run_env[k.strip()] = v

    exit_code = 1
    timed_out = False
    stdout_text = ""
    stderr_text = ""
    error_message = ""

    try:
        completed = subprocess.run(
            command, capture_output=True, text=True,
            timeout=args.timeout_seconds, env=run_env,
        )
        exit_code = completed.returncode
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout_text = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr_text = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        error_message = f"Command timed out after {args.timeout_seconds}s."
    except FileNotFoundError:
        exit_code = 127
        error_message = f"Executable not found: {command[0]}"
    except Exception as exc:
        exit_code = 1
        error_message = f"Execution failed: {exc}"

    duration = round(time.time() - start, 3)
    end_time = utc_now()

    if error_message and error_message not in stderr_text:
        stderr_text = (stderr_text + "\n" + error_message).strip() + "\n"

    # Redact before writing to disk
    stdout_text_safe = redact_sensitive(stdout_text)
    stderr_text_safe = redact_sensitive(stderr_text)

    stdout_path.write_text(stdout_text_safe, encoding="utf-8")
    stderr_path.write_text(stderr_text_safe, encoding="utf-8")

    payload = {
        "step_order": args.step,
        "exit_code": exit_code,
        "duration_ms": int(duration * 1000),
        "command": redact_sensitive(args.command),
        "command_type": args.command_type,
        "error_summary": error_message,
        "timed_out": timed_out,
        "start_time": start_time,
        "end_time": end_time,
        "case_id": args.case_id,
    }
    execution_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    # Append audit entry
    audit_entry = {
        "timestamp": start_time,
        "step": args.step,
        "command": redact_sensitive(args.command),
        "command_type": args.command_type,
        "exit_code": exit_code,
        "duration_ms": int(duration * 1000),
        "timed_out": timed_out,
    }
    with open(audit_path, "a", encoding="utf-8") as af:
        af.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")

    print(json.dumps(payload, ensure_ascii=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
