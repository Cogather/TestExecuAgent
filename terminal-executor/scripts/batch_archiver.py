#!/usr/bin/env python3
"""Batch archiver — package all step artifacts for upload and finalization."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def collect_artifacts(case_dir: Path) -> dict:
    """Walk the case directory and collect metadata about all artifacts."""
    artifacts = {
        "case_dir": str(case_dir),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "step_dirs": [],
        "report_files": [],
        "other_files": [],
        "total_size_bytes": 0,
    }

    if not case_dir.is_dir():
        artifacts["error"] = "case directory not found"
        return artifacts

    for item in sorted(case_dir.iterdir()):
        if item.is_dir() and item.name.startswith("step_"):
            step_info = {"name": item.name, "files": [], "size_bytes": 0}
            for f in sorted(item.iterdir()):
                fsize = f.stat().st_size
                step_info["files"].append({"name": f.name, "size_bytes": fsize})
                step_info["size_bytes"] += fsize
            artifacts["step_dirs"].append(step_info)
            artifacts["total_size_bytes"] += step_info["size_bytes"]
        elif item.is_file():
            fsize = item.stat().st_size
            file_info = {"name": item.name, "size_bytes": fsize}
            if item.name.endswith((".md", ".json", ".yaml", ".yml", ".log")):
                artifacts["report_files"].append(file_info)
            else:
                artifacts["other_files"].append(file_info)
            artifacts["total_size_bytes"] += fsize

    return artifacts


def create_tarball(case_dir: Path, output_path: Path) -> Path:
    """Create a .tar.gz archive of the case directory."""
    output_path = output_path.resolve()
    with tarfile.open(output_path, "w:gz") as tar:
        for item in sorted(case_dir.rglob("*")):
            arcname = str(item.relative_to(case_dir.parent))
            tar.add(str(item), arcname=arcname)
    return output_path


def create_zip(case_dir: Path, output_path: Path) -> Path:
    """Create a .zip archive of the case directory."""
    output_path = output_path.resolve()
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(case_dir.rglob("*")):
            if item.is_file():
                arcname = str(item.relative_to(case_dir.parent))
                zf.write(str(item), arcname=arcname)
    return output_path


def cleanup_workspace(
    case_dir: Path,
    mode: str = "safe",
    keep_patterns: list[str] | None = None,
) -> list[str]:
    """Clean up workspace directory. 'safe' keeps reports/; 'aggressive' removes everything."""
    if keep_patterns is None:
        keep_patterns = ["reports/", "flow_validation_report.md", "report.md"]

    removed = []
    if mode == "aggressive":
        for item in sorted(case_dir.rglob("*"), reverse=True):
            if item.is_file():
                item.unlink()
                removed.append(str(item))
        # Remove empty dirs
        for item in sorted(case_dir.rglob("*"), reverse=True):
            if item.is_dir() and item != case_dir and not any(item.iterdir()):
                item.rmdir()
                removed.append(str(item))
        return removed

    # safe mode: remove temp files, keep reports
    for item in sorted(case_dir.rglob("*")):
        if item.is_dir():
            continue
        relative = str(item.relative_to(case_dir))
        should_keep = any(relative.startswith(p.rstrip("/")) for p in keep_patterns)
        if not should_keep:
            item.unlink()
            removed.append(str(item))

    return removed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch archiver for case artifacts.")
    sub = parser.add_subparsers(dest="action", required=True)

    collect_p = sub.add_parser("collect", help="Collect artifact metadata.")
    collect_p.add_argument("--case-dir", required=True, help="Path to ./<case_id>/")

    archive_p = sub.add_parser("archive", help="Create archive of case directory.")
    archive_p.add_argument("--case-dir", required=True, help="Path to ./<case_id>/")
    archive_p.add_argument("--format", choices=["tar.gz", "zip"], default="tar.gz", help="Archive format.")
    archive_p.add_argument("--output", "-o", required=True, help="Output archive path.")

    clean_p = sub.add_parser("cleanup", help="Clean up workspace.")
    clean_p.add_argument("--case-dir", required=True, help="Path to ./<case_id>/")
    clean_p.add_argument("--mode", choices=["safe", "aggressive"], default="safe", help="Cleanup mode.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.action == "collect":
        artifacts = collect_artifacts(Path(args.case_dir))
        print(json.dumps(artifacts, ensure_ascii=True, indent=2))
        return 0 if "error" not in artifacts else 1

    elif args.action == "archive":
        case_dir = Path(args.case_dir)
        output = Path(args.output)
        if args.format == "tar.gz":
            result = create_tarball(case_dir, output)
        else:
            result = create_zip(case_dir, output)
        print(f"Archive created: {result} ({result.stat().st_size} bytes)")
        return 0

    elif args.action == "cleanup":
        case_dir = Path(args.case_dir)
        removed = cleanup_workspace(case_dir, mode=args.mode)
        if removed:
            print(f"Removed {len(removed)} files ({args.mode} mode):")
            for f in removed[:20]:
                print(f"  {f}")
            if len(removed) > 20:
                print(f"  ... and {len(removed) - 20} more")
        else:
            print("Nothing to clean up.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
