"""Unit tests for run_command_with_capture.py."""

from unittest.mock import MagicMock

import pytest


def test_utc_now(run_command):
    result = run_command.utc_now()
    assert "T" in result


@pytest.mark.parametrize("step_input,expected", [
    ("1", "step_1"),
    (" 3 ", "step_3"),
    ("10", "step_10"),
    ("first", "step_first"),
    ("my-step", "step_my-step"),
    ("a/b", "step_a_b"),
])
def test_step_dir_name(run_command, step_input, expected):
    assert run_command.step_dir_name(step_input) == expected


def test_step_dir_name_empty(run_command):
    assert run_command.step_dir_name("   ") == "step_unknown"


def test_build_command_local(run_command):
    args = MagicMock()
    args.command_type = "local"
    args.command = "python test.py"
    args.ssh_port = None
    cmd = run_command.build_command(args)
    assert cmd == ["bash", "-c", "python test.py"]


def test_build_command_ssh(run_command):
    args = MagicMock()
    args.command_type = "ssh"
    args.command = "mml show version"
    args.ssh_port = 2222
    args.ssh_host = "10.0.0.1"
    args.ssh_user = "admin"
    cmd = run_command.build_command(args)
    assert "ssh" in cmd
    assert "-p" in cmd
    assert "2222" in cmd
    assert "admin@10.0.0.1" in cmd


def test_build_command_ssh_no_port(run_command):
    args = MagicMock()
    args.command_type = "ssh"
    args.command = "show status"
    args.ssh_port = None
    args.ssh_host = "192.168.1.1"
    args.ssh_user = "root"
    cmd = run_command.build_command(args)
    assert "-p" not in cmd
    assert "root@192.168.1.1" in cmd


def test_build_command_unknown_raises(run_command):
    args = MagicMock()
    args.command_type = "invalid"
    with pytest.raises(ValueError, match="Unknown command_type"):
        run_command.build_command(args)


def test_redact_sensitive_password(run_command):
    result = run_command.redact_sensitive('token=abcdef123456')
    assert 'abcdef123456' not in result
    assert '***=***' in result


def test_redact_sensitive_jwt(run_command):
    result = run_command.redact_sensitive('Bearer eyJhbGci.eyJzdWIi.dG9rZW4')
    assert 'eyJhbGci' not in result


def test_redact_sensitive_plaintext(run_command):
    assert run_command.redact_sensitive("ls -la /tmp") == "ls -la /tmp"


def test_redact_sensitive_private_key(run_command):
    result = run_command.redact_sensitive('-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----')
    assert 'PRIVATE KEY' not in result
    assert 'REDACTED_KEY' in result


def test_redact_sensitive_api_secret(run_command):
    result = run_command.redact_sensitive("api_secret=supersecretvalue")
    assert "supersecretvalue" not in result
