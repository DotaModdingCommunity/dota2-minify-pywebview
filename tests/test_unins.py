from unittest.mock import MagicMock

import helper
from core import base, constants, steam
from patch import unins, vpk_utils


def _setup_uninstall(tmp_path, monkeypatch, outputs=None):
    out_dir = tmp_path / "dota_dutch"
    out_dir.mkdir()
    minify_pak = out_dir / "pak01_dir.vpk"
    minify_pak.write_bytes(b"m")
    foreign_pak = out_dir / "pak02_dir.vpk"
    foreign_pak.write_bytes(b"f")

    outputs = outputs or [str(out_dir)]
    monkeypatch.setattr(constants, "minify_dota_possible_language_output_paths", outputs)
    monkeypatch.setattr(vpk_utils, "is_minify_pak", lambda p: str(p).endswith("pak01_dir.vpk"))
    monkeypatch.setattr(steam, "remove_minify_lang", MagicMock())
    monkeypatch.setattr(helper, "bulk_exec_script", MagicMock())
    monkeypatch.setattr(unins.output, "clean", MagicMock())
    monkeypatch.setattr(unins.output, "add_text", MagicMock())
    monkeypatch.setattr(base, "HEADLESS", True)
    return out_dir, minify_pak, foreign_pak


def test_uninstall_removes_only_minify_paks(tmp_path, monkeypatch):
    out_dir, minify_pak, foreign_pak = _setup_uninstall(tmp_path, monkeypatch)

    unins._uninstall(progress=False)

    assert not minify_pak.exists()
    assert foreign_pak.exists()
    steam.remove_minify_lang.assert_called_once()
    helper.bulk_exec_script.assert_called_once_with("uninstall")


def test_uninstall_skips_non_vpk_files(tmp_path, monkeypatch):
    out_dir, _, _ = _setup_uninstall(tmp_path, monkeypatch)
    readme = out_dir / "readme.txt"
    readme.write_bytes(b"hi")

    unins._uninstall(progress=False)

    assert readme.exists()
