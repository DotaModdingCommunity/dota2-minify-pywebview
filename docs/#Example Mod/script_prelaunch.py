"""script_prelaunch.py — bulk hook that runs right before the game is launched
(when launching via Minify). Runs for every enabled mod, like the other bulk
hooks, and is also triggered by the CLI when no patch was needed.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import output


def main():
    output.add_text("-> Example Mod: script_prelaunch.py ran.")
