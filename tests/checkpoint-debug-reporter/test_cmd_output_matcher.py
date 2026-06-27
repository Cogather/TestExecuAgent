"""Unit tests for cmd_output_matcher.py."""

import json


def test_contains_match(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.contains("hello world", "world")
    assert ok


def test_contains_nomatch(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.contains("hello", "xyz")
    assert not ok


def test_contains_empty_stdout(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.contains("", "x")
    assert not ok


def test_contains_empty_expected(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.contains("hello", "")
    assert ok


def test_regex_match(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.regex("Version: 2.3.1", r"Version: \d+\.\d+\.\d+")
    assert ok


def test_regex_multiline(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.regex("a\nV: 3.0\nb", r"V: \d+\.\d+")
    assert ok


def test_regex_nomatch(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.regex("hello", r"\d{10,}")
    assert not ok


def test_regex_invalid(cmd_output_matcher):
    ok, detail = cmd_output_matcher.OutputMatcher.regex("x", r"[bad")
    assert not ok
    assert "invalid" in detail


def test_json_path_simple(cmd_output_matcher):
    stdout = json.dumps({"status": "ok"})
    ok, detail = cmd_output_matcher.OutputMatcher.json_path(stdout, "status")
    assert ok and "ok" in detail


def test_json_path_nested(cmd_output_matcher):
    stdout = json.dumps({"data": {"result": "ok"}})
    ok, _ = cmd_output_matcher.OutputMatcher.json_path(stdout, "data.result")
    assert ok


def test_json_path_array(cmd_output_matcher):
    stdout = json.dumps({"items": [{"name": "a"}, {"name": "b"}]})
    ok, detail = cmd_output_matcher.OutputMatcher.json_path(stdout, "items[1].name")
    assert ok and "b" in detail


def test_json_path_not_found(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.json_path(json.dumps({"a": 1}), "b")
    assert not ok


def test_json_path_bad_json(cmd_output_matcher):
    ok, detail = cmd_output_matcher.OutputMatcher.json_path("nope", "k")
    assert not ok and "not valid JSON" in detail


def test_json_path_oob(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.json_path(json.dumps([1]), "[5]")
    assert not ok


def test_equals_match(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.equals("hello\n", "hello")
    assert ok


def test_equals_diff(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.equals("a", "b")
    assert not ok


def test_equals_whitespace(cmd_output_matcher):
    ok, _ = cmd_output_matcher.OutputMatcher.equals("  hi  ", "hi")
    assert ok
