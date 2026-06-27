"""Unit tests for batch_archiver.py."""


def test_collect_empty_dir(batch_archiver, tmp_path):
    result = batch_archiver.collect_artifacts(tmp_path)
    assert result["step_dirs"] == []


def test_collect_with_steps(batch_archiver, tmp_case_with_steps):
    result = batch_archiver.collect_artifacts(tmp_case_with_steps)
    assert len(result["step_dirs"]) == 3
    assert result["total_size_bytes"] > 0


def test_collect_reports(batch_archiver, tmp_path):
    (tmp_path / "report.md").write_text("# R")
    (tmp_path / "result.json").write_text("{}")
    result = batch_archiver.collect_artifacts(tmp_path)
    assert len(result["report_files"]) == 2


def test_collect_nonexistent(batch_archiver, tmp_path):
    result = batch_archiver.collect_artifacts(tmp_path / "nope")
    assert "error" in result


def test_collect_other(batch_archiver, tmp_path):
    (tmp_path / "script.py").write_text("x")
    assert len(batch_archiver.collect_artifacts(tmp_path)["other_files"]) == 1


def test_tarball(batch_archiver, tmp_path):
    (tmp_path / "f.txt").write_text("hi")
    output = tmp_path / "a.tar.gz"
    result = batch_archiver.create_tarball(tmp_path, output)
    assert result.exists() and result.stat().st_size > 0


def test_zip(batch_archiver, tmp_path):
    (tmp_path / "f.txt").write_text("hi")
    output = tmp_path / "a.zip"
    result = batch_archiver.create_zip(tmp_path, output)
    assert result.exists() and result.stat().st_size > 0


def test_cleanup_safe(batch_archiver, tmp_path):
    (tmp_path / "reports").mkdir()
    rpt = tmp_path / "reports" / "r.md"
    rpt.write_text("x")
    (tmp_path / "tmp.txt").write_text("x")
    batch_archiver.cleanup_workspace(tmp_path, mode="safe")
    assert rpt.exists()
    assert not (tmp_path / "tmp.txt").exists()


def test_cleanup_keeps_report_md(batch_archiver, tmp_path):
    (tmp_path / "report.md").write_text("r")
    (tmp_path / "junk.tmp").write_text("x")
    batch_archiver.cleanup_workspace(tmp_path, mode="safe")
    assert (tmp_path / "report.md").exists()


def test_cleanup_aggressive(batch_archiver, tmp_path):
    (tmp_path / "a.txt").write_text("a")
    batch_archiver.cleanup_workspace(tmp_path, mode="aggressive")
    assert len([f for f in tmp_path.rglob("*") if f.is_file()]) == 0


def test_cleanup_empty(batch_archiver, tmp_path):
    assert batch_archiver.cleanup_workspace(tmp_path, mode="safe") == []
