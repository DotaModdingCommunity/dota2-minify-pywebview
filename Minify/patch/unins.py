import os
import re
import time

import helper
from core import base, constants, fs, output, steam
from patch import vpk_utils
from ui import modal_shared

PAK_PATTERN = re.compile(r"^pak\d{2}_dir\.vpk$")

from patch import vpk_utils


def _uninstall(progress: bool = False) -> None:
    output.clean()
    if progress:
        modal_shared.show_progress(["&status_uninstalling"])
        time.sleep(0.05)
        modal_shared.set_progress(20, "&status_scanning_outputs")

    for path in constants.minify_dota_possible_language_output_paths:
        if os.path.isdir(path):
            maps_vpk_path = os.path.join(path, "maps", "dota.vpk")
            if os.path.exists(maps_vpk_path):
                fs.remove_path(os.path.join(path, "maps"))
            for item in os.listdir(path):
                pak_path = os.path.join(path, item)
                if os.path.isfile(pak_path) and PAK_PATTERN.fullmatch(item):
                    if vpk_utils.is_minify_pak(pak_path):
                        fs.remove_path(pak_path)

    if progress:
        modal_shared.set_progress(60, "&status_removing_launch_options")
    steam.remove_minify_lang()

    if progress:
        modal_shared.set_progress(80, "&status_running_uninstall_scripts")
    helper.bulk_exec_script("uninstall")

    output.add_text("&mods_removed_terminal")
    if progress:
        modal_shared.set_progress(100, "&status_done")
        modal_shared.hide_progress()


def uninstall() -> None:
    if base.HEADLESS:
        _uninstall(progress=False)
        return

    from ui import actions

    with actions.interactive_lock():
        _uninstall(progress=True)

    from ui import output_bridge

    output_bridge.send_js("window.__uninstallEnd()")


def wipe() -> None:
    from ui import actions

    with actions.interactive_lock():
        output.clean()
        _uninstall(progress=True)
        for path in constants.minify_dota_possible_language_output_paths:
            if os.path.isdir(path):
                for item in os.listdir(path):
                    if PAK_PATTERN.fullmatch(item):
                        fs.remove_path(os.path.join(path, item))
                maps_dir = os.path.join(path, "maps", "dota.vpk")
                if os.path.exists(maps_dir):
                    fs.remove_path(os.path.join(path, "maps"))
