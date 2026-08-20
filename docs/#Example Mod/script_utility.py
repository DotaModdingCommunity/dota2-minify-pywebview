"""script_utility.py — loaded on demand by a `button`-type setting.

The function name MUST match the setting key ("run_utility" here).
Messages printed with `output.add_text` are shown in the settings modal.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
sys.path.insert(0, minify_root)

from core import config, output

mod_name = os.path.basename(current_dir)


def run_utility():
    settings = config.get_mod_config(mod_name)
    output.add_text(
        "-> Example Mod utility ran.\n   Greeting: {}\n   Ignored items: {}",
        settings.get("greeting_text", ""),
        settings.get("ignored_items", []),
    )
