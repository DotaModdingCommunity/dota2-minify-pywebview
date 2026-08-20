"""script_uninstall.py — bulk hook that runs for every mod that gets
uninstalled/reverted. Typical use: clean up files the mod created elsewhere.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import output


def main():
    output.add_text("-> Example Mod: script_uninstall.py ran.")
