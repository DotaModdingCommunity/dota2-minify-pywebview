from unittest.mock import MagicMock, patch

import pytest

import core.config
from core import mods_shared


@pytest.fixture(autouse=True)
def _restore_config_mocks():
    """Several tests replace core.config.get/set at test scope; restore the
    conftest fakes afterwards so later test files aren't affected."""
    get_orig = core.config.get
    set_orig = core.config.set
    yield
    core.config.get = get_orig
    core.config.set = set_orig


def _make_dm(mods_data, constants=None):
    dm = MagicMock()
    dm.is_loaded.return_value = True
    dm.get_mods.return_value = mods_data
    dm.get_categories.return_value = ["heroes"]
    dm.get_file_url.side_effect = lambda cat, fn: f"https://assets/{cat}/{fn}"
    return dm


@patch("ui.actions.fs.download_file", return_value=False)
@patch("ui.actions.fs.create_dirs")
@patch("ui.actions.output.add_text")
def test_load_preview_failure_uses_warning_level_and_dedupe(mock_add_text, mock_dirs, mock_dl, tmp_path):
    from ui import actions

    dm = MagicMock()
    dm.previews_dir = str(tmp_path)
    dm.get_preview_url.side_effect = lambda cat, fn: f"https://previews/{cat}/{fn}"

    actions._preview_warned.clear()
    assert actions._d2pfx_load_preview(dm, "heroes", "ns.webp") is None
    assert actions._d2pfx_load_preview(dm, "heroes", "ns.webp") is None

    mock_dl.assert_called()
    for call in mock_dl.call_args_list:
        assert call.kwargs.get("log_level") == "warning"
        assert call.kwargs.get("dedupe_set") is actions._preview_warned
    mock_add_text.assert_not_called()


def test_get_preview_url_image_uses_data_branch():
    from browsers.d2pfx.data import DataManager

    dm = DataManager.__new__(DataManager)
    url = dm.get_preview_url("heroes", "ns.webp")
    assert url == "https://raw.githubusercontent.com/h6rd/Dota2PornFxWeb/data/previews/heroes/ns.jpg"


def test_get_preview_url_mp4_uses_main_assets():
    from browsers.d2pfx.data import DataManager

    dm = DataManager.__new__(DataManager)
    url = dm.get_preview_url("terrains", "Flat Green Terrain.mp4")
    assert (
        url
        == "https://raw.githubusercontent.com/h6rd/Dota2PornFxWeb/main/assets/previews/terrains/Flat Green Terrain.mp4"
    )


def test_get_preview_url_webm_uses_main_assets():
    from browsers.d2pfx.data import DataManager

    dm = DataManager.__new__(DataManager)
    url = dm.get_preview_url("heroes", "effect.webm")
    assert url == "https://raw.githubusercontent.com/h6rd/Dota2PornFxWeb/main/assets/previews/heroes/effect.webm"


def _styles_mod():
    return {
        "name": "Night Stalker Remilia",
        "preview": None,
        "file": None,
        "tags": {"effects": True},
        "links": [],
        "styles": [
            {"label": "Style I", "color": "#ddd4ff", "preview": "ns.webp", "file": "ns.zip"},
            {"label": "Style II", "color": "#da7777", "preview": "ns2.webp", "file": "ns2.zip"},
        ],
    }


def _plain_mod():
    return {
        "name": "Bare Brewmaster",
        "preview": "bb.webp",
        "file": "bb.zip",
        "tags": {},
        "links": [],
    }


@patch("ui.actions._d2pfx_bg_preload_category", lambda *a, **k: None)
def test_get_d2pfx_mods_expands_styles_into_variants():
    from ui import actions

    with patch.object(actions, "_get_d2pfx_dm", return_value=_make_dm([_styles_mod(), _plain_mod()])):
        core.config.get = MagicMock(side_effect=lambda key, default=None: default)
        core.config.set = MagicMock()

        result = actions._get_d2pfx_mods("heroes")

    styles_entry = next(r for r in result if r["name"] == "Night Stalker Remilia")
    assert styles_entry["variants"] is not None
    assert styles_entry["preview"] == "ns.webp"
    assert styles_entry["enabled"] is False

    v1, v2 = styles_entry["variants"]
    assert v1["label"] == "Style I"
    assert v1["color"] == "#ddd4ff"
    assert v1["preview"] == "ns.webp"
    assert v1["fileUrl"] == "https://assets/heroes/ns.zip"
    assert v1["isZip"] is True
    assert v1["modDirName"] == "D2PFX HEROES - Night Stalker Remilia (Style I)"
    assert v2["modDirName"] == "D2PFX HEROES - Night Stalker Remilia (Style II)"


@patch("ui.actions._d2pfx_bg_preload_category", lambda *a, **k: None)
def test_get_d2pfx_mods_styles_fallback_label_for_empty():
    from ui import actions

    mod = _styles_mod()
    mod["styles"] = [{"label": "", "color": "#fff", "preview": "a.webp", "file": "a.zip"}]

    with patch.object(actions, "_get_d2pfx_dm", return_value=_make_dm([mod])):
        core.config.get = MagicMock(side_effect=lambda key, default=None: default)
        core.config.set = MagicMock()

        result = actions._get_d2pfx_mods("heroes")

    assert result[0]["variants"][0]["label"] == "Variant 1"


@patch("ui.actions._d2pfx_bg_preload_category", lambda *a, **k: None)
def test_get_d2pfx_mods_non_styles_unchanged():
    from ui import actions

    with patch.object(actions, "_get_d2pfx_dm", return_value=_make_dm([_plain_mod()])):
        core.config.get = MagicMock(side_effect=lambda key, default=None: default)
        core.config.set = MagicMock()

        result = actions._get_d2pfx_mods("heroes")

    assert len(result) == 1
    entry = result[0]
    assert entry["name"] == "Bare Brewmaster"
    assert "variants" not in entry
    assert entry["fileUrl"] == "https://assets/heroes/bb.zip"
    assert entry["isZip"] is True


def test_toggle_d2pfx_mod_enable_disables_siblings():
    from ui import actions

    modconf = {
        "D2PFX HEROES - Night Stalker Remilia (Style I)": {"enabled": False, "url": "u1", "is_zip": True},
        "D2PFX HEROES - Night Stalker Remilia (Style II)": {"enabled": True, "url": "u2", "is_zip": True},
    }
    core.config.get = MagicMock(side_effect=lambda key, default=None: modconf if key == "modconf" else default)
    core.config.set = MagicMock(side_effect=lambda key, val: None)

    with patch.object(mods_shared, "set_state_batch") as m_set:
        actions._toggle_d2pfx_mod(
            "D2PFX HEROES - Night Stalker Remilia (Style I)",
            True,
            "u1",
            True,
            disable_others=["D2PFX HEROES - Night Stalker Remilia (Style II)"],
        )

    updated = core.config.set.call_args.args[1]
    assert updated["D2PFX HEROES - Night Stalker Remilia (Style I)"]["enabled"] is True
    assert updated["D2PFX HEROES - Night Stalker Remilia (Style II)"]["enabled"] is False
    assert updated["D2PFX HEROES - Night Stalker Remilia (Style II)"]["url"] == "u2"

    states = m_set.call_args.args[0]
    assert states["D2PFX HEROES - Night Stalker Remilia (Style I)"] is True
    assert states["D2PFX HEROES - Night Stalker Remilia (Style II)"] is False


def test_toggle_d2pfx_mod_disable_keeps_others():
    from ui import actions

    modconf = {
        "D2PFX HEROES - Night Stalker Remilia (Style I)": {"enabled": True, "url": "u1", "is_zip": True},
        "D2PFX HEROES - Night Stalker Remilia (Style II)": {"enabled": False, "url": "u2", "is_zip": True},
    }
    core.config.get = MagicMock(side_effect=lambda key, default=None: modconf if key == "modconf" else default)
    core.config.set = MagicMock()

    with patch.object(mods_shared, "set_state_batch"):
        actions._toggle_d2pfx_mod("D2PFX HEROES - Night Stalker Remilia (Style I)", False, "u1", True)

    updated = core.config.set.call_args.args[1]
    assert updated["D2PFX HEROES - Night Stalker Remilia (Style I)"]["enabled"] is False
    # Siblings are not touched when disabling
    assert updated["D2PFX HEROES - Night Stalker Remilia (Style II)"]["enabled"] is False


def test_get_d2pfx_selected_variants_returns_saved():
    from ui import actions

    saved = {"D2PFX HEROES - Night Stalker Remilia": "D2PFX HEROES - Night Stalker Remilia (Style II)"}
    core.config.get = MagicMock(
        side_effect=lambda key, default=None: saved if key == "d2pfx_selected_variants" else default
    )

    result = actions._get_d2pfx_selected_variants()
    assert result == saved


def test_set_d2pfx_selected_variants_persists_string_pairs():
    from ui import actions

    core.config.set = MagicMock()
    data = {
        "D2PFX HEROES - Night Stalker Remilia": "D2PFX HEROES - Night Stalker Remilia (Style II)",
        "": "D2PFX HEROES - Night Stalker Remilia (Style I)",
        "No variant": "",
        42: "ignored",
    }

    result = actions._set_d2pfx_selected_variants(data)

    core.config.set.assert_called_once()
    saved = core.config.set.call_args.args[1]
    assert saved == {"D2PFX HEROES - Night Stalker Remilia": "D2PFX HEROES - Night Stalker Remilia (Style II)"}
    assert result == saved


def test_set_d2pfx_selected_variants_rejects_non_dict():
    from ui import actions

    core.config.set = MagicMock()
    try:
        actions._set_d2pfx_selected_variants(["not", "a", "dict"])
        assert False, "Expected ValueError"
    except ValueError:
        pass
    core.config.set.assert_not_called()
