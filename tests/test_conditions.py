from unittest.mock import patch


def _import_conditions():
    import conditions

    return conditions


def test_check_workshop_tools_optionaldlc_null_no_crash(tmp_path, monkeypatch):
    conditions = _import_conditions()
    from core import base

    acf_dir = tmp_path / "steamapps"
    acf_dir.mkdir()
    acf_path = acf_dir / f"appmanifest_{base.STEAM_DOTA_ID}.acf"
    acf_path.write_text("dummy", encoding="utf-8")

    workshop_id = base.STEAM_DOTA_WORKSHOP_TOOLS_ID
    fake_app_state = {
        "AppState": {
            "StateFlags": "4",
            "MountedConfig": {"optionaldlc": None, "DisabledDLC": workshop_id},
        }
    }

    monkeypatch.setattr("core.steam.LIBRARY", str(tmp_path))
    monkeypatch.setattr("vdf.load", lambda f: fake_app_state)

    result = conditions.check_workshop_tools()
    assert result is False


def test_check_workshop_tools_optionaldlc_mounted(tmp_path, monkeypatch):
    conditions = _import_conditions()
    from core import base

    workshop_id = base.STEAM_DOTA_WORKSHOP_TOOLS_ID
    fake_app_state = {
        "AppState": {
            "StateFlags": "4",
            "MountedConfig": {"optionaldlc": workshop_id, "DisabledDLC": None},
        }
    }

    acf_dir = tmp_path / "steamapps"
    acf_dir.mkdir()
    (acf_dir / f"appmanifest_{base.STEAM_DOTA_ID}.acf").write_text("dummy", encoding="utf-8")

    monkeypatch.setattr("core.steam.LIBRARY", str(tmp_path))
    monkeypatch.setattr("vdf.load", lambda f: fake_app_state)

    assert conditions.check_workshop_tools() is True


def test_resolve_dependencies_does_not_delete_s2v_without_workshop(monkeypatch):
    conditions = _import_conditions()
    from core import constants

    monkeypatch.setattr(conditions, "workshop_installed", False)
    monkeypatch.setattr("core.config.get", lambda key, default=None: default)
    monkeypatch.setattr(conditions, "_which", lambda name: None)
    monkeypatch.setattr("core.log.write_warning", lambda *a, **k: None)
    monkeypatch.setattr("core.log.write_crashlog", lambda: None)
    monkeypatch.setattr("core.output.add_text", lambda *a, **k: None)
    removed = []
    monkeypatch.setattr("core.fs.remove_path", lambda *a, **k: removed.append(a))

    def fail_download(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("core.fs.download_file", fail_download)

    conditions.resolve_dependencies(headless=True)

    assert all(str(p) != constants.s2v_executable for args in removed for p in args), (
        "existing Source2Viewer-CLI binary must not be deleted when workshop tools are unavailable"
    )


def test_resolve_dependencies_retry_preserves_headless(monkeypatch):
    conditions = _import_conditions()

    monkeypatch.setattr(conditions, "workshop_installed", False)
    monkeypatch.setattr("core.config.get", lambda key, default=None: default)
    monkeypatch.setattr(conditions, "_which", lambda name: None)
    monkeypatch.setattr("core.log.write_warning", lambda *a, **k: None)
    monkeypatch.setattr("core.log.write_crashlog", lambda: None)
    monkeypatch.setattr("core.output.add_text", lambda *a, **k: None)
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("core.fs.download_file", boom)

    conditions.resolve_dependencies(headless=True)

    assert opened == [], "headless mode must suppress the webbrowser.open fallback"


def test_which_returns_abs_path_when_file_exists(tmp_path, monkeypatch):
    conditions = _import_conditions()
    exe = tmp_path / "rg"
    exe.write_text("x", encoding="utf-8")
    if not conditions.base.is_win:
        exe.chmod(0o755)

    assert conditions._which(str(exe)) == str(exe)


def test_which_returns_none_when_missing(tmp_path):
    conditions = _import_conditions()

    assert conditions._which(str(tmp_path / "missing")) is None
    assert conditions._which("missing_binary") is None


def test_which_returns_none_when_not_executable_on_posix(tmp_path, monkeypatch):
    conditions = _import_conditions()
    monkeypatch.setattr(conditions.base, "is_win", False)
    exe = tmp_path / "rg"
    exe.write_text("x", encoding="utf-8")

    with patch("os.access", return_value=False):
        assert conditions._which(str(exe)) is None


def test_which_returns_path_when_executable_on_posix(tmp_path, monkeypatch):
    conditions = _import_conditions()
    monkeypatch.setattr(conditions.base, "is_win", False)
    exe = tmp_path / "rg"
    exe.write_text("x", encoding="utf-8")

    with patch("os.access", return_value=True):
        assert conditions._which(str(exe)) == str(exe)
