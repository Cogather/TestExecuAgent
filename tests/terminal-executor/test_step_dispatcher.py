"""Unit tests for step_dispatcher.py."""


def test_classify_playwright(step_dispatcher):
    assert step_dispatcher.classify_step({"command_type": "playwright"}) == step_dispatcher.StepType.PLAYWRIGHT


def test_classify_shell(step_dispatcher):
    assert step_dispatcher.classify_step({"command_type": "shell"}) == step_dispatcher.StepType.LOCAL


def test_classify_ssh(step_dispatcher):
    assert step_dispatcher.classify_step({"command_type": "ssh"}) == step_dispatcher.StepType.SSH


def test_classify_default(step_dispatcher):
    assert step_dispatcher.classify_step({}) == step_dispatcher.StepType.PLAYWRIGHT


def test_classify_mml(step_dispatcher):
    assert step_dispatcher.classify_step({"command_type": "mml"}) == step_dispatcher.StepType.SSH


def test_group_steps(step_dispatcher):
    steps = [
        {"step_order": "1", "command_type": "playwright"},
        {"step_order": "2", "command_type": "ssh"},
        {"step_order": "3", "command_type": "local"},
        {"step_order": "4", "command_type": "playwright"},
    ]
    groups = step_dispatcher.group_steps_by_type(steps)
    assert len(groups[step_dispatcher.StepType.PLAYWRIGHT]) == 2
    assert len(groups[step_dispatcher.StepType.SSH]) == 1
    assert len(groups[step_dispatcher.StepType.LOCAL]) == 1


def test_group_empty(step_dispatcher):
    groups = step_dispatcher.group_steps_by_type([])
    assert all(len(v) == 0 for v in groups.values())


def test_interleave_preserves_order(step_dispatcher):
    steps = [
        {"step_order": "2", "command_type": "ssh"},
        {"step_order": "1", "command_type": "playwright"},
        {"step_order": "3", "command_type": "local"},
    ]
    tagged = step_dispatcher.interleave_steps(steps)
    assert [t[0] for t in tagged] == [1, 2, 3]
    assert tagged[0][1] == step_dispatcher.StepType.PLAYWRIGHT


def test_build_plan_web(step_dispatcher):
    steps = [{"step_order": "1", "command_type": "playwright"}] * 2
    plan = step_dispatcher.build_execution_plan(steps, "CASE")
    assert plan["summary"]["is_hybrid"] is False
    assert plan["summary"]["playwright_steps"] == 2


def test_build_plan_hybrid(step_dispatcher):
    steps = [
        {"step_order": "1", "command_type": "playwright"},
        {"step_order": "2", "command_type": "ssh"},
        {"step_order": "3", "command_type": "playwright"},
        {"step_order": "4", "command_type": "ssh"},
    ]
    plan = step_dispatcher.build_execution_plan(steps, "CASE")
    assert plan["summary"]["is_hybrid"] is True
    assert plan["summary"]["engine_switches"] == 3


def test_build_plan_sequence(step_dispatcher):
    steps = [{"step_order": "1", "command_type": "ssh", "command": "mml show"}]
    plan = step_dispatcher.build_execution_plan(steps, "CASE")
    seq = plan["step_sequence"][0]
    assert seq["engine"] == "terminal-executor"
    assert seq["command"] == "mml show"


def test_build_plan_transitions(step_dispatcher):
    steps = [
        {"step_order": "1", "command_type": "playwright"},
        {"step_order": "2", "command_type": "local"},
    ]
    plan = step_dispatcher.build_execution_plan(steps, "T")
    t = plan["engine_transitions"][0]
    assert t["from"] == "playwright"
    assert t["to"] == "local"
