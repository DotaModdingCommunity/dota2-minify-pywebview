import json
import os

from unittest.mock import patch


def _make_always_on_mod(tmp_path, name="#base"):
    mod_dir = tmp_path / name
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "manifest.json").write_text(json.dumps({"always": True}))
    return mod_dir


def _patch_mods_listdir(monkeypatch, mods_dir):
    fake = os.listdir

    def passthrough(path):
        if str(path) == str(mods_dir):
            return [e.name for e in os.scandir(path)]
        return fake(path)

    monkeypatch.setattr(os, "listdir", passthrough)


def test_read_states_from_disk_corrupt_file_backed_up(tmp_path):
    from core import base, mods_shared

    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write("{ this is not valid json !!!")

    with (
        patch.object(base, "mods_config_dir", cfg),
        patch("core.mods_shared.shutil.copy2") as mock_copy,
        patch("core.mods_shared.log.write_warning") as mock_warn,
    ):
        result = mods_shared._read_states_from_disk()

    assert result == {}
    mock_copy.assert_called_once_with(cfg, cfg + ".corrupt")
    mock_warn.assert_called_once_with(
        f"Failed to read mod states; corrupt file backed up to {cfg}.corrupt", show_traceback=False
    )


def test_read_states_from_disk_corrupt_backup_failure_short_message(tmp_path):
    from core import base, mods_shared

    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write("{ this is not valid json !!!")

    with (
        patch.object(base, "mods_config_dir", cfg),
        patch("core.mods_shared.shutil.copy2", side_effect=OSError),
        patch("core.mods_shared.log.write_warning") as mock_warn,
    ):
        result = mods_shared._read_states_from_disk()

    assert result == {}
    mock_warn.assert_called_once_with("Failed to read mod states", show_traceback=False)


def test_read_states_from_disk_valid(tmp_path):
    from core import base, mods_shared

    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write('{"My Mod": true}')

    with patch.object(base, "mods_config_dir", cfg), patch("core.mods_shared.shutil.copy2") as mock_copy:
        result = mods_shared._read_states_from_disk()

    assert result == {"My Mod": True}
    mock_copy.assert_not_called()


def test_get_state_returns_true_for_always_on_mod(tmp_path, monkeypatch):
    from core import base, mods_shared

    _make_always_on_mod(tmp_path)
    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write('{"#base": false}')

    _patch_mods_listdir(monkeypatch, str(tmp_path))
    monkeypatch.setattr(mods_shared, "_always_on_mods", None)
    monkeypatch.setattr(mods_shared, "_state_cache", None)
    with patch.object(base, "mods_dir", str(tmp_path)), patch.object(base, "mods_config_dir", cfg):
        assert mods_shared.get_state("#base") is True


def test_set_state_always_on_mod_persists_true(tmp_path, monkeypatch):
    from core import base, mods_shared

    _make_always_on_mod(tmp_path)
    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write('{"#base": false}')

    _patch_mods_listdir(monkeypatch, str(tmp_path))
    monkeypatch.setattr(mods_shared, "_always_on_mods", None)
    monkeypatch.setattr(mods_shared, "_state_cache", None)
    with patch.object(base, "mods_dir", str(tmp_path)), patch.object(base, "mods_config_dir", cfg):
        mods_shared.set_state("#base", False)

    with open(cfg) as file:
        data = json.load(file)
    assert data == {"#base": True}


def test_write_states_to_disk_coerces_stale_false_to_true(tmp_path, monkeypatch):
    from core import base, mods_shared

    _make_always_on_mod(tmp_path)
    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write('{"#base": false, "Mod A": true}')

    _patch_mods_listdir(monkeypatch, str(tmp_path))
    monkeypatch.setattr(mods_shared, "_always_on_mods", None)
    monkeypatch.setattr(mods_shared, "_state_cache", None)
    with patch.object(base, "mods_dir", str(tmp_path)), patch.object(base, "mods_config_dir", cfg):
        mods_shared.set_state("Mod A", True)

    with open(cfg) as file:
        data = json.load(file)
    assert data == {"#base": True, "Mod A": True}


def test_read_states_from_disk_filters_false_entries(tmp_path):
    from core import base, mods_shared

    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write('{"Mod A": true, "Mod B": false}')

    with patch.object(base, "mods_config_dir", cfg):
        result = mods_shared._read_states_from_disk()

    assert result == {"Mod A": True}


def test_set_state_false_removes_mod_from_disk(tmp_path, monkeypatch):
    from core import base, mods_shared

    _make_always_on_mod(tmp_path)
    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write('{"#base": true, "Mod B": true}')

    _patch_mods_listdir(monkeypatch, str(tmp_path))
    monkeypatch.setattr(mods_shared, "_always_on_mods", None)
    monkeypatch.setattr(mods_shared, "_state_cache", None)
    with patch.object(base, "mods_dir", str(tmp_path)), patch.object(base, "mods_config_dir", cfg):
        mods_shared.set_state("Mod B", False)
        assert mods_shared.get_state("Mod B") is False
        assert mods_shared.get_state("#base") is True

    with open(cfg) as file:
        data = json.load(file)
    assert data == {"#base": True}


def test_set_state_batch_removes_disabled_mods_from_disk(tmp_path, monkeypatch):
    from core import base, mods_shared

    _make_always_on_mod(tmp_path)
    cfg = str(tmp_path / "mods.json")
    with open(cfg, "w") as file:
        file.write('{"#base": true, "Mod B": true}')

    _patch_mods_listdir(monkeypatch, str(tmp_path))
    monkeypatch.setattr(mods_shared, "_always_on_mods", None)
    monkeypatch.setattr(mods_shared, "_state_cache", None)
    with patch.object(base, "mods_dir", str(tmp_path)), patch.object(base, "mods_config_dir", cfg):
        mods_shared.set_state_batch({"Mod A": False, "Mod C": True})

    with open(cfg) as file:
        data = json.load(file)
    assert data == {"#base": True, "Mod B": True, "Mod C": True}
