"Dynamic localization handling"

import jsonc
import threading
from typing import Any
from core import base, utils

localization_dict: dict[str, str] = {}

_cache: dict[str, Any] | None = None
_localization_lock = threading.Lock()


def _load() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    try:
        with utils.open_utf8(base.localization_file_dir) as f:
            _cache = jsonc.load(f)
    except (FileNotFoundError, jsonc.JSONDecodeError, OSError):
        _cache = {}
    assert _cache is not None
    return _cache


def load_headless(lang: str = "EN") -> None:
    global localization_dict
    data = _load()
    new_dict = {key: values.get(lang, values.get("EN", key)) for key, values in data.items()}
    with _localization_lock:
        localization_dict = new_dict


def get_available() -> list[str]:
    localization_data = _load()
    sub_headers = set()
    for header in localization_data.values():
        if isinstance(header, dict):
            sub_headers.update(header.keys())
    sorted_langs = sorted(lang for lang in sub_headers if lang != "EN")
    return ["EN"] + sorted_langs
