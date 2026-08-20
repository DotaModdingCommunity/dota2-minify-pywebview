"""script_after_patch.py — bulk hook that runs after the patch is applied and
the custom pak is built. Typical use: wrap-up tasks or launching the game.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import output


def main():
    output.add_text("-> Example Mod: script_after_patch.py ran.")
