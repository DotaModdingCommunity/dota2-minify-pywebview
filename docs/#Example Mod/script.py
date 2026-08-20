"""script.py — runs once during every patch of this mod.

Demonstrates reading the mod's settings via `config.get_mod_config`.
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
if os.getcwd() != minify_root:
    os.chdir(minify_root)

if minify_root not in sys.path:
    sys.path.insert(0, minify_root)

from core import base, config, output
from patch import manifest_utils

mod_name = os.path.basename(current_dir)


def _ensure_default_config() -> None:
    """Write schema defaults if no config file exists yet.

    The `@key:` gates in styling.css and blacklist.txt treat a missing
    setting as enabled, so a fresh (unconfigured) mod would apply every
    gated block. Persisting the defaults up-front keeps the blacklist
    blocks, which default to off, harmless until the user opts in.
    """
    if config.get_mod_config(mod_name):
        return
    manifest = manifest_utils.get_mod(os.path.join(base.mods_dir, mod_name))
    defaults = {s["key"]: s.get("default") for s in manifest.get("settings", []) if s.get("key")}
    if defaults:
        config.save_mod_config(mod_name, defaults)


def main():
    _ensure_default_config()
    settings = config.get_mod_config(mod_name)
    output.add_text(
        "-> Example Mod: greeting = '{}', ignored items = {}",
        settings.get("greeting_text", ""),
        settings.get("ignored_items", []),
    )
