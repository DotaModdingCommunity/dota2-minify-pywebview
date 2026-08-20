"""script_setup.py — shown in the settings modal the first time a mod with a
settings schema is configured. Return a string to display guidance; return
None once the user has configured the mod.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import base


def main():
    config_file = os.path.join(base.config_dir, f"{os.path.basename(current_dir)} config.json")
    if os.path.exists(config_file):
        return None
    return "Explore the Example Mod settings — every input type and mod feature is demonstrated."
