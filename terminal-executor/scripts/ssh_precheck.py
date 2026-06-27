#!/usr/bin/env python3
"""SSH connectivity pre-check — tests if a remote host is reachable via SSH."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def probe_ssh(host: str, port: int, user: str, timeout: int = 10) -> dict:
    """Run a quick SSH echo check and return structured result."""
    command = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=no",
        "-o", f"ConnectTimeout={timeout}",
        "-p", str(port),
        f"{user}@{host}",
        "echo ok",
    ]

    start = time.time()
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout + 5,
        )
        duration_ms = int((time.time() - start) * 1000)
        return {
            "host": host,
            "port": port,
            "user": user,
            "reachable": result.returncode == 0 and "ok" in result.stdout,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr_abridged": result.stderr.strip()[:200] if result.stderr else "",
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired:
        return {
            "host": host, "port": port, "user": user,
            "reachable": False, "exit_code": 124,
            "stdout": "", "stderr_abridged": "Connection timed out",
            "duration_ms": int((time.time() - start) * 1000),
        }
    except FileNotFoundError:
        return {
            "host": host, "port": port, "user": user,
            "reachable": False, "exit_code": 127,
            "stdout": "", "stderr_abridged": "ssh command not found",
            "duration_ms": 0,
        }
    except Exception as exc:
        return {
            "host": host, "port": port, "user": user,
            "reachable": False, "exit_code": -1,
            "stdout": "", "stderr_abridged": str(exc),
            "duration_ms": int((time.time() - start) * 1000),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-check SSH connectivity to a remote host.")
    parser.add_argument("--host", required=True, help="SSH remote host.")
    parser.add_argument("--port", type=int, default=22, help="SSH port.")
    parser.add_argument("--user", required=True, help="SSH username.")
    parser.add_argument("--timeout", type=int, default=10, help="Connect timeout in seconds.")
    parser.add_argument("--output", "-o", help="Write JSON result to file.")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = probe_ssh(args.host, args.port, args.user, args.timeout)

    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        status = "OK" if result["reachable"] else "FAILED"
        print(f"[{status}] {result['user']}@{result['host']}:{result['port']} "
              f"({result['duration_ms']}ms)")

    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")

    return 0 if result["reachable"] else 1


if __name__ == "__main__":
    sys.exit(main())
