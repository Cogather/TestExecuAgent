#!/usr/bin/env python3
"""Pipeline state machine for tracking test case execution progress through stages."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class CaseStatus(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    RECORDING = "recording"
    FIXING = "fixing"
    EXECUTING = "executing"
    CHECKING = "checking"
    FINALIZING = "finalizing"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class CaseType(str, Enum):
    WEB = "web"
    API = "api"
    MML = "mml"
    HYBRID = "hybrid"


class PipelineStage(str, Enum):
    BOOTSTRAP = "bootstrap"
    ENV_PREP = "env-preparation"
    RECORD = "record-scripts"
    FIX = "fix-scripts"
    TERMINAL_EXEC = "terminal-executor"
    CHECKPOINT = "checkpoint-debug-reporter"
    FINALIZE = "result-finalizer"
    DONE = "done"


# Stage sequence per case type
STAGE_SEQUENCES: dict[CaseType, list[PipelineStage]] = {
    CaseType.WEB: [
        PipelineStage.BOOTSTRAP, PipelineStage.ENV_PREP, PipelineStage.RECORD,
        PipelineStage.FIX, PipelineStage.CHECKPOINT, PipelineStage.FINALIZE,
        PipelineStage.DONE,
    ],
    CaseType.API: [
        PipelineStage.BOOTSTRAP, PipelineStage.ENV_PREP, PipelineStage.TERMINAL_EXEC,
        PipelineStage.CHECKPOINT, PipelineStage.FINALIZE, PipelineStage.DONE,
    ],
    CaseType.MML: [
        PipelineStage.BOOTSTRAP, PipelineStage.ENV_PREP, PipelineStage.TERMINAL_EXEC,
        PipelineStage.CHECKPOINT, PipelineStage.FINALIZE, PipelineStage.DONE,
    ],
    CaseType.HYBRID: [
        PipelineStage.BOOTSTRAP, PipelineStage.ENV_PREP, PipelineStage.RECORD,
        PipelineStage.FIX, PipelineStage.TERMINAL_EXEC, PipelineStage.CHECKPOINT,
        PipelineStage.FINALIZE, PipelineStage.DONE,
    ],
}

STATUS_TO_STAGE: dict[CaseStatus, PipelineStage] = {
    CaseStatus.PENDING: PipelineStage.BOOTSTRAP,
    CaseStatus.PREPARING: PipelineStage.ENV_PREP,
    CaseStatus.RECORDING: PipelineStage.RECORD,
    CaseStatus.FIXING: PipelineStage.FIX,
    CaseStatus.EXECUTING: PipelineStage.TERMINAL_EXEC,
    CaseStatus.CHECKING: PipelineStage.CHECKPOINT,
    CaseStatus.FINALIZING: PipelineStage.FINALIZE,
}


@dataclass
class PipelineState:
    case_id: str
    case_type: CaseType
    current_status: CaseStatus = CaseStatus.PENDING
    completed_stages: list[str] = field(default_factory=list)
    stage_results: dict[str, str] = field(default_factory=dict)
    started_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.started_at:
            self.started_at = now
        if not self.updated_at:
            self.updated_at = now

    @property
    def stages(self) -> list[PipelineStage]:
        return STAGE_SEQUENCES.get(self.case_type, STAGE_SEQUENCES[CaseType.WEB])

    @property
    def current_stage(self) -> PipelineStage:
        return STATUS_TO_STAGE.get(self.current_status, PipelineStage.BOOTSTRAP)

    @property
    def next_stage(self) -> Optional[PipelineStage]:
        stages = self.stages
        try:
            idx = stages.index(self.current_stage)
            if idx + 1 < len(stages):
                return stages[idx + 1]
        except ValueError:
            pass
        return None

    def mark_stage_complete(self, stage: PipelineStage, result: str = "ok") -> None:
        stage_str = stage.value
        if stage_str not in self.completed_stages:
            self.completed_stages.append(stage_str)
        self.stage_results[stage_str] = result
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def advance(self, next_status: CaseStatus) -> None:
        self.current_status = next_status
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "case_type": self.case_type.value,
            "current_status": self.current_status.value,
            "current_stage": self.current_stage.value,
            "next_stage": self.next_stage.value if self.next_stage else None,
            "completed_stages": self.completed_stages,
            "stage_results": self.stage_results,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PipelineState:
        return cls(
            case_id=data["case_id"],
            case_type=CaseType(data.get("case_type", "web")),
            current_status=CaseStatus(data.get("current_status", "pending")),
            completed_stages=data.get("completed_stages", []),
            stage_results=data.get("stage_results", {}),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Optional[PipelineState]:
        if not path.exists():
            return None
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError):
            return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline state machine utility.")
    sub = parser.add_subparsers(dest="action", required=True)

    init_p = sub.add_parser("init", help="Create a new pipeline state.")
    init_p.add_argument("--case-id", required=True, help="Case identifier.")
    init_p.add_argument("--case-type", required=True, choices=[t.value for t in CaseType], help="Case type.")

    advance_p = sub.add_parser("advance", help="Advance to the next stage.")
    advance_p.add_argument("--state-file", required=True, help="Path to pipeline_state.json.")
    advance_p.add_argument("--result", default="ok", help="Stage result: ok, failed, blocked.")

    show_p = sub.add_parser("show", help="Display current pipeline state.")
    show_p.add_argument("--state-file", required=True, help="Path to pipeline_state.json.")

    return parser.parse_args()


def cmd_init(args: argparse.Namespace) -> int:
    state = PipelineState(case_id=args.case_id, case_type=CaseType(args.case_type))
    stages = state.stages
    print(f"Case: {state.case_id}  Type: {state.case_type.value}")
    print(f"Stages: {' → '.join(s.value for s in stages)}")
    print(json.dumps(state.to_dict(), ensure_ascii=True, indent=2))
    return 0


def cmd_advance(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = PipelineState.load(state_path)
    if state is None:
        print(f"State file not found or invalid: {state_path}", file=sys.stderr)
        return 1

    current_stage = state.current_stage
    state.mark_stage_complete(current_stage, args.result)

    next_stage = state.next_stage
    if next_stage is None or next_stage == PipelineStage.DONE:
        state.advance(CaseStatus.PASSED if args.result == "ok" else CaseStatus.FAILED)
    else:
        # Map next stage to status
        stage_to_status = {v: k for k, v in STATUS_TO_STAGE.items()}
        next_status = stage_to_status.get(next_stage, CaseStatus.PENDING)
        state.advance(next_status)

    state.save(state_path)
    print(f"Advanced: {current_stage.value} → {state.current_stage.value} (result: {args.result})")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state = PipelineState.load(Path(args.state_file))
    if state is None:
        print(f"State file not found or invalid: {args.state_file}", file=sys.stderr)
        return 1
    print(f"Case: {state.case_id}  Type: {state.case_type.value}")
    print(f"Status: {state.current_status.value}  Stage: {state.current_stage.value}")
    print(f"Completed: {state.completed_stages}")
    print(f"Next: {state.next_stage.value if state.next_stage else 'done'}")
    return 0


def main() -> int:
    args = parse_args()
    if args.action == "init":
        return cmd_init(args)
    elif args.action == "advance":
        return cmd_advance(args)
    elif args.action == "show":
        return cmd_show(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
