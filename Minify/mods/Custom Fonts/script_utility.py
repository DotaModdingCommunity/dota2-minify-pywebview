import os
import shutil
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
mod_name = os.path.basename(current_dir)
minify_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
if os.getcwd() != minify_root:
    os.chdir(minify_root)

if minify_root not in sys.path:
    sys.path.insert(0, minify_root)

from core import base, config
from ui import dialogs, modal_shared

FONT_EXTENSIONS = (".ttf", ".otf")

# Magic bytes for the first 4 bytes of a font file (SFNT-based formats).
_FONT_MAGIC = {
    b"\x00\x01\x00\x00": ".ttf",  # TrueType
    b"true": ".ttf",  # TrueType (Apple)
    b"OTTO": ".otf",  # OpenType/CFF
    b"ttcf": ".ttc",  # TrueType collection (not supported)
}


def _detect_font_type(path):
    try:
        with open(path, "rb") as f:
            header = f.read(4)
    except OSError:
        return None
    return _FONT_MAGIC.get(header)


def place_font():
    saved_path = config.get_mod_config(mod_name).get("font_file", "") or ""
    source = saved_path if saved_path and os.path.exists(saved_path) else ""

    if not source:
        source = dialogs.select_file(
            file_types="Fonts (*.ttf;*.otf)",
            directory=os.getcwd(),
        )

    if not source:
        return

    actual_ext = _detect_font_type(source)
    if actual_ext not in FONT_EXTENSIONS:
        modal_shared.show(
            title="Unsupported Format",
            messages=[f"The selected file has an unsupported format or invalid magic bytes. Detected: {actual_ext}"],
            buttons=[{"label": "OK", "width": 100}],
        )
        return

    dest_path = os.path.join(base.config_dir, f"font{actual_ext}")

    try:
        shutil.copy2(source, dest_path)
    except Exception as e:
        modal_shared.show(
            title="Error", messages=[f"Failed to copy file:\n{e}"], buttons=[{"label": "OK", "width": 100}]
        )
        return

    mod_config = config.get_mod_config(mod_name)
    mod_config["font_file"] = source
    config.save_mod_config(mod_name, mod_config)

    modal_shared.show(
        title="Font Placed",
        messages=[f"Font copied to {os.path.basename(dest_path)}."],
        buttons=[{"label": "OK", "width": 100}],
    )
