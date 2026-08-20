from unittest.mock import patch

import pytest
from core import log


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    monkeypatch.setattr(log.base, "log_crashlog", str(logs_dir / "crashlog.txt"))
    monkeypatch.setattr(log.base, "log_warnings", str(logs_dir / "warnings.txt"))
    monkeypatch.setattr(log.base, "logs_dir", str(logs_dir))
    return logs_dir


def test_write_crashlog(mock_env):
    log.write_crashlog(header="Test", handled=True)
    assert "Test" in open(log.base.log_crashlog).read()


def test_write_warning(mock_env):
    log.write_warning(header="Test")
    assert "Test" in open(log.base.log_warnings).read()


def test_write_warning_show_traceback_false_keeps_file_full_console_short(mock_env):
    try:
        raise ValueError("boom")
    except ValueError:
        with patch("core.output.add_text") as mock_add:
            log.write_warning(header="Test", show_traceback=False)

    with open(log.base.log_warnings) as file:
        content = file.read()
    assert "Test" in content
    assert "Traceback (most recent call last):" in content
    assert "ValueError: boom" in content
    mock_add.assert_called_once_with("Test", msg_type="warning")


def test_write_warning_show_traceback_false_no_active_exception(mock_env):
    with patch("core.output.add_text") as mock_add:
        log.write_warning(header="Test", show_traceback=False)

    mock_add.assert_called_once_with("Test", msg_type="warning")


def test_create_debug_zip(mock_env, tmp_path, monkeypatch):
    (mock_env / "test.log").write_text("data")
    monkeypatch.chdir(tmp_path)
    with patch("core.fs.open_thing") as mock_open:
        log.create_debug_zip()
        mock_open.assert_called_once_with(".")
    assert len(list(tmp_path.glob("*.zip"))) == 1
