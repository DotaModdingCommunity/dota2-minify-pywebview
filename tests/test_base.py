import os

import pytest

from core import base


def test_steam_default_path_linux_uses_expanduser(monkeypatch):
    monkeypatch.setattr(base, "is_linux", True)
    monkeypatch.setattr(base, "is_mac", False)
    monkeypatch.setattr("os.path.expanduser", lambda path: "/home/fakeuser")

    assert base.steam_default_path() == os.path.join("/home/fakeuser", ".local", "share", "Steam")


def test_steam_default_path_linux_no_home_does_not_raise(monkeypatch):
    monkeypatch.setattr(base, "is_linux", True)
    monkeypatch.setattr(base, "is_mac", False)
    monkeypatch.setattr("os.path.expanduser", lambda path: path)

    assert base.steam_default_path() == os.path.join("~", ".local", "share", "Steam")


def test_steam_default_path_macos_uses_expanduser(monkeypatch):
    monkeypatch.setattr(base, "is_linux", False)
    monkeypatch.setattr(base, "is_mac", True)
    monkeypatch.setattr("os.path.expanduser", lambda path: "/Users/fakeuser")

    assert base.steam_default_path() == os.path.join("/Users/fakeuser", "Library", "Application Support", "Steam")


def test_steam_default_path_windows(monkeypatch):
    monkeypatch.setattr(base, "is_linux", False)
    monkeypatch.setattr(base, "is_mac", False)

    assert base.steam_default_path() == "C:\\Program Files (x86)\\Steam"


def _make_app_dir(tmp_path, with_mods: bool = True) -> str:
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    if with_mods:
        (app_dir / "mods" / "Some Mod").mkdir(parents=True)
    return str(app_dir)


def _blocking_makedirs(block_prefix: str):
    real_makedirs = os.makedirs

    def wrapped(path, *args, **kwargs):
        if str(path).startswith(block_prefix):
            raise PermissionError(path)
        return real_makedirs(path, *args, **kwargs)

    return wrapped


@pytest.mark.parametrize("is_win", [True, False])
def test_resolve_app_root_writable_returns_app_dir(monkeypatch, tmp_path, is_win):
    monkeypatch.setattr(base, "is_win", is_win)
    monkeypatch.setattr(base, "is_mac", False)
    app_dir = _make_app_dir(tmp_path)

    assert base.resolve_app_root(app_dir) == app_dir
    assert os.path.isdir(os.path.join(app_dir, "config"))
    assert os.path.isdir(os.path.join(app_dir, "logs"))


def test_resolve_app_root_falls_back_to_data_dir_when_read_only(monkeypatch, tmp_path):
    monkeypatch.setattr(base, "is_win", False)
    monkeypatch.setattr(base, "is_mac", False)
    monkeypatch.setattr("os.path.expanduser", lambda path: str(tmp_path))
    monkeypatch.setattr("os.makedirs", _blocking_makedirs(str(tmp_path / "app")))

    app_dir = _make_app_dir(tmp_path)
    data_dir = os.path.join(str(tmp_path), ".local", "share", "minify")

    assert base.resolve_app_root(app_dir) == data_dir
    assert os.path.isdir(os.path.join(data_dir, "config"))
    assert os.path.isdir(os.path.join(data_dir, "logs"))
    assert os.path.isdir(os.path.join(data_dir, "mods", "Some Mod"))


def test_resolve_app_root_macos_fallback_path(monkeypatch, tmp_path):
    monkeypatch.setattr(base, "is_win", False)
    monkeypatch.setattr(base, "is_mac", True)
    monkeypatch.setattr("os.path.expanduser", lambda path: str(tmp_path))
    monkeypatch.setattr("os.makedirs", _blocking_makedirs(str(tmp_path / "app")))

    app_dir = _make_app_dir(tmp_path)
    data_dir = os.path.join(str(tmp_path), "Library", "Application Support", "Minify")

    assert base.resolve_app_root(app_dir) == data_dir


def test_resolve_app_root_does_not_reseed_mods(monkeypatch, tmp_path):
    monkeypatch.setattr(base, "is_win", False)
    monkeypatch.setattr(base, "is_mac", False)
    monkeypatch.setattr("os.path.expanduser", lambda path: str(tmp_path))
    monkeypatch.setattr("os.makedirs", _blocking_makedirs(str(tmp_path / "app")))

    app_dir = _make_app_dir(tmp_path)
    data_dir = os.path.join(str(tmp_path), ".local", "share", "minify")
    os.makedirs(os.path.join(data_dir, "mods", "Existing"))

    base.resolve_app_root(app_dir)

    assert os.path.isdir(os.path.join(data_dir, "mods", "Existing"))
    assert not os.path.exists(os.path.join(data_dir, "mods", "Some Mod"))
