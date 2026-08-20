import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import base, config

IMG_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
VID_EXTENSIONS = (".mp4", ".webm")


def main():
    mod_name = os.path.basename(current_dir)
    config_file = os.path.join(minify_root, "config", f"{mod_name} config.json")
    if os.path.exists(config_file):
        return
    for ext in IMG_EXTENSIONS + VID_EXTENSIONS:
        if os.path.exists(os.path.join(base.config_dir, f"background{ext}")):
            return
    return "Select a background image or video in the mod's settings, or use the default."
