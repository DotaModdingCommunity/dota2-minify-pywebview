import base64
import os

from ui import actions


def _write_file(path, content: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def test_get_mod_file_preview_image_data_url(monkeypatch, tmp_path):
    monkeypatch.setattr(actions.base, "config_dir", str(tmp_path))
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    _write_file(os.path.join(str(tmp_path), "background.png"), png)

    result = actions._get_mod_file_preview("Custom Backgrounds", "background")

    assert result == f"data:image/png;base64,{base64.b64encode(png).decode()}"
    assert result.startswith("data:image/png;base64,")


def test_get_mod_file_preview_video_data_url(monkeypatch, tmp_path):
    monkeypatch.setattr(actions.base, "config_dir", str(tmp_path))
    mp4 = b"\x00\x00\x00\x18ftyp" + b"\x00" * 10
    _write_file(os.path.join(str(tmp_path), "background.mp4"), mp4)

    result = actions._get_mod_file_preview("Custom Backgrounds", "background")

    assert result.startswith("data:video/mp4;base64,")


def test_get_mod_file_preview_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(actions.base, "config_dir", str(tmp_path))

    assert actions._get_mod_file_preview("Custom Backgrounds", "background") is None


def test_get_mod_file_preview_oversized_returns_none(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(actions.base, "config_dir", str(tmp_path))
    monkeypatch.setattr(actions, "_MAX_PREVIEW_BYTES", 8)
    _write_file(os.path.join(str(tmp_path), "background.png"), b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    result = actions._get_mod_file_preview("Custom Backgrounds", "background")

    assert result is None
    assert "&preview_too_large_file" in capsys.readouterr().out


def test_get_mod_settings_includes_preview_file():
    data = actions._API_HANDLERS["get_mod_settings"]("Custom Backgrounds")

    assert data["preview_file"] == "background"
