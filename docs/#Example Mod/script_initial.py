"""script_initial.py — bulk hook that runs for every enabled mod at the very
start of a patch, before anything is extracted. (Runs for all mods, even
`always` ones.)
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import output


def main():
    output.add_text("-> Example Mod: script_initial.py ran.")
