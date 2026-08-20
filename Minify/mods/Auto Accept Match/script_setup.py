import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

import conditions
from core import config


def main():
    mod_name = os.path.basename(current_dir)
    config_file = os.path.join(minify_root, "config", f"{mod_name} config.json")
    if os.path.exists(config_file):
        return

    if conditions.workshop_installed:
        return

    precompiled = os.path.join(current_dir, "files", "panorama", "layout", "popups", "popup_accept_match.vxml_c")
    if os.path.exists(precompiled):
        return

    return "Precompiled assets need to be downloaded for this mod (Workshop Tools not detected)."
