import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import config


def main():
    config_file = os.path.join(minify_root, "config", f"{os.path.basename(current_dir)} config.json")
    if os.path.exists(config_file):
        return
    return "Configure which UI elements to hide or modify in the mod's settings."
