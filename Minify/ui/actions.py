"""
All JS-facing application logic.
Handlers registered in _API_HANDLERS; module __getattr__ wraps each
with an error envelope ({"ok": bool, "data": ..., "error": ...}).
"""

import base64
import contextlib
import functools
import json
import os
import re
import shutil
import threading
import urllib.parse
import webbrowser
from typing import Any, Callable

import conditions
import helper
import webview
from core import base, config, constants, fs, log, mods_shared, output, steam, utils
from patch import manifest_utils
from ui import localization, modals

# ── Init guard ──────────────────────────────────────────────────────────

_init_done = False
_EARLY_ALLOW = frozenset(
    {
        "get_app_info",
        "get_steam_path_state",
        "resolve_steam_path",
    }
)

# ── Lock state ──────────────────────────────────────────────────────────

_locked = False
_lock_owner: str | None = None
_lock_depth = 0
_lock_mutex = threading.Lock()
_lock_tls = threading.local()


def is_locked() -> bool:
    with _lock_mutex:
        return _locked


def _set_locked(val: bool, owner: str | None = None, notify_ui: bool = True):
    global _locked, _lock_owner, _lock_depth
    token = owner or getattr(_lock_tls, "token", None) or f"anon-{threading.get_ident()}"
    with _lock_mutex:
        if val:
            if _locked and _lock_owner is not None and _lock_owner != token:
                raise RuntimeError("Already running")
            _locked = True
            _lock_depth += 1
            if _lock_owner is None:
                _lock_owner = token
        else:
            if _lock_owner is not None and _lock_owner != token:
                return
            _lock_depth = max(0, _lock_depth - 1)
            if _lock_depth == 0:
                _locked = False
                _lock_owner = None
    if notify_ui:
        _notify_locked(val)


def _notify_locked(val: bool):
    from ui import output_bridge

    output_bridge.send_js(f"window.__setLocked({str(val).lower()})")


@contextlib.contextmanager
def interactive_lock(owner: str | None = None):
    _set_locked(True, owner)
    try:
        yield
    finally:
        _set_locked(False, owner)


# ── Mod state ───────────────────────────────────────────────────────────


# ── Reusable runner ─────────────────────────────────────────────────────


def _run_locked(target: Callable[..., Any], *args: Any) -> None:
    """Lock, start daemon thread, unlock on thread-creation failure."""
    global _locked, _lock_owner, _lock_depth
    token = f"run-{threading.get_ident()}-{id(target)}"
    with _lock_mutex:
        if _locked:
            raise RuntimeError("Already running")
        _locked = True
        _lock_owner = token
        _lock_depth = 1
    _notify_locked(True)

    def _wrapper():
        # Adopt the owner token so nested interactive_lock() calls inside
        # the target (e.g. patcher()) are recognized as the same operation
        # instead of being rejected as a foreign acquirer.
        _lock_tls.token = token
        try:
            target(*args)
        finally:
            _lock_tls.token = None
            _set_locked(False, token)

    threading.Thread(target=_wrapper, daemon=True).start()


# ── Internal helpers (not API-visible) ──────────────────────────────────

_MAX_PREVIEW_BYTES = 5 * 1024 * 1024


def _run_patch():
    import patch as patch_module
    from core import log
    from ui import modal_shared, output_bridge

    modal_shared.show_progress(["&status_patching"])
    try:
        completed = patch_module.patcher()
        if completed:
            output_bridge.send_js("window.__patchEnd()")
        else:
            output_bridge.send_js("window.__patchCancelled()")
    except Exception as e:
        log.write_crashlog(header="Patch failed")
        log.write_warning(f"Patch failed: {e}")
        output_bridge.send_js(f"window.__patchError({json.dumps(str(e))})")
    finally:
        modal_shared.hide_progress()
        _set_locked(False)


def _iter_available_mods():
    mods_shared.scan_mods()
    for mod in list(mods_shared.visually_available_mods):
        mod_path = os.path.join(base.mods_dir, mod)
        if mod.endswith(".vpk"):
            yield mod, mod_path, True, False, False, False, {}
            continue
        cfg = manifest_utils.get_mod(mod_path)
        if cfg.get("browser", {}).get("browser") == "d2pfx":
            continue
        unsupported = False
        if version_req := cfg.get("version"):
            if not manifest_utils.is_version_at_least(base.VERSION, version_req):
                unsupported = True
        if not conditions.workshop_installed and not unsupported and not cfg.get("skip_workshop_check", False):
            if any(os.path.exists(os.path.join(mod_path, m)) for m in conditions.workshop_required_methods):
                unsupported = True
        yield mod, mod_path, False, bool(cfg.get("always", False)), unsupported, cfg.get("version", ""), cfg


# ── D2PFX helpers ───────────────────────────────────────────────────────

_d2pfx_dl_locks: dict[str, threading.Lock] = {}
_d2pfx_dl_locks_lock = threading.Lock()
_d2pfx_data_manager = None
_d2pfx_lock = threading.Lock()


def _d2pfx_dl_lock(key: str) -> threading.Lock:
    with _d2pfx_dl_locks_lock:
        if key not in _d2pfx_dl_locks:
            _d2pfx_dl_locks[key] = threading.Lock()
        return _d2pfx_dl_locks[key]


_preview_warned: set = set()


def _d2pfx_load_preview(dm: Any, cat_id: str, filename: str) -> str | None:
    lock_key = f"{cat_id}:{filename}"
    clean_filename = filename.replace(".webp", ".jpg")
    lock = _d2pfx_dl_lock(lock_key)
    with lock:
        cat_preview_dir = os.path.join(dm.previews_dir, utils.sanitize_win_path(cat_id))
        fs.create_dirs(cat_preview_dir)
        local_path = os.path.join(cat_preview_dir, utils.sanitize_win_path(clean_filename))
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            pass
        else:
            encoded_cat = urllib.parse.quote(cat_id)
            encoded_file = urllib.parse.quote(clean_filename)
            url = dm.get_preview_url(encoded_cat, encoded_file)
            if not fs.download_file(url, local_path, log_level="warning", dedupe_set=_preview_warned):
                root_url = url.replace(f"previews/{encoded_cat}/", "previews/")
                if root_url != url:
                    fs.download_file(root_url, local_path, log_level="warning", dedupe_set=_preview_warned)
    if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
        return None
    try:
        with open(local_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        if filename.endswith(".mp4"):
            mime = "video/mp4"
        elif filename.endswith(".webm"):
            mime = "video/webm"
        else:
            mime = "image/png" if filename.endswith(".png") else "image/jpeg"
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def _d2pfx_bg_preload_category(dm: Any, cat_id: str, max_concurrent: int = 4) -> None:
    mods = dm.get_mods(cat_id)
    previews: list[str] = []
    for m in mods:
        for style in m.get("styles", []) if isinstance(m.get("styles"), list) else []:
            if style.get("preview"):
                previews.append(style["preview"])
        if m.get("preview"):
            previews.append(m["preview"])
    sem = threading.Semaphore(max_concurrent)

    def _worker(filename: str) -> None:
        try:
            _d2pfx_load_preview(dm, cat_id, filename)
        finally:
            sem.release()

    for filename in previews:
        sem.acquire()
        threading.Thread(target=_worker, args=(filename,), daemon=True).start()


def _get_d2pfx_dm() -> Any:
    global _d2pfx_data_manager
    if _d2pfx_data_manager is None:
        with _d2pfx_lock:
            if _d2pfx_data_manager is None:
                from browsers.d2pfx.data import DataManager

                dm = DataManager()
                _d2pfx_data_manager = dm

                def _load_dm(dm: Any = dm) -> None:
                    dm.load()
                    if dm.is_loaded():
                        from ui import output_bridge

                        output_bridge.send_js("window.__d2pfxLoaded()")

                threading.Thread(target=_load_dm, daemon=True).start()
    return _d2pfx_data_manager


# ── Path resolution ─────────────────────────────────────────────────────

_resolving_paths = False
_resolve_paths_lock = threading.Lock()


def _do_resolve_paths():
    global _resolving_paths
    from core import log

    try:
        steam.ensure_paths_resolved()
        if steam.ROOT:
            constants.init_paths()
    except Exception as e:
        log.write_warning(f"Path resolution failed: {e}")
    finally:
        _resolving_paths = False


# ── Dependency download (background) ────────────────────────────────────


def _download_deps_background():
    import conditions
    from core import config as _config
    from core import log
    from ui import modal_shared, output_bridge

    _set_locked(True, notify_ui=False)
    try:
        debug = _config.get("debug_env", False)
        needs_download = not conditions.check_binaries()
        if not needs_download and debug:
            needs_download = True
        if needs_download:
            modal_shared.show_progress(["&deps_downloading"])
            output_bridge.send_js("window.__setDepsDownloading(true)")
        conditions.resolve_dependencies(
            progress_callback=(lambda r, s, *a: modal_shared.set_progress(r, s, *a)) if needs_download else None
        )
        if needs_download:
            modal_shared.hide_progress()
            output_bridge.send_js("window.__setDepsDownloading(false)")
        if not conditions.check_binaries():
            modal_shared.show(
                title="&deps_dl_fail_title",
                messages=[
                    "&deps_dl_fail_msg1",
                    "&deps_dl_fail_msg2",
                    "&deps_dl_fail_msg3",
                    "&deps_dl_fail_msg4",
                ],
                buttons=["OK"],
            )
    except Exception as e:
        output_bridge.send_js("window.__setDepsDownloading(false)")
        log.write_warning(f"Dependency download failed: {e}")
    finally:
        _set_locked(False, notify_ui=False)


# ── Complex API handlers (kept as named for readability) ────────────────


def _get_mods() -> list[dict[str, Any]]:
    result = []
    for mod, mod_path, is_vpk, always_val, unsupported, _version, cfg in _iter_available_mods():
        has_notes = False
        has_preview = False
        if not is_vpk:
            notes_p = os.path.join(mod_path, "notes.md")
            has_notes = os.path.exists(notes_p) and os.path.getsize(notes_p) > 0
            for ext in ("preview.png", "preview.jpg"):
                if os.path.exists(os.path.join(mod_path, ext)):
                    has_preview = True
                    break
        result.append(
            {
                "name": mod[:-4] if is_vpk else mod,
                "raw_name": mod,
                "enabled": (
                    config.get("output_locale", "english") in ("english", "minify")
                    if always_val and mod == "#English Fix"
                    else (not unsupported)
                    if always_val
                    else bool(mods_shared.get_state(mod))
                ),
                "always": always_val,
                "unsupported": unsupported,
                "hasNotes": has_notes,
                "hasPreview": has_preview,
                "version": cfg.get("version", "") if not is_vpk else "",
                "tags": cfg.get("tags", []) if not is_vpk else [],
                "status": cfg.get("status", "working") if not is_vpk else "working",
                "hasSettings": bool(cfg.get("settings", [])) if not is_vpk else False,
                "socialLinks": cfg.get("social_links", {}) if not is_vpk else {},
                "author": cfg.get("author", "") if not is_vpk else "",
            }
        )
    return result


def _get_mod_preview(mod: str) -> str | None:
    mod_path = os.path.join(base.mods_dir, mod)
    for ext in ("preview.png", "preview.jpg"):
        p = os.path.join(mod_path, ext)
        if os.path.exists(p):
            if os.path.getsize(p) > _MAX_PREVIEW_BYTES:
                output.add_text("&preview_too_large_mod", mod, os.path.getsize(p), msg_type="warning")
                return None
            mime = "image/png" if ext.endswith(".png") else "image/jpeg"
            try:
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f"data:{mime};base64,{b64}"
            except Exception:
                return None
    return None


_PREVIEW_FILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm")
_PREVIEW_FILE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}


def _get_mod_file_preview(_mod: str, file_base: str) -> str | None:
    """Base64 data URL of a user-supplied config file (e.g. `background.png`)."""
    for ext in _PREVIEW_FILE_EXTENSIONS:
        p = os.path.join(base.config_dir, f"{file_base}{ext}")
        if not os.path.exists(p):
            continue
        size = os.path.getsize(p)
        if size > _MAX_PREVIEW_BYTES:
            output.add_text("&preview_too_large_file", os.path.basename(p), size, msg_type="warning")
            return None
        try:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f"data:{_PREVIEW_FILE_MIME[ext]};base64,{b64}"
        except Exception:
            return None
    return None


def _get_mod_notes_html(mod: str) -> str | None:
    notes_p = os.path.join(base.mods_dir, mod, "notes.md")
    if not os.path.exists(notes_p):
        return None
    with utils.open_utf8(notes_p) as f:
        raw_notes = f.read()
    user_locale = config.get("locale", "EN").upper()
    parts = re.split(r"<!-- LANG:([\w-]+) -->", raw_notes)
    if len(parts) > 1:
        sections = {}
        for i in range(1, len(parts), 2):
            lang = parts[i].upper()
            content = parts[i + 1].strip()
            sections[lang] = content
        return sections.get(user_locale, sections.get("EN", ""))
    return raw_notes.strip()


def _reset_mod_settings(mod: str) -> dict[str, Any]:
    """Delete a mod's config so it re-prompts in setup; return its manifest defaults."""
    config.remove_mod_config(mod)
    settings = manifest_utils.get_mod(os.path.join(base.mods_dir, mod)).get("settings", [])
    return {s["key"]: s.get("default") for s in settings}


def _reset_all_mod_settings() -> None:
    """Delete every per-mod config file so all mods re-prompt in setup. Global config untouched."""
    for fname in os.listdir(base.config_dir):
        if fname.endswith(" config.json"):
            config.remove_mod_config(fname[: -len(" config.json")])


def _get_settings():
    schema_global = []
    for opt in _SETTINGS:
        entry = {k: v for k, v in opt.items() if k != "items_getter"}
        if "items_getter" in opt:
            raw = opt["items_getter"]()
            if opt.get("type") == "accounts":
                entry["items"] = raw if raw else []
            elif raw and isinstance(raw[0], dict):
                entry["items"] = [f"{x['id']} - {x['name']}" for x in raw]
            else:
                entry["items"] = raw if raw else ["(No accounts found)"]
        schema_global.append(entry)
    values_global = {opt["key"]: config.get(opt["key"], opt["default"]) for opt in _SETTINGS}
    values_global["ui_zoom"] = _clamp_zoom(values_global["ui_zoom"])
    if not values_global.get("steam_ids") and config.get("steam_id"):
        values_global["steam_ids"] = [config.get("steam_id")]
    return {
        "schema": {"global": schema_global, "mods": {}},
        "values": {"global": values_global, "mods": {}},
        "showAdvanced": config.get("settings_advanced", False),
    }


def _save_settings(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Invalid settings payload: expected object")
    global_vals = data.get("global", {})
    for opt in _SETTINGS:
        key = opt["key"]
        if key in global_vals:
            val = global_vals[key]
            if key == "ui_zoom":
                val = _clamp_zoom(val)
            elif opt["type"] == "checkbox":
                val = bool(val)
            elif opt["type"] == "inputbox":
                val = str(val)
            config.set(key, val)
    if "showAdvanced" in data:
        config.set("settings_advanced", bool(data["showAdvanced"]))


def _run_mod_utility(mod: str, function_name: str):
    script_path = os.path.join(base.mods_dir, mod, "script_utility.py")
    captured = []

    def capture(text_or_id: str, *args: Any, msg_type: str | None = None, **_kwargs: Any) -> None:
        text = text_or_id
        if text_or_id.startswith("&"):
            text = localization.localization_dict.get(text_or_id.replace("&", ""), text_or_id)
        if args:
            text = text.format(*args)
        captured.append({"text": text, "type": msg_type})

    with output.capture_thread(capture):
        helper.exec_script_function(script_path, mod, function_name)
    return captured


def _set_language(lang: str):
    localization.load_headless(lang)
    config.set("locale", lang)


def _resolve_steam_path():
    global _resolving_paths
    if steam.ROOT:
        return {"path_known": True}
    with _resolve_paths_lock:
        if not _resolving_paths:
            _resolving_paths = True
            threading.Thread(target=_do_resolve_paths, daemon=True).start()
    return {"path_known": False}


def _get_app_info():
    return {
        "version": base.VERSION,
        "title": base.TITLE,
        "discord": base.discord,
        "telegram": base.telegram,
        "github_io": base.github_io,
        "output_list": constants.minify_output_list,
        "output_names": constants.minify_output_names,
        "locale_aliases": dict(constants.LOCALE_ALIASES),
        "current_output": config.get("output_locale", "english"),
        "current_lang": config.get("locale", "EN"),
    }


def _set_output_locale(locale: str):
    if locale not in constants.minify_output_list:
        raise ValueError(f"Unknown output locale: {locale}")
    config.set("output_locale", locale)


def _save_setup(data: dict[str, Any]) -> None:
    if "lang" in data:
        localization.load_headless(data["lang"])
        config.set("locale", data["lang"])
    if "game_lang" in data:
        _set_output_locale(data["game_lang"])
    if "steam_ids" in data:
        config.set("steam_ids", data["steam_ids"] if data["steam_ids"] else [])
    config.set("setup_complete", True)

    if not conditions.workshop_installed and not config.get("workshop_modal_shown", False):
        modals.WorkshopTools.show()


def _get_setup_data():
    return {
        "lang": config.get("locale", "EN"),
        "game_lang": config.get("output_locale", "english"),
        "steam_ids": config.get("steam_ids", []),
    }


def _restart_steam_and_apply(data: dict[str, Any]) -> Any:
    steam_ids = data.get("steam_ids", [])
    locale = data.get("locale")
    return steam.apply_and_restart_steam(steam_ids, locale)


def _get_d2pfx_categories():
    dm = _get_d2pfx_dm()
    if not dm.is_loaded():
        return []
    cats = dm.get_categories()
    return [{"id": c, "name": dm.get_category_name(c), "description": dm.get_category_description(c)} for c in cats]


def _get_d2pfx_mods(cat_id: str):
    dm = _get_d2pfx_dm()
    raw = dm.get_mods(cat_id)
    threading.Thread(target=_d2pfx_bg_preload_category, args=(dm, cat_id), daemon=True).start()

    def _has_tag(tags: Any, name: str) -> bool:
        if isinstance(tags, dict):
            return any(k.lower() == name and v for k, v in tags.items())
        return name in [t.lower() for t in (tags or [])]

    def _resolve_url(filename: str) -> tuple[str, bool]:
        is_zip = filename.endswith(".zip")
        if not filename.startswith("http"):
            filename = dm.get_file_url(cat_id, filename)
        return filename, is_zip

    def _is_enabled(mod_dir_name: str) -> bool:
        entry = config.get("modconf", {}).get(mod_dir_name, {})
        return bool(entry.get("enabled", False)) if isinstance(entry, dict) else bool(entry)

    def _tags_list(tags: Any) -> list[str]:
        if isinstance(tags, dict):
            return list(tags.keys())
        return tags if isinstance(tags, list) else []

    filter_nsfw = config.get("d2pfx_filter_nsfw", True)
    filter_anime = config.get("d2pfx_filter_anime", False)
    result = []
    for m in raw:
        tags = m.get("tags", {})
        if filter_nsfw and _has_tag(tags, "adult"):
            continue
        if filter_anime and _has_tag(tags, "anime"):
            continue

        base_dir = f"D2PFX {cat_id.upper()} - {m.get('name', 'Unknown')}"

        # Mods with styles are variants (alternative looks for the same cosmetic).
        # Expand each style into its own installable variant; enabling one is
        # exclusive (see _toggle_d2pfx_mod).
        styles = m.get("styles")
        if styles:
            variants = []
            for i, style in enumerate(styles):
                filename = style.get("file") or ""
                if not filename:
                    continue
                file_url, is_zip = _resolve_url(filename)
                label = style.get("label") or f"Variant {i + 1}"
                variant_dir = f"{base_dir} ({label})"
                variants.append(
                    {
                        "label": label,
                        "color": style.get("color"),
                        "preview": style.get("preview"),
                        "fileUrl": file_url,
                        "isZip": is_zip,
                        "modDirName": variant_dir,
                        "enabled": _is_enabled(variant_dir),
                    }
                )
            if not variants:
                continue
            result.append(
                {
                    "name": m.get("name", "Unknown"),
                    "label": None,
                    "author": m.get("author"),
                    "sender": m.get("sender"),
                    "tags": _tags_list(tags),
                    "preview": variants[0]["preview"],
                    "fileUrl": None,
                    "isZip": False,
                    "modDirName": base_dir,
                    "enabled": any(v["enabled"] for v in variants),
                    "variants": variants,
                }
            )
            continue

        links = m.get("links", [])
        vpk_link = next((lnk for lnk in links if lnk.get("url", "").endswith(".vpk")), None)
        zip_link = next((lnk for lnk in links if lnk.get("url", "").endswith(".zip")), None)
        direct_file = m.get("file")
        mod_url = None
        is_zip = False
        if direct_file:
            if direct_file.endswith(".vpk") or direct_file.endswith(".zip"):
                mod_url, is_zip = _resolve_url(direct_file)
        if not mod_url and vpk_link:
            mod_url = vpk_link["url"]
        if not mod_url and zip_link:
            mod_url = zip_link["url"]
            is_zip = True
        if mod_url and not mod_url.startswith("http"):
            mod_url = dm.get_file_url(cat_id, mod_url)
        mod_dir_name = base_dir
        label = m.get("label")
        if label:
            mod_dir_name = f"{mod_dir_name} {label}"
        result.append(
            {
                "name": m.get("name", "Unknown"),
                "label": m.get("label"),
                "author": m.get("author"),
                "sender": m.get("sender"),
                "tags": _tags_list(tags),
                "preview": m.get("preview"),
                "fileUrl": mod_url,
                "isZip": is_zip,
                "modDirName": mod_dir_name,
                "enabled": _is_enabled(mod_dir_name),
            }
        )
    return result


def _get_d2pfx_counts():
    dm = _get_d2pfx_dm()
    if not dm.is_loaded():
        return {"total": 0, "enabled": 0}
    total = sum(len(dm.get_mods(cat)) for cat in dm.get_categories())
    modconf = config.get("modconf", {})
    enabled = sum(1 for v in modconf.values() if isinstance(v, dict) and v.get("enabled"))
    return {"total": total, "enabled": enabled}


def _get_d2pfx_state():
    dm = _get_d2pfx_dm()
    return {
        "loading": dm.is_loading(),
        "loaded": dm.is_loaded(),
        "error": dm.get_load_error(),
    }


def _reload_d2pfx():
    dm = _get_d2pfx_dm()
    if dm.is_loading() or dm.is_loaded():
        return dm.is_loaded()

    def _load_dm(dm: Any = dm) -> None:
        dm.load()
        if dm.is_loaded():
            from ui import output_bridge

            output_bridge.send_js("window.__d2pfxLoaded()")

    threading.Thread(target=_load_dm, daemon=True).start()
    return False


def _refresh_d2pfx_catalogue():
    dm = _get_d2pfx_dm()
    if dm.is_loading():
        return False

    def _do_refresh(dm: Any = dm) -> None:
        if dm.refresh():
            from ui import output_bridge

            output_bridge.send_js("window.__d2pfxLoaded()")

    threading.Thread(target=_do_refresh, daemon=True).start()
    return True


def _clear_d2pfx_cache():
    dm = _get_d2pfx_dm()

    def _do_clear(dm: Any = dm) -> None:
        try:
            if os.path.isdir(dm.previews_dir):
                for entry in os.listdir(dm.previews_dir):
                    path = os.path.join(dm.previews_dir, entry)
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        os.remove(path)
        except Exception as e:
            log.write_warning(f"Error clearing D2PFX previews cache: {e}")

    threading.Thread(target=_do_clear, daemon=True).start()
    return True


def _get_d2pfx_selected_variants():
    return config.get("d2pfx_selected_variants", {})


def _set_d2pfx_selected_variants(data: object):
    if not isinstance(data, dict):
        raise ValueError("Invalid payload: expected object mapping mod dir names to selected variant dir names")
    cleaned = {}
    for base_dir, variant_dir in data.items():
        if isinstance(base_dir, str) and isinstance(variant_dir, str) and base_dir and variant_dir:
            cleaned[base_dir] = variant_dir
    config.set("d2pfx_selected_variants", cleaned)
    return cleaned


def _toggle_d2pfx_mod(
    mod_dir_name: str, enabled: bool, file_url: str = "", is_zip: bool = False, disable_others: list[str] | None = None
):
    modconf = config.get("modconf", {})
    modconf[mod_dir_name] = {"enabled": enabled, "url": file_url, "is_zip": is_zip}
    # Variants of the same mod are exclusive: enabling one disables the rest.
    if enabled:
        for other in disable_others or []:
            if other == mod_dir_name or other not in modconf:
                continue
            modconf[other] = {**modconf[other], "enabled": False}
    config.set("modconf", modconf)
    states = {mod_dir_name: enabled}
    for other in disable_others or []:
        if other != mod_dir_name:
            states[other] = False
    mods_shared.set_state_batch(states)


def _set_all_mods(enabled: bool):
    targets = [
        mod
        for mod, _, is_vpk, always, unsupported, _, _ in _iter_available_mods()
        if is_vpk or not (always or unsupported)
    ]
    mods_shared.set_state_batch({mod: enabled for mod in targets})


def _wipe_language_paths():
    import patch.unins as unins
    from ui import localization, modal_shared

    # Capture the owner token on the caller (JS worker) thread so the daemon
    # thread can release the same lock instead of leaking it via owner mismatch.
    token = getattr(_lock_tls, "token", None) or f"anon-{threading.get_ident()}"
    _set_locked(True, token)

    def _do_wipe():
        # Adopt the caller's owner token so _set_locked(False) and the nested
        # interactive_lock() inside unins.wipe() are recognized as this operation.
        _lock_tls.token = token
        try:
            loc = localization.localization_dict
            btn_cancel = loc.get("btn_cancel", "Cancel")
            btn_proceed = loc.get("btn_proceed", "Proceed")
            result = modal_shared.show(
                title=loc.get("confirm_title", "Confirm"),
                messages=[loc.get("wipe_language_confirm", "This will wipe all language output paths. Continue?")],
                buttons=[btn_cancel, btn_proceed],
            )
            if result == btn_proceed:
                unins.wipe()
        finally:
            _lock_tls.token = None
            _set_locked(False, token)

    threading.Thread(target=_do_wipe, daemon=True).start()


def _extract_workshop_tools():
    output.clean()
    fs.remove_path(base.rescomp_override_dir)
    fails = 0
    for i, path in enumerate(constants.dota_tools_paths):
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.copytree(path, constants.dota_tools_extraction_paths[i], dirs_exist_ok=True)
            else:
                shutil.copy2(path, constants.dota_tools_extraction_paths[i])
        else:
            output.add_text("&extraction_of_failed", path)
            fails += 1
    if not fails:
        constants.rescomp_override = True
        constants.recalc_rescomp_dirs()
        if os.path.exists(constants.dota_resource_compiler_path):
            output.add_text("&extracted")
        else:
            output.add_text("&extraction_of_failed", constants.dota_resource_compiler_path)


def _select_compile_dir():
    from ui import output_bridge

    w = output_bridge.get_window()
    if w is None:
        return None
    selected = w.create_file_dialog(webview.FileDialog.FOLDER)
    if selected:
        config.set("custom_compile_path", selected[0])
        output.add_text("&selected_compile_path", selected[0])
        return selected[0]
    return None


def _run_compile_from_custom():
    from ui import modal_shared

    try:
        custom_path = config.get("custom_compile_path", "")
        if not custom_path or not os.path.exists(custom_path):
            loc = localization.localization_dict
            modal_shared.show(
                title=loc.get("no_compile_path_title", "No Compile Path"),
                messages=[
                    loc.get("no_compile_path_msg", "No compile path selected. Use 'Select path to compile' first.")
                ],
                buttons=[loc.get("btn_ok", "OK")],
            )
            return
        _run_compile_from(custom_path)
    finally:
        _set_locked(False)


def _run_compile_from(input_path: str) -> None:
    helper.compile_assets(input_path)


def _open_file_dialog(file_types: str = "") -> str | None:
    from ui import output_bridge

    w = output_bridge.get_window()
    if w is None:
        return None
    if file_types:
        selected = w.create_file_dialog(webview.FileDialog.OPEN, file_types=(file_types,))
    else:
        selected = w.create_file_dialog(webview.FileDialog.OPEN)
    if selected:
        return selected[0]
    return None


def _install_mod_from_drop(path: str, progress_callback: Callable[[float, str], None] | None = None):
    if is_locked():
        raise RuntimeError("Application is locked")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")
    basename = os.path.splitext(os.path.basename(path))[0]
    target = os.path.join(base.mods_dir, basename)
    if os.path.isdir(path):
        shutil.copytree(path, target, dirs_exist_ok=True)
    elif path.endswith(".zip"):
        fs.create_dirs(target)
        fs.extract_archive(path, target, progress_callback=progress_callback)
    elif path.endswith(".vpk"):
        vpk_target = os.path.join(base.mods_dir, os.path.basename(path))
        fs.copy_file(path, vpk_target, progress_callback=progress_callback)
        target = vpk_target
    elif path.endswith((".7z", ".rar", ".tar", ".tar.gz", ".tgz")):
        raise ValueError(
            f"Unsupported file type: {path}. Supported drop formats are folders, .zip and .vpk. "
            + "Extract the archive and drop the folder instead."
        )
    else:
        raise ValueError(f"Unsupported file type: {path}")
    if os.path.isdir(target):
        manifest_path = os.path.join(target, "manifest.json")
        if not os.path.exists(manifest_path):
            config.write_json_file(manifest_path, {"visual": True, "order": 1})
    mods_shared.scan_mods(force=True)
    output.add_text("&installed_mod_from_drop", basename)


# ── Dev Tools path map ──────────────────────────────────────────────────

_PATH_MAP = {
    "compile_output": lambda: helper.get_output_path(),
    "compile_output_pak": lambda: os.path.join(helper.get_output_path(), "pak66_dir.vpk"),
    "minify_root": os.getcwd,
    "logs": lambda: base.logs_dir,
    "config": lambda: base.config_dir,
    "mods": lambda: base.mods_dir,
    "dota2": lambda: os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta"),
    "dota2_pak01": lambda: constants.dota_game_pak_path,
    "dota2_core": lambda: constants.dota_core_pak_path,
    "dota2_tools": lambda: constants.dota2_tools_executable,
}


# ── Mod conflict resolution ──────────────────────────────────────────────


def _find_enabled_conflicts(mod: str) -> list[str]:
    """Return currently-enabled mods that conflict with `mod`."""
    disabled = []
    seen = set()
    for conflict_dict in constants.mod_conflicts_list:
        for conflict_mod, conflicts in conflict_dict.items():
            if conflict_mod == mod:
                for c in conflicts:
                    if c not in seen and mods_shared.get_state(c):
                        disabled.append(c)
                        seen.add(c)
            elif mod in conflicts and mods_shared.get_state(conflict_mod) and conflict_mod not in seen:
                disabled.append(conflict_mod)
                seen.add(conflict_mod)
    return disabled


def _set_mod_enabled(mod: str, enabled: bool, resolve_conflicts: bool = False):
    if not enabled:
        mods_shared.set_state(mod, False)
        return {"disabled": []}
    conflicts = _find_enabled_conflicts(mod)
    if conflicts and not resolve_conflicts:
        return {"needs_confirmation": True, "conflicts": conflicts}
    for other in conflicts:
        mods_shared.set_state(other, False)
    mods_shared.set_state(mod, True)
    return {"disabled": conflicts}


# ── API handler registry ────────────────────────────────────────────────

_API_HANDLERS: dict[str, Callable[..., object]] = {
    # ── Lock-pattern runners ──
    "patch": lambda: _run_locked(_run_patch),
    "compile_from_custom": lambda: _run_locked(_run_compile_from_custom),
    # ── Pure passthroughs (1 line) ──
    "uninstall": modals.Uninstall.show,
    "set_mod_enabled": _set_mod_enabled,
    "save_mod_settings": lambda mod, data: config.save_mod_config(mod, data),
    "get_available_langs": localization.get_available,
    "get_steam_path_state": lambda: {"path_known": bool(steam.ROOT), "resolving": _resolving_paths},
    "get_steam_accounts": steam.get_steam_accounts,
    "dismiss_welcome": lambda: config.set("welcome_shown", True),
    "get_d2pfx_preview": lambda cat_id, filename: _d2pfx_load_preview(_get_d2pfx_dm(), cat_id, filename),
    "create_debug_zip": log.create_debug_zip,
    "compile_assets": helper.run_resource_compiler,
    "launch_steam": steam.launch_steam,
    "kill_steam": steam.kill_steam,
    "reset_settings": lambda: config.reset_all(),
    # ── Short helpers (2-3 lines) ──
    "refresh_mods": lambda: (mods_shared.scan_mods(force=True), output.add_text("&refreshed_mod_list")),
    "get_setup_state": lambda: {"complete": bool(config.get("setup_complete", False))},
    "get_setup_data": _get_setup_data,
    "get_welcome_state": lambda: {"show": not bool(config.get("welcome_shown", False))},
    "get_localization": lambda lang: (localization.load_headless(lang), localization.localization_dict)[1],
    "open_url": webbrowser.open,
    "validate_dota2": lambda: webbrowser.open(f"steam://validate/{base.STEAM_DOTA_ID}"),
    "open_path": lambda path, args="": fs.open_thing(_PATH_MAP.get(path, lambda: path)(), args),
    # ── Medium / complex handlers ──
    "get_mods": _get_mods,
    "get_mod_preview": _get_mod_preview,
    "get_mod_file_preview": _get_mod_file_preview,
    "get_mod_notes_html": _get_mod_notes_html,
    "get_settings": _get_settings,
    "save_settings": _save_settings,
    "get_mod_settings": lambda mod: {
        "schema": manifest_utils.get_mod(os.path.join(base.mods_dir, mod)).get("settings", []),
        "values": config.get_mod_config(mod),
        "presets": manifest_utils.get_mod(os.path.join(base.mods_dir, mod)).get("presets", []),
        "preview_file": manifest_utils.get_mod(os.path.join(base.mods_dir, mod)).get("preview_file"),
    },
    "run_mod_utility": _run_mod_utility,
    "reset_mod_settings": _reset_mod_settings,
    "reset_all_mod_settings": _reset_all_mod_settings,
    "set_language": _set_language,
    "resolve_steam_path": _resolve_steam_path,
    "get_app_info": _get_app_info,
    "save_setup": _save_setup,
    "restart_steam_and_apply": _restart_steam_and_apply,
    "get_d2pfx_categories": _get_d2pfx_categories,
    "get_d2pfx_mods": _get_d2pfx_mods,
    "get_d2pfx_counts": _get_d2pfx_counts,
    "get_d2pfx_state": _get_d2pfx_state,
    "reload_d2pfx": _reload_d2pfx,
    "refresh_d2pfx_catalogue": _refresh_d2pfx_catalogue,
    "clear_d2pfx_cache": _clear_d2pfx_cache,
    "get_d2pfx_selected_variants": _get_d2pfx_selected_variants,
    "set_d2pfx_selected_variants": _set_d2pfx_selected_variants,
    "toggle_d2pfx_mod": _toggle_d2pfx_mod,
    "set_all_mods": _set_all_mods,
    "wipe_language_paths": _wipe_language_paths,
    "extract_workshop_tools": lambda: _run_locked(_extract_workshop_tools),
    "select_compile_dir": _select_compile_dir,
    "open_file_dialog": _open_file_dialog,
}

_WRAPPER_CACHE: dict[str, Callable[..., object]] = {}


def __getattr__(name: str) -> Callable[..., object]:
    if name not in _API_HANDLERS:
        raise AttributeError(f"module 'actions' has no attribute '{name}'")
    if name in _WRAPPER_CACHE:
        return _WRAPPER_CACHE[name]
    fn = _API_HANDLERS[name]

    @functools.wraps(fn)
    def wrapper(*a: Any, **kw: Any) -> dict[str, Any]:
        try:
            return {"ok": True, "data": fn(*a, **kw), "error": None}
        except Exception as e:
            log.write_warning(f"API call '{name}' failed")
            return {"ok": False, "data": None, "error": str(e)}

    _WRAPPER_CACHE[name] = wrapper
    return wrapper


# ── Settings schema (unchanged, still referenced by _get_settings) ──────

ZOOM_MIN = 1.0
ZOOM_MAX = 2.0
ZOOM_STEP = 0.05


def _clamp_zoom(value: Any) -> float:
    """Clamp a ui_zoom value to the supported range."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 1.0
    return min(ZOOM_MAX, max(ZOOM_MIN, v))


_SETTINGS: list[dict[str, Any]] = [
    {"key": "steam_root", "text": "Steam Root", "default": "", "type": "inputbox", "advanced": True},
    {"key": "steam_library", "text": "Steam Library", "default": "", "type": "inputbox", "advanced": True},
    {
        "key": "steam_ids",
        "text": "Steam Accounts",
        "default": [],
        "type": "accounts",
        "advanced": True,
        "items_getter": steam.get_steam_accounts,
    },
    {"key": "opt_into_rcs", "text": "Opt into RCs", "default": False, "type": "checkbox", "advanced": True},
    {
        "key": "ui_zoom",
        "text": "UI Zoom",
        "default": 1.0,
        "type": "slider",
        "min": ZOOM_MIN,
        "max": ZOOM_MAX,
        "step": ZOOM_STEP,
    },
    {"key": "launch_dota_after_patch", "text": "Launch Dota2 after patching", "default": False, "type": "checkbox"},
    {
        "key": "patch_on_updates",
        "text": "Add conditional-patch to launch options",
        "default": False,
        "type": "checkbox",
        "advanced": True,
    },
    {"key": "smooth_scroll", "text": "Smooth scrolling", "default": True, "type": "checkbox"},
    {
        "key": "devtools_enabled",
        "text": "Show Dev Tools tab",
        "default": False,
        "type": "checkbox",
        "advanced": True,
    },
    {
        "key": "kill_self_after_patch",
        "text": "Close Minify after patching",
        "default": False,
        "type": "checkbox",
        "advanced": True,
    },
    {
        "key": "d2pfx_filter_nsfw",
        "text": "Filter 18+ Mods (D2PFX Browser)",
        "default": True,
        "type": "checkbox",
        "advanced": True,
    },
    {
        "key": "d2pfx_filter_anime",
        "text": "Filter Anime Mods (D2PFX Browser)",
        "default": False,
        "type": "checkbox",
        "advanced": True,
    },
    {
        "key": "d2pfx_auto_refresh_catalogue",
        "text": "Auto-refresh D2PFX catalogue (24h)",
        "default": True,
        "type": "checkbox",
        "advanced": True,
    },
    {
        "key": "d2pfx_video_autoplay",
        "text": "Auto-play D2PFX video previews",
        "default": True,
        "type": "checkbox",
    },
    {
        "key": "opt_out_vpk_metadata",
        "text": "Opt-out of VPK metadata",
        "default": False,
        "type": "checkbox",
        "advanced": True,
    },
]
