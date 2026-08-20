import os

from ui import actions


def test_reset_mod_settings_removes_config_and_returns_defaults(monkeypatch, tmp_path):
    config_dir = str(tmp_path)
    monkeypatch.setattr(actions.base, "config_dir", config_dir)
    config_file = os.path.join(config_dir, "Custom Backgrounds config.json")
    os.makedirs(config_dir, exist_ok=True)
    with open(config_file, "w") as f:
        f.write('{"bg_img_style": "custom"}')

    defaults = actions._reset_mod_settings("Custom Backgrounds")

    assert not os.path.exists(config_file)
    assert defaults["bg_img_style"].startswith("url(")
    assert defaults["select_background"] is None


def test_reset_mod_settings_missing_config_is_silent(monkeypatch, tmp_path):
    monkeypatch.setattr(actions.base, "config_dir", str(tmp_path))

    defaults = actions._reset_mod_settings("Custom Backgrounds")

    assert defaults["bg_img_style"].startswith("url(")


def test_reset_all_mod_settings_removes_only_mod_configs(monkeypatch, tmp_path):
    config_dir = str(tmp_path)
    monkeypatch.setattr(actions.base, "config_dir", config_dir)
    os.makedirs(config_dir, exist_ok=True)
    for name in ("Mod A", "Mod B"):
        with open(os.path.join(config_dir, f"{name} config.json"), "w") as f:
            f.write('{"x": 1}')
    other = os.path.join(config_dir, "settings.json")
    with open(other, "w") as f:
        f.write("{}")

    actions._reset_all_mod_settings()

    assert not os.path.exists(os.path.join(config_dir, "Mod A config.json"))
    assert not os.path.exists(os.path.join(config_dir, "Mod B config.json"))
    assert os.path.exists(other)
