from unittest.mock import MagicMock

from patch import blacklist


def _make_out(tmp_path, monkeypatch, settings=None):
    blank_dir = tmp_path / "blank"
    blank_dir.mkdir()
    (blank_dir / "blank.png").write_bytes(b"blank")

    monkeypatch.setattr(blacklist.base, "blank_files_dir", str(blank_dir))
    monkeypatch.setattr(blacklist.constants, "minify_dota_compile_output_path", str(tmp_path / "out"))
    monkeypatch.setattr(blacklist.config, "get_mod_config", lambda name: settings or {})


def test_process_copies_blank_files_and_applies_exclusions(tmp_path, monkeypatch):
    blacklist_txt = tmp_path / "blacklist.txt"
    blacklist_txt.write_text("# comment\npanorama/images/a.png\npanorama/images/b.png\n--panorama/images/b.png\n")

    _make_out(tmp_path, monkeypatch)

    blacklist.process(str(blacklist_txt), "TestMod", ["png", "xml"])

    assert (tmp_path / "out" / "panorama" / "images" / "a.png").exists()
    assert not (tmp_path / "out" / "panorama" / "images" / "b.png").exists()


def test_process_logs_invalid_extension(tmp_path, monkeypatch):
    blacklist_txt = tmp_path / "blacklist.txt"
    blacklist_txt.write_text("bad.txt\n")

    warnings = []
    monkeypatch.setattr(blacklist.log, "write_warning", lambda msg: warnings.append(msg))
    _make_out(tmp_path, monkeypatch)

    blacklist.process(str(blacklist_txt), "TestMod", ["png", "xml"])

    assert any("Invalid Extension" in w and "bad.txt" in w for w in warnings)


def test_process_skips_comments_and_blank_lines(tmp_path, monkeypatch):
    blacklist_txt = tmp_path / "blacklist.txt"
    blacklist_txt.write_text("# comment\n\n  \n")

    monkeypatch.setattr(blacklist.log, "write_warning", MagicMock())
    _make_out(tmp_path, monkeypatch)

    blacklist.process(str(blacklist_txt), "TestMod", ["png"])

    blacklist.log.write_warning.assert_not_called()


def test_process_gates_blocks_by_key(tmp_path, monkeypatch):
    blacklist_txt = tmp_path / "blacklist.txt"
    blacklist_txt.write_text("# @key:keep\npanorama/images/keep.png\n# @key:drop\npanorama/images/drop.png\n")

    _make_out(tmp_path, monkeypatch, settings={"keep": True, "drop": False})

    blacklist.process(str(blacklist_txt), "TestMod", ["png"])

    assert (tmp_path / "out" / "panorama" / "images" / "keep.png").exists()
    assert not (tmp_path / "out" / "panorama" / "images" / "drop.png").exists()


def test_process_missing_key_defaults_to_enabled(tmp_path, monkeypatch):
    blacklist_txt = tmp_path / "blacklist.txt"
    blacklist_txt.write_text("# @key:unknown\npanorama/images/a.png\n")

    _make_out(tmp_path, monkeypatch, settings={})

    blacklist.process(str(blacklist_txt), "TestMod", ["png"])

    assert (tmp_path / "out" / "panorama" / "images" / "a.png").exists()


def test_process_unkeyed_block_always_applied(tmp_path, monkeypatch):
    blacklist_txt = tmp_path / "blacklist.txt"
    blacklist_txt.write_text("panorama/images/always.png\n# @key:off\npanorama/images/drop.png\n")

    _make_out(tmp_path, monkeypatch, settings={"off": False})

    blacklist.process(str(blacklist_txt), "TestMod", ["png"])

    assert (tmp_path / "out" / "panorama" / "images" / "always.png").exists()
    assert not (tmp_path / "out" / "panorama" / "images" / "drop.png").exists()


def test_process_dir_runs_rg_and_returns_lines(monkeypatch):
    mock_run = MagicMock(return_value=MagicMock(stdout="a\nb\n"))
    monkeypatch.setattr(blacklist.subprocess, "run", mock_run)
    monkeypatch.setattr(blacklist.constants, "rg_exec_path", "rg")
    monkeypatch.setattr(blacklist.base, "bin_dir", "/fake/bin")

    result = blacklist.process_dir(1, ">>panorama", "TestMod")

    assert result == ["a", "b"]
    assert mock_run.call_count == 1


def test_process_dir_warns_when_empty(monkeypatch):
    monkeypatch.setattr(blacklist.subprocess, "run", MagicMock(return_value=MagicMock(stdout="")))
    monkeypatch.setattr(blacklist.constants, "rg_exec_path", "rg")
    monkeypatch.setattr(blacklist.base, "bin_dir", "/fake/bin")
    warnings = []
    monkeypatch.setattr(blacklist.log, "write_warning", lambda msg: warnings.append(msg))

    result = blacklist.process_dir(2, ">>panorama", "TestMod")

    assert result == []
    assert any("Directory Not Found" in w for w in warnings)
