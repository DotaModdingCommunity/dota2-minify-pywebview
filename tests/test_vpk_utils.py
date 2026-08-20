import os
from unittest.mock import patch

from patch import vpk_utils


def test_dump_metadata_default_behavior(tmp_path):
    target_dir = str(tmp_path / "output")
    os.makedirs(target_dir, exist_ok=True)

    # Mock config.get to return False for opt_out_vpk_metadata
    def mock_get(key, default=None):
        if key == "opt_out_vpk_metadata":
            return False
        return default

    with patch("core.config.get", side_effect=mock_get):
        # Mock shutil.copy and utils.open_utf8 to avoid hitting real steam.inf or mods.json
        with patch("shutil.copy") as _, patch("patch.vpk_utils.utils.open_utf8") as mock_open:
            vpk_utils.dump_metadata(target_dir, mod_name="test_mod")

            # Since mod_name is provided, it should create {mod_name}.txt
            assert os.path.exists(os.path.join(target_dir, "test_mod.txt"))

            # Should have called open_utf8 to write minify_version.txt
            mock_open.assert_any_call(os.path.join(target_dir, "minify_version.txt"), "w")


def test_dump_metadata_opt_out(tmp_path):
    target_dir = str(tmp_path / "output")
    os.makedirs(target_dir, exist_ok=True)

    # Mock config.get to return True for opt_out_vpk_metadata
    def mock_get(key, default=None):
        if key == "opt_out_vpk_metadata":
            return True
        return default

    with patch("core.config.get", side_effect=mock_get):
        with patch("shutil.copy") as mock_copy, patch("patch.vpk_utils.utils.open_utf8") as mock_open:
            vpk_utils.dump_metadata(target_dir, mod_name="test_mod")

            # Since we opted out, metadata should be skipped:
            # {mod_name}.txt should NOT be created, and copy should NOT be called.
            # But minify_version.txt is ALWAYS written regardless of opt_out.
            assert not os.path.exists(os.path.join(target_dir, "test_mod.txt"))
            mock_copy.assert_not_called()
            mock_open.assert_called_once_with(os.path.join(target_dir, "minify_version.txt"), "w")


def _create_test_vpk(tmp_path, files):
    import vpk

    source_dir = tmp_path / "src"
    source_dir.mkdir(exist_ok=True)
    for name, content in files.items():
        (source_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (source_dir / name).write_text(content, encoding="utf-8")

    pak = vpk.new(str(source_dir))
    pak_path = tmp_path / "pak01_dir.vpk"
    pak.save(str(pak_path))
    return str(pak_path)


def test_is_minify_pak_true_with_version_marker(tmp_path):
    pak_path = _create_test_vpk(tmp_path, {"minify_version.txt": "1.13.1", "dota/steam.inf": "x"})
    assert vpk_utils.is_minify_pak(pak_path)


def test_is_minify_pak_false_with_mod_txt_only(tmp_path):
    pak_path = _create_test_vpk(tmp_path, {"Minify Base Attacks.txt": ""})
    assert not vpk_utils.is_minify_pak(pak_path)


def test_is_minify_pak_false_without_marker(tmp_path):
    pak_path = _create_test_vpk(tmp_path, {"dota/steam.inf": "x"})
    assert not vpk_utils.is_minify_pak(pak_path)


def test_is_minify_pak_nonexistent_path():
    assert not vpk_utils.is_minify_pak(os.path.join("nope", "pak99_dir.vpk"))


def test_is_minify_pak_unreadable(tmp_path):
    assert not vpk_utils.is_minify_pak(str(tmp_path))
