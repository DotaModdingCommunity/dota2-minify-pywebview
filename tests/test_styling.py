from unittest.mock import MagicMock

from patch import styling


def _parse(content, monkeypatch, mod_settings=None, mod_cfg=None):
    styling_dictionary = {}
    core_extracts = []
    dota_extracts = []
    monkeypatch.setattr(styling.fs, "create_dirs", MagicMock())

    styling.parse_styling_content(
        content,
        mod_cfg=mod_cfg or {"settings": [{"key": "accent", "default": "#f00"}]},
        folder="TestMod",
        mod_settings=mod_settings or {},
        styling_dictionary=styling_dictionary,
        core_extracts=core_extracts,
        dota_extracts=dota_extracts,
    )
    return styling_dictionary, core_extracts, dota_extracts


def test_parse_styling_content_setting_overrides_default(monkeypatch):
    content = "/* g:panorama/styles/test */ #x { color: <&accent>; }"
    dict_, _, _ = _parse(content, monkeypatch, mod_settings={"accent": "#0f0"})
    (path, style) = dict_["styling-css-TestMod-0"]

    assert path == "panorama/styles/test"
    assert "#0f0" in style
    assert "<&accent>" not in style


def test_parse_styling_content_falls_back_to_manifest_default(monkeypatch):
    content = "/* g:panorama/styles/test */ #x { color: <&accent>; }"
    dict_, _, _ = _parse(content, monkeypatch, mod_settings={})
    (_, style) = dict_["styling-css-TestMod-0"]

    assert "#f00" in style
    assert "<&accent>" not in style


def test_parse_styling_content_unknown_key_stays_literal(monkeypatch):
    content = "/* g:panorama/styles/test */ #x { color: <&nope>; }"
    dict_, _, _ = _parse(content, monkeypatch, mod_settings={})
    (_, style) = dict_["styling-css-TestMod-0"]

    assert "<&nope>" in style


def test_parse_styling_content_c_indicator_is_core_extract(monkeypatch):
    content = "/* c:panorama/styles/panel */ #p { width: 10px; }"
    _, core_extracts, dota_extracts = _parse(content, monkeypatch)

    assert core_extracts == ["panorama/styles/panel.vcss_c"]
    assert dota_extracts == []


def test_parse_styling_content_g_indicator_is_dota_extract(monkeypatch):
    content = "/* g:panorama/styles/panel */ #p { width: 10px; }"
    _, core_extracts, dota_extracts = _parse(content, monkeypatch)

    assert dota_extracts == ["panorama/styles/panel.vcss_c"]
    assert core_extracts == []


def test_parse_styling_content_empty_section_skipped(monkeypatch):
    content = "/* g:panorama/styles/a */ /* g:panorama/styles/b */ #b { height: 5px; }"
    dict_, _, dota_extracts = _parse(content, monkeypatch)

    assert "styling-css-TestMod-0" not in dict_
    assert "styling-css-TestMod-1" in dict_
    assert dota_extracts == ["panorama/styles/b.vcss_c"]


def test_parse_styling_content_multiple_sections(monkeypatch):
    content = "/* g:a */ #a {} /* c:b */ #b {}"
    dict_, core_extracts, dota_extracts = _parse(content, monkeypatch)

    assert set(dict_) == {"styling-css-TestMod-0", "styling-css-TestMod-1"}
    assert dota_extracts == ["a.vcss_c"]
    assert core_extracts == ["b.vcss_c"]
