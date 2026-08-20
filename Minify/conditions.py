"Checks for various things"

import os
import stat
import subprocess
import threading
import webbrowser
from typing import Any, Callable

import vdf
from core import base, constants, fs, log, output, steam

workshop_installed = False
workshop_required_methods = ["styling.css", "xml.json", "files_uncompiled"]

_dependency_lock = threading.RLock()

ProgressCallback = Callable[..., Any]


def is_dota_running(text_tag: str, text_type: str) -> bool:
    target = "dota2.exe" if base.is_win else "dota2"
    if base.is_win:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {target}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            running = target.lower() in result.stdout.lower()
        except subprocess.TimeoutExpired:
            running = False
    else:
        try:
            result = subprocess.run(["pgrep", "-x", target], capture_output=True, timeout=5)
            running = result.returncode == 0
        except subprocess.TimeoutExpired:
            running = False

    if running:
        output.add_text(text_tag, msg_type=text_type)
    return running


def check_workshop_tools():
    acf_path = os.path.join(steam.LIBRARY, "steamapps", f"appmanifest_{base.STEAM_DOTA_ID}.acf")
    try:
        with open(acf_path, encoding="utf-8") as f:
            app_state = vdf.load(f).get("AppState", {})
    except Exception as e:
        log.write_warning(f"Failed to read ACF: {e}")
        return False

    if not app_state or str(app_state.get("StateFlags", "")) != "4":
        return False

    mounted_config = app_state.get("MountedConfig", "")
    if isinstance(mounted_config, str):
        return base.STEAM_DOTA_WORKSHOP_TOOLS_ID in mounted_config.split()

    if not isinstance(mounted_config, dict):
        return False
    mounted_str = mounted_config.get("optionaldlc") or ""
    disabled_str = mounted_config.get("DisabledDLC") or ""
    mounted_set = {token.strip() for token in mounted_str.replace(",", " ").split() if token.strip()}
    disabled_set = {token.strip() for token in disabled_str.replace(",", " ").split() if token.strip()}
    return base.STEAM_DOTA_WORKSHOP_TOOLS_ID in mounted_set and base.STEAM_DOTA_WORKSHOP_TOOLS_ID not in disabled_set


def is_compiler_found() -> None:
    global workshop_installed
    workshop_installed = check_workshop_tools()
    if not workshop_installed:
        workshop_installed = os.path.exists(constants.dota_resource_compiler_path)
    from core import config as _config

    if _config.get("debug_disable_workshop", False):
        workshop_installed = False
    if not workshop_installed:
        output.add_text("&error_no_workshop_tools_found_terminal", msg_type="warning")


_DL_FRAC = 0.80
_EXTRACT_FRAC = 0.95


def resolve_dependencies(
    retries: int = 0, progress_callback: ProgressCallback | None = None, headless: bool = False
) -> None:
    """Serialize dependency resolution so concurrent callers never write the same binaries."""
    with _dependency_lock:
        return _resolve_dependencies(retries, progress_callback=progress_callback, headless=headless)


def _resolve_dependencies(
    retries: int = 0, progress_callback: ProgressCallback | None = None, headless: bool = False
) -> None:
    """
    Attempts to download dependencies ripgrep and Source2Viewer-CLI(if workshop tools are available)
    for up to 4 times and opens up their download URLs if they don't exist.
    """
    from core import config as _config

    debug = _config.get("debug_env", False)
    disable_workshop = _config.get("debug_disable_workshop", False)
    workshop_available = workshop_installed and not disable_workshop

    try:
        total_steps = 2 if workshop_available else 1
        completed_steps = 0

        if workshop_available:
            s2v_on_path = _which(constants.s2v_executable) if not debug else None
            if s2v_on_path:
                constants.s2v_executable = s2v_on_path
            else:
                constants.s2v_executable = os.path.basename(constants.s2v_executable)

            if s2v_on_path is None or debug:
                zip_path = constants.s2v_latest.split("/")[-1]
                file_base = completed_steps / total_steps
                file_inc = 1.0 / total_steps
                output.add_text("&deps_downloading_s2v")
                if progress_callback:
                    progress_callback(file_base, "&deps_checking_s2v")

                def _s2v_progress(downloaded: int, total: int) -> None:
                    p = file_base
                    if total:
                        p += (downloaded / total) * file_inc * _DL_FRAC
                    if progress_callback:
                        progress_callback(p, "&deps_downloading_s2v")

                if fs.download_file(constants.s2v_latest, zip_path, progress_callback=_s2v_progress):
                    output.add_text("&deps_extracting_s2v")
                    if progress_callback:
                        progress_callback(file_base + file_inc * _DL_FRAC, "&deps_extracting_s2v")
                    if fs.extract_archive(zip_path, "."):
                        fs.remove_path(zip_path)
                        constants.s2v_executable = os.path.basename(constants.s2v_executable)

                        if progress_callback:
                            progress_callback(file_base + file_inc * _EXTRACT_FRAC, "&deps_setup_s2v")

                        if not base.is_win and not os.access(constants.s2v_executable, os.X_OK):
                            current_permissions = os.stat(constants.s2v_executable).st_mode
                            os.chmod(
                                constants.s2v_executable,
                                current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                            )

                        completed_steps += 1
                        output.add_text("&deps_s2v_ready")
                        if progress_callback:
                            progress_callback(completed_steps / total_steps, "&deps_s2v_ready")

        rg_on_path = _which(constants.rg_executable) if not debug else None
        if rg_on_path:
            constants.rg_executable = rg_on_path
        else:
            constants.rg_executable = os.path.basename(constants.rg_executable)

        if rg_on_path is None or debug:
            archive_path = constants.rg_latest.split("/")[-1]
            archive_name = archive_path[:-4] if archive_path[-4:] == ".zip" else archive_path[:-7]
            file_base = completed_steps / total_steps
            file_inc = 1.0 / total_steps
            output.add_text("&deps_downloading_rg")
            if progress_callback:
                progress_callback(file_base, "&deps_checking_rg")

            def _rg_progress(downloaded: int, total: int) -> None:
                p = file_base
                if total:
                    p += (downloaded / total) * file_inc * _DL_FRAC
                if progress_callback:
                    progress_callback(p, "&deps_downloading_rg")

            if fs.download_file(constants.rg_latest, archive_path, progress_callback=_rg_progress):
                output.add_text("&deps_extracting_rg")
                if progress_callback:
                    progress_callback(file_base + file_inc * _DL_FRAC, "&deps_extracting_rg")

                rg_binary_name = os.path.basename(constants.rg_executable)
                success = fs.extract_archive(archive_path, ".", f"{archive_name}/{rg_binary_name}")

                if success:
                    fs.move_path(
                        os.path.join(archive_name, rg_binary_name),
                        rg_binary_name,
                    )
                    fs.remove_path(archive_path, archive_name)

                    if progress_callback:
                        progress_callback(file_base + file_inc * _EXTRACT_FRAC, "&deps_setup_rg")

                    constants.rg_executable = rg_binary_name

                    if not base.is_win and not os.access(constants.rg_executable, os.X_OK):
                        current_permissions = os.stat(constants.rg_executable).st_mode
                        os.chmod(
                            constants.rg_executable,
                            current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                        )

                    completed_steps += 1
                    output.add_text("&deps_rg_ready")
                    if progress_callback:
                        progress_callback(completed_steps / total_steps, "&deps_rg_ready")
        constants.s2v_exec_path = (
            constants.s2v_executable
            if os.path.isabs(constants.s2v_executable)
            else os.path.join(".", constants.s2v_executable)
        )
        constants.rg_exec_path = (
            constants.rg_executable
            if os.path.isabs(constants.rg_executable)
            else os.path.join(".", constants.rg_executable)
        )

        if progress_callback:
            progress_callback(1.0, "&deps_done")

    except Exception:
        if retries < 3:
            log.write_warning(f"Download failed (attempt {retries + 1}/3), retrying...")
            output.add_text("&deps_dl_retry", msg_type="warning")
            if progress_callback:
                progress_callback(0, "&deps_retrying", retries + 1)
            return _resolve_dependencies(retries + 1, progress_callback=progress_callback, headless=headless)
        log.write_crashlog()
        output.add_text("&deps_failed_attempts", msg_type="error")
        if progress_callback:
            progress_callback(0, "&deps_failed")
        if not headless:
            webbrowser.open(constants.rg_latest)
            if workshop_installed or disable_workshop:
                webbrowser.open(constants.s2v_latest)
        return


def _which(name: str) -> str | None:
    """Check if executable exists in CWD. No PATH search (avoids network hangs)."""
    if os.path.isabs(name):
        if not os.path.isfile(name):
            return None
        found = name
    else:
        try:
            found = os.path.abspath(os.path.basename(name))
            if not os.path.isfile(found):
                return None
        except (OSError, PermissionError):
            return None
    if not base.is_win and not os.access(found, os.X_OK):
        return None
    return found


def check_binaries() -> bool:
    """Checks if required binaries exist in CWD (no PATH search)."""
    if workshop_installed:
        s2v_found = _which(constants.s2v_executable)
        if s2v_found is None:
            return False
        constants.s2v_executable = s2v_found
        constants.s2v_exec_path = s2v_found

    rg_found = _which(constants.rg_executable)
    if rg_found is None:
        return False
    constants.rg_executable = rg_found
    constants.rg_exec_path = rg_found

    return True


def disable_workshop_mods() -> None:
    if not workshop_installed:
        from core import mods_shared
        from patch import manifest_utils

        disabled = []
        for mod in mods_shared.mods_with_order:
            if not mods_shared.get_state(mod):
                continue
            mod_path = os.path.join(base.mods_dir, mod)
            if manifest_utils.get_mod(mod_path).get("skip_workshop_check", False):
                continue
            for method_path in workshop_required_methods:
                if os.path.exists(os.path.join(mod_path, method_path)):
                    disabled.append(mod)
                    output.add_text("&mod_disabled_requires_workshop", mod, msg_type="warning")
                    break
        if disabled:
            mods_shared.set_state_batch({mod: False for mod in disabled})
