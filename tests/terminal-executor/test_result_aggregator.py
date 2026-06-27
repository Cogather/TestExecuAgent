"""Unit tests for result_aggregator.py."""


def test_collect_step_results(result_aggregator, tmp_case_with_steps):
    results = result_aggregator.collect_step_results(tmp_case_with_steps)
    assert len(results) == 3
    assert results[0]["exit_code"] == 0
    assert results[1]["exit_code"] == 1
    assert results[0]["status"] == "passed"


def test_collect_missing_execution_json(result_aggregator, tmp_path):
    step_dir = tmp_path / "step_empty"
    step_dir.mkdir()
    results = result_aggregator.collect_step_results(tmp_path)
    assert results[0]["status"] == "missing"


def test_collect_corrupted_json(result_aggregator, tmp_path):
    step_dir = tmp_path / "step_1"
    step_dir.mkdir()
    (step_dir / "execution.json").write_text("{bad")
    results = result_aggregator.collect_step_results(tmp_path)
    assert results[0]["status"] == "corrupted"


def test_collect_empty_dir(result_aggregator, tmp_path):
    assert result_aggregator.collect_step_results(tmp_path) == []


def test_summarize_all_passed(result_aggregator):
    results = [
        {"step": "step_1", "exit_code": 0, "status": "passed"},
        {"step": "step_2", "exit_code": 0, "status": "passed"},
    ]
    summary = result_aggregator.summarize(results)
    assert summary["overall"] == "passed"


def test_summarize_mixed(result_aggregator):
    results = [
        {"step": "step_1", "exit_code": 0, "status": "passed"},
        {"step": "step_2", "exit_code": 1, "status": "failed"},
    ]
    assert result_aggregator.summarize(results)["overall"] == "failed"


def test_summarize_corrupted(result_aggregator):
    results = [
        {"step": "step_1", "exit_code": 0, "status": "passed"},
        {"step": "step_2", "status": "corrupted"},
    ]
    assert result_aggregator.summarize(results)["corrupted"] == 1


def test_summarize_missing(result_aggregator):
    results = [
        {"step": "step_1", "exit_code": 0, "status": "passed"},
        {"step": "step_2", "status": "missing"},
    ]
    assert result_aggregator.summarize(results)["overall"] == "incomplete"


def test_summarize_timeouts(result_aggregator):
    results = [
        {"step": "step_1", "exit_code": 124, "status": "failed", "timed_out": True},
        {"step": "step_2", "exit_code": 0, "status": "passed", "timed_out": False},
    ]
    assert result_aggregator.summarize(results)["timed_out"] == 1


def test_summarize_command_type(result_aggregator):
    results = [
        {"step": "step_1", "exit_code": 0, "command_type": "ssh",
         "status": "passed", "duration_ms": 500, "error_summary": ""},
    ]
    detail = result_aggregator.summarize(results)["step_details"][0]
    assert detail["command_type"] == "ssh"
