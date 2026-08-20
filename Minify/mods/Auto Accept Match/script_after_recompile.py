import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
if os.getcwd() != minify_root:
    os.chdir(minify_root)

if minify_root not in sys.path:
    sys.path.insert(0, minify_root)

# isort: split

import conditions
import requests
from core import constants, fs, output

before_workshop_req = "https://raw.githubusercontent.com/Egezenn/dota2-minify/Minify-v1.11.2/mods/Auto%20Accept%20Match/files/panorama/layout/popups/popup_accept_match.vxml_c"

_TARGET = ("panorama", "layout", "popups", "popup_accept_match.vxml_c")


def main():
    if conditions.workshop_installed:
        return
    try:
        response = requests.get(before_workshop_req, timeout=15)
        if response.status_code != 200 or response.headers.get("content-type", "").startswith("text/html"):
            output.add_text(
                "Failed to download the precompiled Auto Accept Match file; continuing without it.", msg_type="warning"
            )
            return
        target = os.path.join(constants.minify_dota_compile_output_path, *_TARGET)
        fs.create_dirs(os.path.dirname(target))
        with open(target, "wb") as file:
            file.write(response.content)
    except Exception:
        output.add_text(
            "Failed to download the precompiled Auto Accept Match file; continuing without it.", msg_type="warning"
        )
