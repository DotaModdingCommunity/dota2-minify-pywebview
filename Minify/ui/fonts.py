import os
import subprocess

from core import base


def _find_font_linux(font_name: str) -> str | None:
    try:
        result = subprocess.run(["fc-match", "-f", "%{file}", font_name], capture_output=True, text=True, check=True)
        if result.stdout and os.path.exists(result.stdout.strip()):
            return result.stdout.strip()
    except Exception:
        pass

    common_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.expanduser("~/.fonts"),
        os.path.expanduser("~/.local/share/fonts"),
    ]
    for d in common_dirs:
        for root, _, files in os.walk(d):
            if font_name in files:
                return os.path.join(root, font_name)
    return None


def _normalize_filename(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    return stem.lower().replace(" ", "").replace("-", "").replace("_", "")


def find_system_font(font_name: str) -> str | None:
    normalized = font_name.lower().replace(" ", "").replace("-", "").replace("_", "")

    if base.is_win:
        windir = os.environ.get("windir", "C:\\Windows")
        font_dirs = [os.path.join(windir, "Fonts")]
    elif base.is_linux:
        result = _find_font_linux(font_name)
        if result:
            return result
        font_dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ]
    elif base.is_mac:
        font_dirs = ["/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    else:
        return None

    for d in font_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower().endswith((".ttf", ".otf")) and normalized in _normalize_filename(f):
                    return os.path.join(root, f)
    return None
