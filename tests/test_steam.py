import os
from unittest.mock import MagicMock

import pytest
from core import base
from core.constants import resolve_locale
from core.steam import _remove_lang_arg, remove_minify_lang, restore_boot_language


def test_remove_specific_lang_arg():
    # Test removing a specific language
    assert _remove_lang_arg("-language minify -novid", "minify") == "-novid"
    assert _remove_lang_arg("-novid -language minify", "minify") == "-novid"
    assert _remove_lang_arg("-language english -language minify", "minify") == "-language english"
    assert _remove_lang_arg("-language minify -language english", "minify") == "-language english"

    # Test when language is not present
    assert _remove_lang_arg("-novid", "minify") == "-novid"

    # Test when different language is present
    assert _remove_lang_arg("-language english", "minify") == "-language english"

    # Test empty string
    assert _remove_lang_arg("", "minify") == ""

    # Test None
    assert _remove_lang_arg(None, "minify") == ""


@pytest.fixture
def mock_steam_env(monkeypatch):
    mock_accounts = [{"id": "123", "name": "User"}]
    monkeypatch.setattr("core.steam.get_steam_accounts", lambda: mock_accounts)

    def config_get_side_effect(key, default=None):
        if key == "steam_root":
            return "/fake/steam"
        if key == "output_locale":
            return "english"
        if key == "steam_id":
            return "123"
        return default

    monkeypatch.setattr("core.config.get", config_get_side_effect)
    return mock_accounts


def test_resolve_locale():
    assert resolve_locale("dutch") == "dutch"
    assert resolve_locale("english") == "dutch"
    assert resolve_locale("minify") == "minify"
    assert resolve_locale("french") == "french"
    assert resolve_locale("unknown") == "unknown"


def test_remove_minify_lang_success(mock_steam_env, monkeypatch):
    import vdf
    from core import base

    # English locale should resolve to dutch and remove -language dutch
    def config_get_side_effect(key, default=None):
        if key == "apply_for_all":
            return True
        if key == "steam_root":
            return "/fake/steam"
        if key == "output_locale":
            return "english"
        if key == "steam_id":
            return "123"
        return default

    monkeypatch.setattr("core.config.get", config_get_side_effect)

    vdf_data = {
        "UserLocalConfigStore": {
            "Software": {
                "Valve": {"Steam": {"apps": {base.STEAM_DOTA_ID: {"LaunchOptions": "-language dutch -novid"}}}}
            }
        }
    }

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("core.utils.open_utf8", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: vdf_data)

    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)

    result = remove_minify_lang()

    assert result == ["123"]
    assert (
        vdf_data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID]["LaunchOptions"]
        == "-novid"
    )
    assert mock_dump.called


def test_remove_minify_lang_wrong_locale(mock_steam_env, monkeypatch):
    import vdf

    def config_get_side_effect(key, default=None):
        if key == "steam_root":
            return "/fake/steam"
        if key == "output_locale":
            return "russian"  # Not english
        return default

    monkeypatch.setattr("core.config.get", config_get_side_effect)
    monkeypatch.setattr("os.path.exists", lambda path: True)

    mock_load = MagicMock(return_value={})
    monkeypatch.setattr("vdf.load", mock_load)
    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())

    result = remove_minify_lang()

    assert result == []
    assert mock_load.called
    assert not mock_dump.called


def test_remove_minify_lang_no_vdf(mock_steam_env, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda path: False)

    result = remove_minify_lang()
    assert result == []


def test_remove_minify_lang_no_language_arg(mock_steam_env, monkeypatch):
    import vdf
    from core import base

    vdf_data = {
        "UserLocalConfigStore": {
            "Software": {"Valve": {"Steam": {"apps": {base.STEAM_DOTA_ID: {"LaunchOptions": "-novid"}}}}}
        }
    }

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: vdf_data)
    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)

    result = remove_minify_lang()

    assert result == []
    assert not mock_dump.called


def test_remove_minify_lang_cleans_all_accounts(mock_steam_env, monkeypatch):
    import vdf
    from core import base

    monkeypatch.setattr(
        "core.steam.get_steam_accounts",
        lambda: [{"id": "123", "name": "User1"}, {"id": "456", "name": "User2"}],
    )

    def make_data():
        return {
            "UserLocalConfigStore": {
                "Software": {
                    "Valve": {"Steam": {"apps": {base.STEAM_DOTA_ID: {"LaunchOptions": "-language dutch -novid"}}}}
                }
            }
        }

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("core.utils.open_utf8", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: make_data())
    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)

    result = remove_minify_lang()

    assert result == ["123", "456"]
    assert mock_dump.call_count == 2
    written = mock_dump.call_args[0][0]
    assert (
        written["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID]["LaunchOptions"]
        == "-novid"
    )


def test_remove_minify_lang_no_launch_options(mock_steam_env, monkeypatch):
    import vdf
    from core import base

    vdf_data = {
        "UserLocalConfigStore": {
            "Software": {"Valve": {"Steam": {"apps": {base.STEAM_DOTA_ID: {}}}}}  # Missing LaunchOptions
        }
    }

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: vdf_data)

    result = remove_minify_lang()
    assert result == []


def test_restore_boot_language_restores_to_english(monkeypatch):
    import vdf

    def config_get_side_effect(key, default=None):
        if key == "output_locale":
            return "english"
        if key == "steam_library":
            return "/fake/steam"
        return default

    monkeypatch.setattr("core.config.get", config_get_side_effect)

    vdf_data = {"boot": {"UILanguage": "dutch", "AudioLanguage": "english"}}
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("core.utils.open_utf8", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: vdf_data)
    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)

    assert restore_boot_language() is True
    assert vdf_data["boot"]["UILanguage"] == "english"
    assert vdf_data["boot"]["AudioLanguage"] == "english"
    assert mock_dump.called


def test_restore_boot_language_wrong_locale(monkeypatch):
    import vdf

    def config_get_side_effect(key, default=None):
        if key == "output_locale":
            return "french"
        return default

    monkeypatch.setattr("core.config.get", config_get_side_effect)
    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)

    assert restore_boot_language() is False
    assert not mock_dump.called


def test_restore_boot_language_not_dutch(monkeypatch):
    import vdf

    monkeypatch.setattr(
        "core.config.get",
        lambda key, default=None: (
            "english" if key == "output_locale" else "/fake/steam" if key == "steam_library" else default
        ),
    )

    vdf_data = {"boot": {"UILanguage": "english", "AudioLanguage": "english"}}
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("core.utils.open_utf8", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: vdf_data)
    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)

    assert restore_boot_language() is False
    assert not mock_dump.called


def test_restore_boot_language_no_vcfg(monkeypatch):
    import vdf

    monkeypatch.setattr(
        "core.config.get",
        lambda key, default=None: (
            "english" if key == "output_locale" else "/fake/steam" if key == "steam_library" else default
        ),
    )
    monkeypatch.setattr("os.path.exists", lambda path: False)
    mock_dump = MagicMock()
    monkeypatch.setattr("vdf.dump", mock_dump)

    assert restore_boot_language() is False
    assert not mock_dump.called


@pytest.mark.parametrize(
    "input_string, expected",
    [
        # Empty/None cases
        (None, ""),
        ("", ""),
        ("   ", ""),
        # Normal cases
        ("-language english -console", "-console"),
        ("-novid -language turkish -console +fps_max 60", "-novid -console +fps_max 60"),
        # No language flag
        ("-console -novid", "-console -novid"),
        # Trailing without value
        ("-console -language", "-console"),
        # Followed by another flag
        ("-language -console", "-console"),
        ("-language +fps_max 60 -console", "+fps_max 60 -console"),
        # Multiple language flags
        ("-language english -console -language russian", "-console"),
        ("-language english -language turkish", ""),
        # Edge cases
        ("-language", ""),
        ("-language english", ""),
    ],
)
def test_remove_lang_arg(input_string, expected):
    assert _remove_lang_arg(input_string) == expected


def test_apply_and_restart_steam_already_set_skips_restart(monkeypatch):
    from core.steam import apply_and_restart_steam

    monkeypatch.setattr("core.steam.config.get_locale", lambda: "english")
    monkeypatch.setattr(
        "core.steam.check_launch_options",
        lambda ids, locale: [{"steam_id": "1", "name": "A", "status": "already_set"}],
    )
    apply_calls = []
    monkeypatch.setattr(
        "core.steam._apply_launch_options",
        lambda ids, locale: apply_calls.append("apply") or [],
    )
    calls = []
    monkeypatch.setattr("core.steam.is_steam_running", lambda: True)
    monkeypatch.setattr("core.steam.kill_steam", lambda: calls.append("kill") or True)
    monkeypatch.setattr("core.steam.wait_steam_exit", lambda **k: calls.append("wait") or True)
    monkeypatch.setattr("core.steam.launch_steam", lambda: calls.append("launch") or True)

    result = apply_and_restart_steam(["1"])

    assert result["restart_needed"] is False
    assert result["steam_killed"] is False
    assert result["steam_exited"] is False
    assert result["steam_launched"] is False
    assert calls == [], "no Steam restart should be attempted when nothing changed"
    assert apply_calls == [], "no write should happen when nothing changed"


def test_apply_and_restart_steam_changes_restarts(monkeypatch):
    from core.steam import apply_and_restart_steam

    monkeypatch.setattr("core.steam.config.get_locale", lambda: "english")
    monkeypatch.setattr(
        "core.steam.check_launch_options",
        lambda ids, locale: [{"steam_id": "1", "name": "A", "status": "needs_change"}],
    )
    monkeypatch.setattr(
        "core.steam._apply_launch_options",
        lambda ids, locale: [{"steam_id": "1", "name": "A", "status": "ok"}],
    )
    monkeypatch.setattr("core.steam.is_steam_running", lambda: True)
    monkeypatch.setattr("core.steam.kill_steam", lambda: True)
    monkeypatch.setattr("core.steam.wait_steam_exit", lambda **k: True)
    monkeypatch.setattr("core.steam.launch_steam", lambda: True)

    result = apply_and_restart_steam(["1"])

    assert result["restart_needed"] is True
    assert result["steam_killed"] is True
    assert result["steam_exited"] is True
    assert result["steam_launched"] is True


def _mock_apply_vdf(monkeypatch, launch_options):
    import vdf
    from core import base

    vdf_data = {
        "UserLocalConfigStore": {
            "Software": {"Valve": {"Steam": {"apps": {base.STEAM_DOTA_ID: {"LaunchOptions": launch_options}}}}}
        }
    }
    monkeypatch.setattr("core.steam.get_steam_accounts", lambda: [{"id": "123", "name": "User"}])
    monkeypatch.setattr(
        "core.config.get",
        lambda key, default=None: "/fake/steam" if key == "steam_root" else default,
    )
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("os.replace", MagicMock())
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: vdf_data)
    monkeypatch.setattr("vdf.dump", MagicMock())
    return vdf_data


def test_apply_launch_options_resolves_locale_alias(monkeypatch):
    from core import base
    from core.steam import _apply_launch_options

    vdf_data = _mock_apply_vdf(monkeypatch, "-language russian -novid")
    result = _apply_launch_options(["123"], "english")

    assert result[0]["status"] == "ok"
    written = vdf_data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID][
        "LaunchOptions"
    ]
    assert written == "-language dutch -novid"


def test_apply_launch_options_resolved_alias_detects_already_set(monkeypatch):
    from core.steam import _apply_launch_options

    _mock_apply_vdf(monkeypatch, "-language dutch -novid")
    result = _apply_launch_options(["123"], "english")

    assert result[0]["status"] == "already_set"


def test_check_launch_options_is_read_only(monkeypatch):
    import vdf
    from core.steam import check_launch_options

    _mock_apply_vdf(monkeypatch, "-language russian -novid")
    dump_mock = MagicMock()
    replace_mock = MagicMock()
    monkeypatch.setattr("vdf.dump", dump_mock)
    monkeypatch.setattr("os.replace", replace_mock)

    result = check_launch_options(["123"], "english")

    assert result[0]["status"] == "needs_change"
    assert not dump_mock.called
    assert not replace_mock.called


def test_check_launch_options_resolved_alias_detects_already_set(monkeypatch):
    from core.steam import check_launch_options

    _mock_apply_vdf(monkeypatch, "-language dutch -novid")
    result = check_launch_options(["123"], "english")

    assert result[0]["status"] == "already_set"


def test_apply_and_restart_steam_rewrites_after_steam_exits(monkeypatch):
    from core.steam import apply_and_restart_steam

    calls = []
    monkeypatch.setattr("core.steam.config.get_locale", lambda: "russian")

    monkeypatch.setattr(
        "core.steam.check_launch_options",
        lambda ids, locale: calls.append("check") or [{"steam_id": "1", "name": "A", "status": "needs_change"}],
    )
    monkeypatch.setattr(
        "core.steam._apply_launch_options",
        lambda ids, locale: calls.append("apply") or [{"steam_id": "1", "name": "A", "status": "ok"}],
    )
    monkeypatch.setattr("core.steam.is_steam_running", lambda: True)
    monkeypatch.setattr("core.steam.kill_steam", lambda: calls.append("kill") or True)
    monkeypatch.setattr("core.steam.wait_steam_exit", lambda **k: calls.append("wait") or True)
    monkeypatch.setattr("core.steam.launch_steam", lambda: calls.append("launch") or True)

    result = apply_and_restart_steam(["1"])

    assert result["restart_needed"] is True
    assert result["steam_killed"] is True
    assert result["steam_exited"] is True
    assert result["steam_launched"] is True
    assert calls == ["check", "kill", "wait", "apply", "launch"]


def test_loginusers_personas_maps_steam64_to_account_id(monkeypatch):
    from core.steam import _loginusers_personas

    monkeypatch.setattr("core.steam.ROOT", "/fake/steam")
    monkeypatch.setattr("os.path.exists", lambda path: path.endswith("loginusers.vdf"))
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    loginusers = {
        "users": {
            "76561197961690934": {"AccountName": "cowking@t-online.de", "PersonaName": "WIP"},
            "76561198077941024": {"PersonaName": "106"},
            "76561198206966992": {"PersonaName": "tyutyy"},
            "not-a-number": {"PersonaName": "junk"},
        }
    }
    monkeypatch.setattr("vdf.load", lambda f: loginusers)

    assert _loginusers_personas() == {"1425206": "WIP", "117675296": "106", "246701264": "tyutyy"}


def test_get_steam_accounts_prefers_loginusers_personas(monkeypatch):
    from core.steam import get_steam_accounts

    monkeypatch.setattr("core.steam.ROOT", "/fake/steam")
    monkeypatch.setattr("core.steam._loginusers_personas", lambda: {"117675296": "106", "246701264": "tyutyy"})
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("os.path.isdir", lambda path: True)
    monkeypatch.setattr("os.listdir", lambda path: ["117675296", "1425206", "246701264"])
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("vdf.load", lambda f: {"UserLocalConfigStore": {"friends": {"PersonaName": "WIP"}}})

    result = get_steam_accounts()

    assert {a["id"]: a["name"] for a in result} == {"117675296": "106", "1425206": "WIP", "246701264": "tyutyy"}


def test_check_launch_options_corrupt_vdf_is_needs_change(monkeypatch):
    import vdf
    from core.steam import check_launch_options

    monkeypatch.setattr("core.steam.get_steam_accounts", lambda: [{"id": "123", "name": "User"}])
    monkeypatch.setattr(
        "core.config.get",
        lambda key, default=None: "/fake/steam" if key == "steam_root" else default,
    )
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("vdf.load", MagicMock(side_effect=SyntaxError("corrupt")))

    result = check_launch_options(["123"], "russian")

    assert result[0]["status"] == "needs_change"


def test_apply_launch_options_repairs_corrupt_vdf(monkeypatch):
    import vdf
    from core import base
    from core.steam import _apply_launch_options

    monkeypatch.setattr("core.steam.get_steam_accounts", lambda: [{"id": "123", "name": "User"}])
    monkeypatch.setattr(
        "core.config.get",
        lambda key, default=None: "/fake/steam" if key == "steam_root" else default,
    )
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("os.replace", MagicMock())
    monkeypatch.setattr("core.utils.open_utf8R", MagicMock())
    monkeypatch.setattr("vdf.load", MagicMock(side_effect=SyntaxError("corrupt")))
    dump_mock = MagicMock()
    monkeypatch.setattr("vdf.dump", dump_mock)
    copy_mock = MagicMock()
    monkeypatch.setattr("shutil.copy2", copy_mock)

    result = _apply_launch_options(["123"], "russian")

    assert result[0]["status"] == "ok"
    copy_mock.assert_called_once_with(
        os.path.join("/fake/steam", "userdata", "123", "config", "localconfig.vdf"),
        os.path.join("/fake/steam", "userdata", "123", "config", "localconfig.vdf.minify_bak"),
    )
    dumped = dump_mock.call_args[0][0]
    apps = dumped["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"]
    assert apps[base.STEAM_DOTA_ID]["LaunchOptions"].strip() == "-language russian"


class _FakeRegKey:
    pass


class _FakeWinreg:
    HKEY_LOCAL_MACHINE = "HKLM"
    KEY_READ = 0x20019
    KEY_WOW64_64KEY = 0x0100

    def __init__(self, fail_32bit=False):
        self.fail_32bit = fail_32bit
        self.opened = []

    def OpenKey(self, hkey, subkey, access=0):
        self.opened.append((subkey, access))
        if self.fail_32bit and subkey == r"SOFTWARE\WOW6432Node\Valve\Steam":
            raise OSError("no 32-bit view")
        return _FakeRegKey()

    def QueryValueEx(self, hkey, name):
        return ("/fake/steam/registry", 1)


def _install_winreg(monkeypatch, fail_32bit=False):
    import sys

    fake = _FakeWinreg(fail_32bit)
    monkeypatch.setitem(sys.modules, "winreg", fake)
    return fake


@pytest.mark.skipif(not base.is_win, reason="Windows registry only")
def test_get_steam_root_uses_32bit_hive_first(monkeypatch):
    from core import config, steam

    monkeypatch.setattr("core.config.get", lambda key, default=None: "" if key == "steam_root" else default)
    fake = _install_winreg(monkeypatch, fail_32bit=False)
    assert steam.get_steam_root_path() == "/fake/steam/registry"
    assert fake.opened[0][0] == r"SOFTWARE\WOW6432Node\Valve\Steam"


@pytest.mark.skipif(not base.is_win, reason="Windows registry only")
def test_get_steam_root_falls_back_to_64bit_hive(monkeypatch):
    from core import steam

    monkeypatch.setattr("core.config.get", lambda key, default=None: "" if key == "steam_root" else default)
    fake = _install_winreg(monkeypatch, fail_32bit=True)
    assert steam.get_steam_root_path() == "/fake/steam/registry"
    assert fake.opened[0][0] == r"SOFTWARE\WOW6432Node\Valve\Steam"
    assert fake.opened[1][0] == r"SOFTWARE\Valve\Steam"
    assert fake.opened[1][1] & _FakeWinreg.KEY_WOW64_64KEY
