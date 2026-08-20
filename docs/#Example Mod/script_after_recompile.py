"""script_after_recompile.py — bulk hook that runs after raw assets have been
recompiled (Resource Compiler pass). Typical use: post-process compiled assets.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import output


def main():
    output.add_text("-> Example Mod: script_after_recompile.py ran.")
