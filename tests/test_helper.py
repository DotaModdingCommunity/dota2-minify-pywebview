from unittest.mock import MagicMock

import pytest

import helper


def _setup_compile_assets(tmp_path, monkeypatch):
    input_dir = tmp_path / "src"
    input_dir.mkdir()
    (input_dir / "test.png").write_bytes(b"png")

    rc_in = tmp_path / "rc_in"
    compile_out = tmp_path / "compiled"
    compile_out.mkdir()
    (compile_out / "out.vtex_c").write_bytes(b"v")

    monkeypatch.setattr(helper.constants, "minify_dota_compile_input_path", str(rc_in))
    monkeypatch.setattr(helper.constants, "minify_dota_compile_output_path", str(compile_out))
    monkeypatch.setattr(helper.constants, "minify_dota_tools_required_path", str(tmp_path / "tools"))

    monkeypatch.setattr(helper, "compile", MagicMock())
    monkeypatch.setattr(helper.output, "add_text", MagicMock())
    return input_dir


def test_compile_assets_empty_input_returns_early(tmp_path, monkeypatch):
    monkeypatch.setattr(helper.output, "add_text", MagicMock())

    helper.compile_assets(None)
    helper.compile_assets("")

    helper.output.add_text.assert_not_called()


def test_compile_assets_compiles_copies_and_cleans_up(tmp_path, monkeypatch):
    input_dir = _setup_compile_assets(tmp_path, monkeypatch)

    helper.compile_assets(str(input_dir))

    helper.compile.assert_called_once()
    default_out = tmp_path / "#Minify_compiled"
    assert (default_out / "out.vtex_c").exists()
    assert not list(input_dir.glob(".minify_ref_*.xml"))
    assert not (tmp_path / "rc_in").exists()
    assert not (tmp_path / "compiled").exists()


def test_compile_assets_cleanup_on_compile_failure(tmp_path, monkeypatch):
    input_dir = _setup_compile_assets(tmp_path, monkeypatch)
    monkeypatch.setattr(helper, "compile", MagicMock(side_effect=RuntimeError("boom")))

    with pytest.raises(RuntimeError):
        helper.compile_assets(str(input_dir))

    assert not list(input_dir.glob(".minify_ref_*.xml"))
    assert not (tmp_path / "rc_in").exists()
    assert not (tmp_path / "compiled").exists()


def test_compile_assets_explicit_output_path(tmp_path, monkeypatch):
    input_dir = _setup_compile_assets(tmp_path, monkeypatch)

    helper.compile_assets(str(input_dir), output_path=str(tmp_path / "custom_out"))

    assert (tmp_path / "custom_out" / "out.vtex_c").exists()


def test_compile_assets_pak_path_packs_vpk(tmp_path, monkeypatch):
    input_dir = _setup_compile_assets(tmp_path, monkeypatch)
    mock_new = MagicMock()
    mock_pak = MagicMock()
    mock_new.return_value = mock_pak
    monkeypatch.setattr(helper.vpk, "new", mock_new)

    pak_path = str(tmp_path / "out.vpk")
    helper.compile_assets(str(input_dir), pak_path=pak_path)

    mock_new.assert_called_once_with(str(tmp_path / "#Minify_compiled"))
    mock_pak.save.assert_called_once_with(pak_path)
