import importlib.util
import os
from unittest.mock import MagicMock

from core import base, fs


def _load_uninstall_script():
    path = os.path.join(base.mods_dir, "OpenDotaGuides Guides", "script_uninstall.py")
    spec = importlib.util.spec_from_file_location("odg_uninstall_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_open_dota_guides_uninstall_restores_utf8_content(monkeypatch, tmp_path):

    script = _load_uninstall_script()
    itembuilds = tmp_path / "itembuilds"
    backup = tmp_path / "backup"
    itembuilds.mkdir()
    backup.mkdir()
    (itembuilds / "default_antimage.txt").write_bytes(b"line1\nline2\nOpenDotaGuides \xe2\x80\x94 f\xc3\xb6n\n")

    monkeypatch.setattr(script, "dota_itembuilds_path", str(itembuilds))
    monkeypatch.setattr(script, "odg_bkup_path", str(backup))
    restore = MagicMock()
    monkeypatch.setattr(fs, "restore_directory", restore)

    script.main()

    restore.assert_called_once_with(str(itembuilds), str(backup))


def test_open_dota_guides_uninstall_skips_when_no_marker(monkeypatch, tmp_path):

    script = _load_uninstall_script()
    itembuilds = tmp_path / "itembuilds"
    backup = tmp_path / "backup"
    itembuilds.mkdir()
    backup.mkdir()
    (itembuilds / "default_antimage.txt").write_text("line1\nline2\nnot the mod\n", encoding="utf-8")

    monkeypatch.setattr(script, "dota_itembuilds_path", str(itembuilds))
    monkeypatch.setattr(script, "odg_bkup_path", str(backup))
    restore = MagicMock()
    monkeypatch.setattr(fs, "restore_directory", restore)

    script.main()

    restore.assert_not_called()


def test_open_dota_guides_uninstall_skips_without_backup(monkeypatch, tmp_path):

    script = _load_uninstall_script()
    itembuilds = tmp_path / "itembuilds"
    itembuilds.mkdir()
    monkeypatch.setattr(script, "odg_bkup_path", str(tmp_path / "missing_backup"))

    restore = MagicMock()
    monkeypatch.setattr(fs, "restore_directory", restore)

    script.main()

    restore.assert_not_called()
