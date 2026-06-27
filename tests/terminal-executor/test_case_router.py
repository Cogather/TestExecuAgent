"""Unit tests for case_router.py."""


def test_detect_web_default(case_router):
    steps = [{"step_order": "1", "command_type": "playwright"}]
    assert case_router.detect_case_type(steps) == case_router.CaseType.WEB


def test_detect_mml(case_router):
    steps = [{"step_order": "1", "command_type": "ssh"}]
    assert case_router.detect_case_type(steps) == case_router.CaseType.MML


def test_detect_api(case_router):
    steps = [{"step_order": "1", "command_type": "local"}]
    assert case_router.detect_case_type(steps) == case_router.CaseType.API


def test_detect_hybrid(case_router):
    steps = [
        {"step_order": "1", "command_type": "playwright"},
        {"step_order": "2", "command_type": "ssh"},
    ]
    assert case_router.detect_case_type(steps) == case_router.CaseType.HYBRID


def test_detect_explicit_override(case_router):
    steps = [{"step_order": "1", "command_type": "ssh"}]
    assert case_router.detect_case_type(steps, explicit_type="web") == case_router.CaseType.WEB


def test_detect_empty_defaults_web(case_router):
    assert case_router.detect_case_type([]) == case_router.CaseType.WEB


def test_detect_type_field_fallback(case_router):
    steps = [{"step_order": "1", "type": "ssh"}]
    assert case_router.detect_case_type(steps) == case_router.CaseType.MML


def test_web_stages_exclude_terminal(case_router):
    stages = case_router.get_pipeline_stages(case_router.CaseType.WEB)
    assert "terminal-executor" not in stages
    assert "fix-scripts" in stages


def test_mml_stages_include_terminal(case_router):
    stages = case_router.get_pipeline_stages(case_router.CaseType.MML)
    assert "terminal-executor" in stages
    assert "record-scripts" not in stages


def test_api_stages(case_router):
    assert "terminal-executor" in case_router.get_pipeline_stages(case_router.CaseType.API)


def test_hybrid_stages(case_router):
    stages = case_router.get_pipeline_stages(case_router.CaseType.HYBRID)
    assert "terminal-executor" in stages
    assert "fix-scripts" in stages


def test_validate_ssh_valid_password(case_router):
    config = {"host": "10.0.0.1", "username": "admin", "auth_method": "password", "password": "x"}
    assert case_router.validate_ssh_config(config) == []


def test_validate_ssh_valid_key(case_router):
    config = {"host": "10.0.0.1", "username": "admin", "auth_method": "key", "key_path": "/id_rsa"}
    assert case_router.validate_ssh_config(config) == []


def test_validate_ssh_missing_host(case_router):
    config = {"username": "admin", "auth_method": "password", "password": "x"}
    assert "host" in case_router.validate_ssh_config(config)


def test_validate_ssh_missing_password(case_router):
    config = {"host": "x", "username": "admin", "auth_method": "password"}
    assert any("password" in i for i in case_router.validate_ssh_config(config))


def test_validate_ssh_missing_key(case_router):
    config = {"host": "x", "username": "admin", "auth_method": "key"}
    assert any("key_path" in i for i in case_router.validate_ssh_config(config))


def test_validate_ssh_none(case_router):
    issues = case_router.validate_ssh_config(None)
    assert any("missing" in i for i in issues)
