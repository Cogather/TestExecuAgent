"""Unit tests for ssh_precheck.py."""

import subprocess
from unittest.mock import MagicMock, patch


def test_probe_ssh_reachable(ssh_precheck):
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "ok\n"
    proc.stderr = ""
    with patch("subprocess.run", return_value=proc):
        result = ssh_precheck.probe_ssh("10.0.0.1", 22, "admin")
    assert result["reachable"] is True
    assert result["exit_code"] == 0


def test_probe_ssh_unreachable(ssh_precheck):
    proc = MagicMock()
    proc.returncode = 255
    proc.stdout = ""
    proc.stderr = "Connection refused"
    with patch("subprocess.run", return_value=proc):
        result = ssh_precheck.probe_ssh("10.0.0.2", 22, "admin")
    assert result["reachable"] is False


def test_probe_ssh_timeout(ssh_precheck):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ssh", 10)):
        result = ssh_precheck.probe_ssh("10.0.0.3", 22, "admin")
    assert result["reachable"] is False
    assert result["exit_code"] == 124


def test_probe_ssh_not_found(ssh_precheck):
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = ssh_precheck.probe_ssh("10.0.0.4", 22, "admin")
    assert result["exit_code"] == 127


def test_probe_ssh_generic_error(ssh_precheck):
    with patch("subprocess.run", side_effect=RuntimeError("boom")):
        result = ssh_precheck.probe_ssh("10.0.0.5", 22, "admin")
    assert result["exit_code"] == -1


def test_probe_ssh_custom_port(ssh_precheck):
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "ok\n"
    proc.stderr = ""
    with patch("subprocess.run", return_value=proc):
        result = ssh_precheck.probe_ssh("10.0.0.6", 2222, "root", timeout=3)
    assert result["port"] == 2222


def test_probe_ssh_stderr_truncated(ssh_precheck):
    proc = MagicMock()
    proc.returncode = 255
    proc.stdout = ""
    proc.stderr = "X" * 500
    with patch("subprocess.run", return_value=proc):
        result = ssh_precheck.probe_ssh("10.0.0.7", 22, "admin")
    assert len(result["stderr_abridged"]) <= 200


def test_probe_ssh_no_ok_in_stdout(ssh_precheck):
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "welcome\n"
    proc.stderr = ""
    with patch("subprocess.run", return_value=proc):
        result = ssh_precheck.probe_ssh("10.0.0.8", 22, "admin")
    assert result["reachable"] is False
