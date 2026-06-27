"""Unit tests for cmd_sanitizer.py."""

import pytest


def get_funcs(cmd_sanitizer):
    return (
        cmd_sanitizer.extract_basename,
        cmd_sanitizer.check_whitelist,
        cmd_sanitizer.check_blacklist,
        cmd_sanitizer.redact_sensitive,
    )


# --- extract_basename ---

@pytest.mark.parametrize("command,expected", [
    ("python script.py", "python"),
    ("ls -la", "ls"),
    ("/usr/bin/python3 script.py", "python3"),
    ("echo hello | grep world", "echo"),
    ("cat file > out.txt", "cat"),
    ("  mkdir -p /tmp/foo  ", "mkdir"),
    ("ssh -o StrictHostKeyChecking=no host cmd", "ssh"),
])
def test_extract_basename_extracts_first_word(cmd_sanitizer, command, expected):
    assert cmd_sanitizer.extract_basename(command) == expected


def test_extract_basename_empty_string(cmd_sanitizer):
    assert cmd_sanitizer.extract_basename("") == ""
    assert cmd_sanitizer.extract_basename("   ") == ""


# --- check_whitelist ---

def test_check_whitelist_passes(cmd_sanitizer):
    config = {"local": ["python", "ls", "echo"]}
    ok, reason = cmd_sanitizer.check_whitelist("python test.py", config, "local")
    assert ok


def test_check_whitelist_fails(cmd_sanitizer):
    config = {"local": ["python", "ls"]}
    ok, reason = cmd_sanitizer.check_whitelist("rm -rf /tmp", config, "local")
    assert not ok
    assert "rm" in reason


def test_check_whitelist_empty(cmd_sanitizer):
    config = {"local": ["python"]}
    ok, reason = cmd_sanitizer.check_whitelist("", config, "local")
    assert not ok


def test_check_whitelist_type_separation(cmd_sanitizer):
    config = {"local": ["python"], "ssh": ["mml"]}
    ok1, _ = cmd_sanitizer.check_whitelist("python test.py", config, "local")
    ok2, _ = cmd_sanitizer.check_whitelist("mml show version", config, "ssh")
    assert ok1 and ok2


def test_check_whitelist_ssh_not_local(cmd_sanitizer):
    config = {"local": ["python"], "ssh": ["mml"]}
    ok, _ = cmd_sanitizer.check_whitelist("mml show version", config, "local")
    assert not ok


# --- check_blacklist ---

def test_check_blacklist_blocks_rm_rf(cmd_sanitizer):
    ok, reason = cmd_sanitizer.check_blacklist("rm -rf /", ["rm -rf /", "shutdown"])
    assert not ok


def test_check_blacklist_blocks_shutdown(cmd_sanitizer):
    ok, reason = cmd_sanitizer.check_blacklist("shutdown -h now", ["rm -rf /", "shutdown"])
    assert not ok


def test_check_blacklist_passes_safe(cmd_sanitizer):
    ok, reason = cmd_sanitizer.check_blacklist("ls -la", ["rm -rf /", "shutdown"])
    assert ok


def test_check_blacklist_empty(cmd_sanitizer):
    ok, reason = cmd_sanitizer.check_blacklist("rm -rf /", [])
    assert ok


def test_check_blacklist_fork_bomb(cmd_sanitizer):
    ok, reason = cmd_sanitizer.check_blacklist(":(){ :|:& };:", [":(){ :|:& };:"])
    assert not ok


# --- redact_sensitive ---

def test_redact_password(cmd_sanitizer):
    result = cmd_sanitizer.redact_sensitive("ENV password=secret123 --flag")
    assert "secret123" not in result


def test_redact_api_key(cmd_sanitizer):
    result = cmd_sanitizer.redact_sensitive('export api_key=sk-abc123xyz')
    assert "sk-abc123xyz" not in result


def test_redact_jwt(cmd_sanitizer):
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    result = cmd_sanitizer.redact_sensitive(f"Authorization: Bearer {jwt}")
    assert jwt not in result


def test_redact_plaintext(cmd_sanitizer):
    result = cmd_sanitizer.redact_sensitive("python test.py --verbose")
    assert result == "python test.py --verbose"


def test_redact_private_key(cmd_sanitizer):
    key = "-----BEGIN RSA PRIVATE KEY-----\nabc123\n-----END RSA PRIVATE KEY-----"
    result = cmd_sanitizer.redact_sensitive(f"KEY={key}")
    assert "BEGIN RSA PRIVATE KEY" not in result
    assert "REDACTED_KEY" in result
