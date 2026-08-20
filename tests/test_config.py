import importlib
import json
import os
import threading
import time

import pytest


@pytest.fixture
def real_config():
    """Restore the real core.config implementations for white-box testing.

    tests/conftest.py replaces config.get/set with MagicMocks at import time;
    this fixture reloads the module (so the real functions exist) and restores
    the conftest mocks when the test finishes.

    Note: monkeypatch is deliberately NOT used here. importlib.reload replaces
    get/set with the real functions before setattr is called, so monkeypatch
    would record the real function as the pre-test value and its teardown would
    leave the conftest mocks permanently lost for the rest of the suite. A
    try/finally restores them explicitly.
    """
    import core.config as config

    conftest_get = config.get
    conftest_set = config.set
    reloaded = importlib.reload(config)
    assert reloaded.get is not conftest_get
    try:
        yield config
    finally:
        config.get = conftest_get
        config.set = conftest_set


def test_write_json_file_retries_then_succeeds(tmp_path, monkeypatch, real_config):
    config = real_config
    path = str(tmp_path / "minify_config.json")
    real_replace = os.replace
    calls = {"n": 0}

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError(5, "Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)
    assert config.write_json_file(path, {"k": 1}) is True
    with open(path, encoding="utf-8") as f:
        assert json.load(f) == {"k": 1}
    assert calls["n"] >= 2


def test_write_json_file_falls_back_to_direct_write(tmp_path, monkeypatch, real_config):
    config = real_config
    path = str(tmp_path / "minify_config.json")

    def broken_replace(src, dst):
        raise OSError(5, "Access is denied")

    monkeypatch.setattr(os, "replace", broken_replace)
    assert config.write_json_file(path, {"k": 1}) is True
    with open(path, encoding="utf-8") as f:
        assert json.load(f) == {"k": 1}


def test_write_json_file_sweeps_stale_tmp(tmp_path, monkeypatch, real_config):
    config = real_config
    path = str(tmp_path / "minify_config.json")
    stale = tmp_path / "minify_config.json.tmp.999.1"
    stale.write_text("{}", encoding="utf-8")

    assert config.write_json_file(path, {"k": 1}) is True
    assert not stale.exists()


def test_set_writes_under_lock(tmp_path, monkeypatch, real_config):
    config = real_config
    from core import base

    cfg_file = tmp_path / "minify_config.json"
    monkeypatch.setattr(base, "main_config_file_dir", str(cfg_file))
    config._config_cache = None

    in_write = threading.Event()
    release = threading.Event()
    original = config.write_json_file

    def slow_write(path, data):
        in_write.set()
        release.wait(2)
        return original(path, data)

    monkeypatch.setattr(config, "write_json_file", slow_write)

    t = threading.Thread(target=lambda: config.set("k", 1))
    t.start()
    assert in_write.wait(1), "write_json_file must run while set() holds the lock"

    got = []

    def do_get():
        got.append(config.get("k"))

    g = threading.Thread(target=do_get)
    g.start()
    time.sleep(0.2)
    assert got == [], "a concurrent get() must wait for the in-progress set() write"

    release.set()
    t.join()
    g.join()
    assert got == [1]


def test_reset_all_preserves_steam_paths_clears_mod_state(tmp_path, monkeypatch, real_config):
    config = real_config
    from core import base

    cfg_file = tmp_path / "minify_config.json"
    mod_dir = tmp_path / "configs"
    mod_dir.mkdir()
    monkeypatch.setattr(base, "main_config_file_dir", str(cfg_file))
    monkeypatch.setattr(base, "config_dir", str(mod_dir))
    config._config_cache = None
    config._mod_config_cache = {}

    config.set("steam_root", "C:/Steam")
    config.set("steam_library", "D:/Games")
    config.set("locale", "RU")
    config.set("modconf", {"d2pfx_mod": {"enabled": True}})
    (mod_dir / "My Mod config.json").write_text("{}", encoding="utf-8")

    config.reset_all()

    assert config.get("steam_root") == "C:/Steam"
    assert config.get("steam_library") == "D:/Games"
    assert config.get("locale") == "EN"
    assert config.get("modconf") == {}
    assert not (mod_dir / "My Mod config.json").exists()
