"""Unit tests for pipeline_state.py."""

import pytest


def test_web_stages(pipeline_state):
    state = pipeline_state.PipelineState(case_id="CASE_001", case_type=pipeline_state.CaseType.WEB)
    stages = state.stages
    assert pipeline_state.PipelineStage.BOOTSTRAP in stages
    assert pipeline_state.PipelineStage.FIX in stages
    assert pipeline_state.PipelineStage.TERMINAL_EXEC not in stages


def test_mml_has_terminal_executor(pipeline_state):
    state = pipeline_state.PipelineState(case_id="CASE_002", case_type=pipeline_state.CaseType.MML)
    assert pipeline_state.PipelineStage.TERMINAL_EXEC in state.stages
    assert pipeline_state.PipelineStage.RECORD not in state.stages


def test_api_matches_mml(pipeline_state):
    state = pipeline_state.PipelineState(case_id="CASE_003", case_type=pipeline_state.CaseType.API)
    assert pipeline_state.PipelineStage.TERMINAL_EXEC in state.stages


def test_hybrid_has_both(pipeline_state):
    state = pipeline_state.PipelineState(case_id="CASE_004", case_type=pipeline_state.CaseType.HYBRID)
    assert pipeline_state.PipelineStage.FIX in state.stages
    assert pipeline_state.PipelineStage.TERMINAL_EXEC in state.stages


def test_initial_stage(pipeline_state):
    state = pipeline_state.PipelineState(case_id="X", case_type=pipeline_state.CaseType.WEB)
    assert state.current_stage == pipeline_state.PipelineStage.BOOTSTRAP


def test_next_stage(pipeline_state):
    state = pipeline_state.PipelineState(case_id="X", case_type=pipeline_state.CaseType.WEB)
    assert state.next_stage == pipeline_state.PipelineStage.ENV_PREP


def test_mark_complete(pipeline_state):
    state = pipeline_state.PipelineState(case_id="X", case_type=pipeline_state.CaseType.WEB)
    state.mark_stage_complete(pipeline_state.PipelineStage.BOOTSTRAP, "ok")
    assert "bootstrap" in state.completed_stages


def test_mark_complete_idempotent(pipeline_state):
    state = pipeline_state.PipelineState(case_id="X", case_type=pipeline_state.CaseType.WEB)
    state.mark_stage_complete(pipeline_state.PipelineStage.ENV_PREP, "ok")
    state.mark_stage_complete(pipeline_state.PipelineStage.ENV_PREP, "ok")
    assert state.completed_stages.count("env-preparation") == 1


def test_advance(pipeline_state):
    state = pipeline_state.PipelineState(case_id="X", case_type=pipeline_state.CaseType.WEB)
    state.advance(pipeline_state.CaseStatus.PREPARING)
    assert state.current_status == pipeline_state.CaseStatus.PREPARING


def test_to_dict_from_dict(pipeline_state):
    state = pipeline_state.PipelineState(case_id="RT", case_type=pipeline_state.CaseType.HYBRID)
    state.mark_stage_complete(pipeline_state.PipelineStage.BOOTSTRAP, "ok")
    state.advance(pipeline_state.CaseStatus.EXECUTING)
    restored = pipeline_state.PipelineState.from_dict(state.to_dict())
    assert restored.case_id == "RT"
    assert restored.case_type == pipeline_state.CaseType.HYBRID


def test_save_load(pipeline_state, tmp_path):
    state = pipeline_state.PipelineState(case_id="SAVE1", case_type=pipeline_state.CaseType.MML)
    path = tmp_path / "state.json"
    state.save(path)
    loaded = pipeline_state.PipelineState.load(path)
    assert loaded is not None
    assert loaded.case_id == "SAVE1"


def test_load_nonexistent(pipeline_state):
    from pathlib import Path
    assert pipeline_state.PipelineState.load(Path("/nonexistent.json")) is None


def test_load_corrupted(pipeline_state, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{bad")
    assert pipeline_state.PipelineState.load(p) is None


def test_web_full_flow(pipeline_state):
    state = pipeline_state.PipelineState(case_id="FLOW", case_type=pipeline_state.CaseType.WEB)
    PS = pipeline_state.PipelineStage
    CS = pipeline_state.CaseStatus

    state.advance(CS.PREPARING); state.mark_stage_complete(PS.BOOTSTRAP, "ok")
    assert state.current_stage == PS.ENV_PREP

    state.advance(CS.RECORDING); state.mark_stage_complete(PS.ENV_PREP, "ok")
    state.advance(CS.FIXING); state.mark_stage_complete(PS.RECORD, "ok")
    state.advance(CS.CHECKING); state.mark_stage_complete(PS.FIX, "ok")
    state.advance(CS.FINALIZING); state.mark_stage_complete(PS.CHECKPOINT, "ok")
    state.mark_stage_complete(PS.FINALIZE, "ok")
    state.advance(CS.PASSED)
    assert state.current_status == pipeline_state.CaseStatus.PASSED
    assert len(state.completed_stages) == 6


def test_mml_flow(pipeline_state):
    state = pipeline_state.PipelineState(case_id="MML", case_type=pipeline_state.CaseType.MML)
    assert pipeline_state.PipelineStage.TERMINAL_EXEC in state.stages
    assert pipeline_state.PipelineStage.RECORD not in state.stages
