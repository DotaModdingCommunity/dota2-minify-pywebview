"Variables that almost never change"

import os
import platform
import shutil
import sys

VERSION = "2.0.0"
TITLE = f"Minify {VERSION}"

OS = platform.system()
MACHINE = platform.machine().lower().replace("amd64", "x86_64")
ARCHITECTURE = platform.architecture()[0]

is_win = True if OS == "Windows" else False
is_linux = True if OS == "Linux" else False
is_mac = True if OS == "Darwin" else False

FROZEN = getattr(sys, "frozen", False)
HEADLESS = False

# working directory the app was launched from, captured before __main__ chdirs;
# used by the CLI to resolve relative -c/-m paths against the caller's cwd
original_cwd = ""

OWNER = "Egezenn"
REPO = "dota2-minify"


def steam_default_path():
    if is_linux:
        return os.path.join(os.path.expanduser("~"), ".local", "share", "Steam")
    if is_mac:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Steam")
    return os.path.join("C:\\", "Program Files (x86)", "Steam")


def resolve_app_root(app_dir: str) -> str:
    """
    Resolves the writable app root the process should chdir into.

    `app_dir` (the executable's directory) is used when its config/logs
    subdirectories can be created — the normal portable layout. On POSIX, when
    the app dir is read-only (e.g. a macOS bundle in /Applications or a Linux
    install under /opt), the app falls back to a per-user data directory and
    seeds the bundled mods into it on first run, instead of crashing.
    """
    if is_win:
        os.makedirs(os.path.join(app_dir, "config"), exist_ok=True)
        os.makedirs(os.path.join(app_dir, "logs"), exist_ok=True)
        return app_dir

    try:
        os.makedirs(os.path.join(app_dir, "config"), exist_ok=True)
        os.makedirs(os.path.join(app_dir, "logs"), exist_ok=True)
        return app_dir
    except (PermissionError, OSError):
        if is_mac:
            data_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Minify")
        else:
            data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "minify")
        os.makedirs(os.path.join(data_dir, "config"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "logs"), exist_ok=True)

        src_mods = os.path.join(app_dir, "mods")
        dst_mods = os.path.join(data_dir, "mods")
        if os.path.isdir(src_mods) and not os.path.exists(dst_mods):
            try:
                shutil.copytree(src_mods, dst_mods)
            except OSError:
                pass

        try:
            print(f"App directory is not writable; using {data_dir} for config, logs and mods.", file=sys.stderr)
        except Exception:
            pass
        return data_dir


# assuming steam runtimes on linux / darwin
if is_linux:
    DOTA_EXECUTABLE_PATH = os.path.join("steamapps", "common", "dota 2 beta", "game", "bin", "linuxsteamrt64", "dota2")
elif is_mac:
    DOTA_EXECUTABLE_PATH = os.path.join(
        "steamapps",
        "common",
        "dota 2 beta",
        "game",
        "bin",
        "osx64",
        "dota2.app",
        "Contents",
        "MacOS",
        "dota2",
    )
else:
    DOTA_EXECUTABLE_PATH = os.path.join("steamapps", "common", "dota 2 beta", "game", "bin", "win64", "dota2.exe")

STEAM_DEFAULT_INSTALLATION_PATH = steam_default_path()

DOTA_TOOLS_EXECUTABLE_PATH = os.path.join("steamapps", "common", "dota 2 beta", "game", "bin", "win64", "dota2cfg.exe")

# launchers for dota2 won't work as it presumes native version, doesn't really matter
DOTA_EXECUTABLE_PATH_FALLBACK = os.path.join("steamapps", "common", "dota 2 beta", "game", "bin", "win64", "dota2.exe")

STEAM_DOTA_ID = "570"
STEAM_DOTA_WORKSHOP_TOOLS_ID = "313250"

# static directory names
bin_dir = os.path.join(getattr(sys, "_MEIPASS", ""), "bin") if FROZEN else "bin"
build_dir = "vpk_build"
replace_dir = "vpk_replace"
merge_dir = "vpk_merge"
logs_dir = "logs"
mods_dir = "mods"
config_dir = "config"
cache_dir = "cache"

# bin
blank_files_dir = os.path.join(bin_dir, "blank-files")
localization_file_dir = os.path.join(bin_dir, "localization.json")
rescomp_override_dir = os.path.join(config_dir, "rescomp_override")

# logs
log_crashlog = os.path.join(logs_dir, "crashlog.txt")
log_warnings = os.path.join(logs_dir, "warnings.txt")
log_unhandled = os.path.join(logs_dir, "unhandled.txt")
log_s2v = os.path.join(logs_dir, "Source2Viewer-CLI.txt")
log_rescomp = os.path.join(logs_dir, "resourcecompiler.txt")

# cache
dota_steam_inf_cache = os.path.join(cache_dir, "steam.inf")

# config
main_config_file_dir = os.path.join(config_dir, "minify_config.json")
mods_config_dir = os.path.join(config_dir, "mods.json")

# links
discord = "https://discord.com/invite/9867CPv7cy"
telegram = "https://t.me/dota2minify"
github_io = f"https://{OWNER}.github.io/{REPO}"
