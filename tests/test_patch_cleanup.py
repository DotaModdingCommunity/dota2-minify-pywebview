import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../Minify")))

import patch


def test_remove_staged_mod_files_removes_mods_top_level_items(tmp_path):
    src = tmp_path / "mod_files"
    dest = tmp_path / "output"
    os.makedirs(os.path.join(src, "subdir"))
    with open(os.path.join(src, "file.txt"), "w") as f:
        f.write("mod")
    with open(os.path.join(src, "subdir", "nested.txt"), "w") as f:
        f.write("nested")

    os.makedirs(dest)
    with open(os.path.join(dest, "file.txt"), "w") as f:
        f.write("mod")
    os.makedirs(os.path.join(dest, "subdir"))
    with open(os.path.join(dest, "subdir", "nested.txt"), "w") as f:
        f.write("nested")
    with open(os.path.join(dest, "other_mod.txt"), "w") as f:
        f.write("other")

    patch._remove_staged_mod_files(str(src), str(dest))

    assert not os.path.exists(os.path.join(dest, "file.txt"))
    assert not os.path.exists(os.path.join(dest, "subdir"))
    assert os.path.exists(os.path.join(dest, "other_mod.txt"))


def test_remove_staged_mod_files_keeps_dest_when_source_missing(tmp_path):
    dest = tmp_path / "output"
    os.makedirs(dest)
    with open(os.path.join(dest, "keep.txt"), "w") as f:
        f.write("keep")

    patch._remove_staged_mod_files(str(tmp_path / "missing"), str(dest))

    assert os.path.exists(os.path.join(dest, "keep.txt"))
