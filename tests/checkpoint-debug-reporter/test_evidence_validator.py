"""Unit tests for evidence_validator.py."""

import json


def test_evidence_check(evidence_validator):
    c = evidence_validator.EvidenceCheck(name="t", passed=True)
    assert c.name == "t" and c.passed


def test_result_all_passed(evidence_validator):
    r = evidence_validator.StepEvidenceResult(step_dir=None, step_type="cmd")
    r.checks = [evidence_validator.EvidenceCheck("a", True)]
    assert r.all_passed


def test_result_not_all_passed(evidence_validator):
    r = evidence_validator.StepEvidenceResult(step_dir=None, step_type="cmd")
    r.checks = [evidence_validator.EvidenceCheck("a", False)]
    assert not r.all_passed


def test_detect_command(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    (d / "execution.json").write_text(json.dumps({"command_type": "ssh", "exit_code": 0}))
    assert evidence_validator.detect_step_type(d) == "command"


def test_detect_playwright(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    (d / "cp1.png").write_bytes(b"\x89PNG")
    assert evidence_validator.detect_step_type(d) == "playwright"


def test_detect_default_command(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    assert evidence_validator.detect_step_type(d) == "command"


def test_validate_playwright_ok(evidence_validator, tmp_playwright_step_dir):
    r = evidence_validator.validate_playwright_step(tmp_playwright_step_dir)
    assert r.all_passed


def test_validate_playwright_missing_exe(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    r = evidence_validator.validate_playwright_step(d)
    assert not r.all_passed


def test_validate_playwright_nonzero(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    (d / "execution.json").write_text(json.dumps({"exit_code": 1}))
    (d / "cp1.png").write_bytes(b"\x89"); (d / "cp2.png").write_bytes(b"\x89")
    (d / "stdout.log").write_text(""); (d / "stderr.log").write_text("")
    r = evidence_validator.validate_playwright_step(d)
    exe = next(c for c in r.checks if c.name == "execution.json")
    assert not exe.passed


def test_validate_playwright_no_cp1(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    (d / "execution.json").write_text(json.dumps({"exit_code": 0}))
    (d / "cp2.png").write_bytes(b"\x89")
    r = evidence_validator.validate_playwright_step(d)
    png = next(c for c in r.checks if c.name == "checkpoint_pngs")
    assert not png.passed


def test_validate_playwright_too_many(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    (d / "execution.json").write_text(json.dumps({"exit_code": 0}))
    for i in range(1, 5):
        (d / f"cp{i}.png").write_bytes(b"\x89")
    r = evidence_validator.validate_playwright_step(d)
    png = next(c for c in r.checks if c.name == "checkpoint_pngs")
    assert not png.passed


def test_validate_playwright_bad_json(evidence_validator, tmp_path):
    d = tmp_path / "s1"; d.mkdir()
    (d / "execution.json").write_text("{bad")
    r = evidence_validator.validate_playwright_step(d)
    exe = next(c for c in r.checks if c.name == "execution.json")
    assert not exe.passed


def test_validate_command_ok(evidence_validator, tmp_command_step_dir):
    r = evidence_validator.validate_command_step(tmp_command_step_dir)
    assert r.all_passed


def test_validate_command_no_exe(evidence_validator, tmp_path):
    d = tmp_path / "sc"; d.mkdir()
    assert not evidence_validator.validate_command_step(d).all_passed


def test_validate_command_no_stdout(evidence_validator, tmp_path):
    d = tmp_path / "sc"; d.mkdir()
    (d / "execution.json").write_text(json.dumps({"exit_code": 0, "command_type": "ssh"}))
    (d / "stderr.log").write_text("")
    (d / "execution.log").write_text("{}")
    r = evidence_validator.validate_command_step(d)
    c = next(c for c in r.checks if c.name == "stdout.log")
    assert not c.passed


def test_validate_command_no_audit(evidence_validator, tmp_path):
    d = tmp_path / "sc"; d.mkdir()
    (d / "execution.json").write_text(json.dumps({"exit_code": 0, "command_type": "ssh"}))
    (d / "stdout.log").write_text("ok")
    (d / "stderr.log").write_text("")
    r = evidence_validator.validate_command_step(d)
    c = next(c for c in r.checks if c.name == "execution.log")
    assert not c.passed


def test_validate_command_stderr_warn(evidence_validator, tmp_path):
    d = tmp_path / "sc"; d.mkdir()
    (d / "execution.json").write_text(json.dumps({"exit_code": 0, "command_type": "local"}))
    (d / "stdout.log").write_text("ok")
    (d / "stderr.log").write_text("Warning: deprecation")
    (d / "execution.log").write_text("{}")
    r = evidence_validator.validate_command_step(d)
    c = next(c for c in r.checks if c.name == "stderr.log")
    assert c.passed  # non-empty stderr is warning, not failure
