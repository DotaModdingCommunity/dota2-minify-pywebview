import os
import sys
import threading
from typing import Any

_original_cwd = os.getcwd()

from core import base

base.original_cwd = os.getcwd()

# Ensure root directories
_app_dir = (
    os.path.dirname(os.path.abspath(__file__))
    if not getattr(sys, "frozen", False)
    else os.path.dirname(os.path.realpath(sys.executable))
)
if not getattr(sys, "frozen", False):
    sys.argv[0] = os.path.abspath(sys.argv[0])
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from core.base import resolve_app_root

os.chdir(resolve_app_root(_app_dir))

if len(sys.argv) > 1:
    import cli
    from core import base

    base.original_cwd = _original_cwd
    cli.run()
    sys.exit(0)

# isort: split

import core.migrations  # noqa: F401  (triggers modcfg→manifest migration)
import conditions
import helper
from core import config, log

sys.excepthook = lambda *a: log.write_crashlog(*a, handled=False)

# ── pywebview + Svelte path ──────────────────────────────────────────────────

from ui import localization, modals, output_bridge
from ui.localization import load_headless as _load_loc

output_bridge.register_with_output()
_load_loc(config.get("locale", "EN"))

# Patch set_window to trigger deferred startup once the window is ready
_original_set_window = output_bridge.set_window

_init_done = False


def _patched_set_window(w: Any) -> None:
    _original_set_window(w)

    def _init() -> None:
        global _init_done

        def _heavy_init() -> None:
            try:
                mods_shared.scan_mods()
                conditions.disable_workshop_mods()

                setup_done = config.get("setup_complete", False)
                if setup_done:
                    if not conditions.workshop_installed and not config.get("workshop_modal_shown", False):
                        modals.WorkshopTools.show()
                    helper.bulk_exec_script("initial", False)
                    modals.Update.check()
                    modals.Announcements.check()
            except Exception:
                import traceback

                traceback.print_exc()
                log.write_crashlog()

        try:
            from ui import actions as _actions

            # Signal readiness immediately — before any init work
            _actions._init_done = True
            _init_done = True
            output_bridge.send_js("window.__backendReady()")

            from core import constants as _constants
            from core import config, mods_shared, steam, utils

            config.validate()
            steam.init_steam()
            _constants.init_paths()
            utils.setup_system()

            if conditions.is_dota_running("&error_please_close_dota_terminal", "error"):
                from ui import modal_shared

                loc = localization.localization_dict
                modal_shared.show(
                    title=loc.get("close_dota_modal_title", "Dota 2 is running"),
                    messages=[loc.get("close_dota_modal_msg", "Please close Dota 2 and restart Minify.")],
                    buttons=["OK"],
                )

            if not conditions.check_binaries():
                threading.Thread(target=_actions._download_deps_background, daemon=True).start()

            _heavy_init()
        except Exception:
            import traceback

            traceback.print_exc()
            log.write_crashlog()
            _init_done = False
            output_bridge.send_js("window.__backendReady()")

    threading.Thread(target=_init, daemon=True).start()


output_bridge.set_window = _patched_set_window

# Named mutex the installer (installer.iss AppMutex=MinifyMutex) checks so it
# can detect a running instance. Holding the handle keeps it alive; the OS
# releases it on process exit. Also enforced at startup so a second instance
# can't run concurrently and fight over the shared config file.
if sys.platform == "win32":
    import ctypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _INSTANCE_MUTEX = _kernel32.CreateMutexW(None, False, "MinifyMutex")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        try:
            print("Another instance of Minify is already running.", file=sys.stderr)
        except Exception:
            pass
        sys.exit(0)

from ui.web_window import create_window

create_window()
