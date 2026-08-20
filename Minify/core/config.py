"""
JSON(C) config files

Interactions with main config and mod configs
"""

import copy
import glob
import os
import shutil
import threading
import time
from typing import Any

import jsonc

from core import base, utils

_config_cache: dict[str, Any] | None = None
_config_lock = threading.Lock()


def read_json_file(path: str) -> dict[str, Any]:
    try:
        with utils.open_utf8(path, errors="replace") as file:
            return jsonc.load(file)
    except FileNotFoundError:
        return {}
    except jsonc.JSONDecodeError:
        from core import log

        log.write_warning(f"Corrupted JSON file: {path}")
        try:
            shutil.copy2(path, path + ".corrupt")
            log.write_warning(f"Corrupt config file backed up to {path}.corrupt")
        except OSError:
            pass
        return {}


def write_json_file(path: str, data: dict[str, Any]) -> bool:
    from core import log

    def _sweep_stale_tmp() -> None:
        for stale in glob.glob(f"{path}.tmp.*"):
            try:
                os.remove(stale)
            except OSError:
                pass

    def _dump(dest: str) -> None:
        with utils.open_utf8(dest, "w") as file:
            jsonc.dump(data, file, indent=2)

    tmp = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        _dump(tmp)
        try:
            os.replace(tmp, path)
            _sweep_stale_tmp()
            return True
        except OSError:
            # os.replace fails on Windows whenever the destination is held open
            # (concurrent writer, AV scan, read-only attribute). Retry briefly
            # to ride out transient locks, then fall back to a truncate-write.
            for _ in range(3):
                time.sleep(0.1)
                try:
                    os.replace(tmp, path)
                    _sweep_stale_tmp()
                    return True
                except OSError:
                    continue
            _dump(path)
            _sweep_stale_tmp()
            return True
    except (OSError, TypeError, ValueError) as e:
        log.write_warning(f"Failed to write {path}: {e}")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False


def get(key: str, default_value: Any = None) -> Any:
    global _config_cache
    with _config_lock:
        if _config_cache is None:
            _config_cache = read_json_file(base.main_config_file_dir)
        value = _config_cache.get(key, default_value)
        # Return copies of mutable values so callers mutating the result
        # (e.g. `modconf` in place) can't corrupt the cached config or race
        # concurrent readers iterating the same live dict/list.
        if isinstance(value, (dict, list)):
            return copy.deepcopy(value)
        return value


def set(key: str, value: Any) -> Any:
    global _config_cache
    with _config_lock:
        if _config_cache is None:
            _config_cache = read_json_file(base.main_config_file_dir)
        _config_cache[key] = value
        write_json_file(base.main_config_file_dir, _config_cache)
    return value


_mod_config_cache: dict[str, dict[str, Any]] = {}


def reset_all() -> None:
    """Reset config to schema defaults, preserving the Steam paths the app uses.

    Also clears per-mod config files (mod settings and mod-stored paths).
    """
    global _config_cache, _mod_config_cache
    with _config_lock:
        old = _config_cache if _config_cache is not None else read_json_file(base.main_config_file_dir)
        data = {key: spec["default"] for key, spec in _CONFIG_SCHEMA.items()}
        for key in ("steam_root", "steam_library"):
            if key in old:
                data[key] = old[key]
        write_json_file(base.main_config_file_dir, data)
        _config_cache = data
    _mod_config_cache.clear()
    try:
        for fname in os.listdir(base.config_dir):
            if fname.endswith(" config.json"):
                os.remove(os.path.join(base.config_dir, fname))
    except OSError:
        from core import log

        log.write_warning("Failed to clear some per-mod config files")


def get_locale(default: str = "english") -> str:
    from core import constants

    return constants.resolve_locale(get("output_locale", default))


def get_mod_config(mod_name: str) -> dict[str, Any]:
    if mod_name in _mod_config_cache:
        return _mod_config_cache[mod_name]
    path = os.path.join(base.config_dir, f"{mod_name} config.json")
    data = read_json_file(path)
    _mod_config_cache[mod_name] = data
    return data


def save_mod_config(mod_name: str, data: dict[str, Any]) -> None:
    path = os.path.join(base.config_dir, f"{mod_name} config.json")
    write_json_file(path, data)
    _mod_config_cache[mod_name] = data


def remove_mod_config(mod_name: str) -> None:
    """Delete a mod's config file so it is treated as unconfigured (re-prompts in setup)."""
    with _config_lock:
        _mod_config_cache.pop(mod_name, None)
    try:
        os.remove(os.path.join(base.config_dir, f"{mod_name} config.json"))
    except FileNotFoundError:
        pass


_CONFIG_SCHEMA = {
    "locale": {
        "type": str,
        "default": "EN",
        "choices": lambda: __import__("ui.localization", fromlist=["get_available"]).get_available(),
    },
    "output_locale": {
        "type": str,
        "default": "english",
        "choices": lambda: __import__("core.constants", fromlist=["minify_output_list"]).minify_output_list,
    },
    "steam_root": {"type": str, "default": ""},
    "steam_library": {"type": str, "default": ""},
    "steam_ids": {"type": list, "default": []},
    "steam_id": {"type": str, "default": ""},
    "opt_into_rcs": {"type": bool, "default": False},
    "launch_dota_after_patch": {"type": bool, "default": False},
    "kill_self_after_patch": {"type": bool, "default": False},
    "patch_on_updates": {"type": bool, "default": False},
    "patch_on_launch": {"type": bool, "default": False},
    "apply_for_all": {"type": bool, "default": True},
    "d2pfx_filter_nsfw": {"type": bool, "default": True},
    "d2pfx_filter_anime": {"type": bool, "default": False},
    "d2pfx_auto_refresh_catalogue": {"type": bool, "default": True},
    "opt_out_vpk_metadata": {"type": bool, "default": False},
    "settings_advanced": {"type": bool, "default": False},
    "setup_complete": {"type": bool, "default": False},
    "welcome_shown": {"type": bool, "default": False},
    "workshop_modal_shown": {"type": bool, "default": False},
    "ignore_update": {"type": str, "default": ""},
    "custom_compile_path": {"type": str, "default": ""},
    "debug_env": {"type": bool, "default": False},
    "debug_disable_workshop": {"type": bool, "default": False},
    "debug_simulate_offline": {"type": bool, "default": False},
    "debug_simulate_no_steam": {"type": bool, "default": False},
    "announcements_seen": {"type": list, "default": []},
    "ui_zoom": {"type": float, "default": 1.0},
    "modconf": {"type": dict, "default": {}},
    "d2pfx_selected_variants": {"type": dict, "default": {}},
}


def validate() -> bool:
    """Validate config against schema, apply defaults for missing/invalid keys."""
    from core import log

    data = read_json_file(base.main_config_file_dir)
    if not isinstance(data, dict):
        data = {}
        log.write_warning("Config is not a dict, resetting")

    changed = False
    for key, spec in _CONFIG_SCHEMA.items():
        if key not in data:
            data[key] = spec["default"]
            changed = True
            continue
        val = data[key]
        expected_type = spec["type"]
        if expected_type is bool and not isinstance(val, bool):
            if isinstance(val, str):
                data[key] = val.lower() in ("true", "1", "yes")
            elif isinstance(val, int):
                data[key] = bool(val)
            else:
                data[key] = spec["default"]
            changed = True
        elif expected_type is int and not isinstance(val, int):
            try:
                data[key] = int(val)
            except (ValueError, TypeError):
                data[key] = spec["default"]
            changed = True
        elif expected_type is list and not isinstance(val, list):
            data[key] = spec["default"]
            changed = True
        elif expected_type is dict and not isinstance(val, dict):
            data[key] = spec["default"]
            changed = True
        elif expected_type is str and not isinstance(val, str):
            data[key] = str(val)
            changed = True
        if "choices" in spec:
            try:
                choices = spec["choices"]() if callable(spec["choices"]) else spec["choices"]
                if data[key] not in choices:
                    data[key] = spec["default"]
                    changed = True
            except Exception:
                pass

    if changed:
        write_json_file(base.main_config_file_dir, data)
        global _config_cache
        with _config_lock:
            _config_cache = None
    return True
