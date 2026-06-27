"""Shared pytest fixtures for terminal-executor and checkpoint-debug-reporter tests."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TERMINAL_SCRIPTS = _PROJECT_ROOT / "terminal-executor" / "scripts"
_CHECKPOINT_SCRIPTS = _PROJECT_ROOT / "checkpoint-debug-reporter" / "scripts"


def _import_module(module_name: str, file_path: Path):
    """Import a Python module from an arbitrary file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def cmd_sanitizer():
    return _import_module("cmd_sanitizer", _TERMINAL_SCRIPTS / "cmd_sanitizer.py")


@pytest.fixture(scope="session")
def run_command():
    return _import_module("run_command_with_capture", _TERMINAL_SCRIPTS / "run_command_with_capture.py")


@pytest.fixture(scope="session")
def ssh_precheck():
    return _import_module("ssh_precheck", _TERMINAL_SCRIPTS / "ssh_precheck.py")


@pytest.fixture(scope="session")
def result_aggregator():
    return _import_module("result_aggregator", _TERMINAL_SCRIPTS / "result_aggregator.py")


@pytest.fixture(scope="session")
def pipeline_state():
    return _import_module("pipeline_state", _TERMINAL_SCRIPTS / "pipeline_state.py")


@pytest.fixture(scope="session")
def case_router():
    return _import_module("case_router", _TERMINAL_SCRIPTS / "case_router.py")


@pytest.fixture(scope="session")
def step_dispatcher():
    return _import_module("step_dispatcher", _TERMINAL_SCRIPTS / "step_dispatcher.py")


@pytest.fixture(scope="session")
def batch_archiver():
    return _import_module("batch_archiver", _TERMINAL_SCRIPTS / "batch_archiver.py")


@pytest.fixture(scope="session")
def cmd_output_matcher():
    return _import_module("cmd_output_matcher", _CHECKPOINT_SCRIPTS / "cmd_output_matcher.py")


@pytest.fixture(scope="session")
def evidence_validator():
    return _import_module("evidence_validator", _CHECKPOINT_SCRIPTS / "evidence_validator.py")


# ---- reusable test data fixtures ----

@pytest.fixture
def sample_step_data():
    return {
        "step_order": "1",
        "exit_code": 0,
        "duration_ms": 500,
        "command": "mml show version",
        "command_type": "ssh",
        "error_summary": "",
        "timed_out": False,
    }


@pytest.fixture
def tmp_case_dir(tmp_path):
    case_dir = tmp_path / "CASE_001"
    case_dir.mkdir()
    step_dir = case_dir / "step_1"
    step_dir.mkdir()
    return case_dir


@pytest.fixture
def tmp_case_with_steps(tmp_path):
    case_dir = tmp_path / "CASE_002"
    case_dir.mkdir()
    for i in range(1, 4):
        step_dir = case_dir / f"step_{i}"
        step_dir.mkdir()
        payload = {
            "step_order": str(i),
            "exit_code": 0 if i != 2 else 1,
            "duration_ms": 200 * i,
            "command": f"mml step {i}",
            "command_type": "ssh",
            "error_summary": "" if i != 2 else "command failed",
            "timed_out": False,
        }
        (step_dir / "execution.json").write_text(json.dumps(payload))
    return case_dir


@pytest.fixture
def tmp_playwright_step_dir(tmp_path):
    step_dir = tmp_path / "step_1"
    step_dir.mkdir()
    exec_json = {"step_order": "1", "exit_code": 0, "duration_ms": 3000, "error_summary": ""}
    (step_dir / "execution.json").write_text(json.dumps(exec_json))
    (step_dir / "stdout.log").write_text("page loaded\n")
    (step_dir / "stderr.log").write_text("")
    (step_dir / "cp1_after_page_ready.png").write_bytes(b"\x89PNG")
    (step_dir / "cp2_after_key_action.png").write_bytes(b"\x89PNG")
    (step_dir / "cp1_after_page_ready.html").write_text("<html></html>")
    (step_dir / "cp2_after_key_action.html").write_text("<html></html>")
    return step_dir


@pytest.fixture
def tmp_command_step_dir(tmp_path):
    step_dir = tmp_path / "step_cmd_1"
    step_dir.mkdir()
    exec_json = {
        "step_order": "1", "exit_code": 0, "duration_ms": 500,
        "command": "mml show version", "command_type": "ssh", "error_summary": "",
    }
    (step_dir / "execution.json").write_text(json.dumps(exec_json))
    (step_dir / "stdout.log").write_text("Version: 2.3.1\nBuild: 20250101\n")
    (step_dir / "stderr.log").write_text("")
    (step_dir / "execution.log").write_text(json.dumps({"entry": "ok"}) + "\n")
    return step_dir
