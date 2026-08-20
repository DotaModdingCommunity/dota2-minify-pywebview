import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
mod_name = os.path.basename(current_dir)
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
if os.getcwd() != minify_root:
    os.chdir(minify_root)

if minify_root not in sys.path:
    sys.path.insert(0, minify_root)

# isort: split

import shutil

import requests
from core import config, fs, log, output, steam

dota_itembuilds_path = os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota", "itembuilds")
odg_bkup_path = os.path.join(minify_root, "backup", "OpenDotaGuides Guides")
odg_latest = "https://github.com/Egezenn/OpenDotaGuides/releases/latest/download/itembuilds.zip"
odg_release_api = "https://api.github.com/repos/Egezenn/OpenDotaGuides/releases/latest"
zip_path = os.path.join(current_dir, "files", "OpenDotaGuides.zip")
temp_dump_path = os.path.join(current_dir, "files", "temp")


def _latest_release_tag():
    try:
        response = requests.get(odg_release_api, timeout=10)
        if response.status_code == 200:
            return response.json().get("tag_name")
    except Exception as e:
        log.write_warning(f"Connection error while checking for guide updates: {e}")
    return None


def main():
    tag = _latest_release_tag()
    if tag is None:
        output.add_text("&connection_error", msg_type="warning")
        return

    stored = config.get_mod_config(mod_name).get("release_tag")
    if tag == stored:
        output.add_text(f"Guides are up to date ({tag}).", msg_type="success")
        return

    fs.remove_path(zip_path)

    try:
        response = requests.get(odg_latest, timeout=15)
    except Exception as e:
        log.write_warning(f"Connection error while fetching guides: {e}")
        output.add_text("&connection_error", msg_type="warning")
        return
    if response.status_code == 200:
        with open(zip_path, "wb") as file:
            file.write(response.content)
        fs.backup_directory(dota_itembuilds_path, odg_bkup_path)

        shutil.unpack_archive(zip_path, temp_dump_path, format="zip")
        for file in os.listdir(temp_dump_path):
            shutil.copy(
                os.path.join(temp_dump_path, file),
                os.path.join(dota_itembuilds_path, file),
            )
        fs.remove_path(temp_dump_path, zip_path)

        mod_config = config.get_mod_config(mod_name)
        mod_config["release_tag"] = tag
        config.save_mod_config(mod_name, mod_config)
    else:
        log.write_warning(f"Failed to fetch guides. Status code: {response.status_code}")
        output.add_text("&connection_error", msg_type="warning")


if __name__ == "__main__":
    main()
