# core.base

Variables that almost never change

## `steam_default_path()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def steam_default_path():
    if is_linux:
        return os.path.join(os.path.expanduser("~"), ".local", "share", "Steam")
    if is_mac:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Steam")
    return os.path.join("C:\\", "Program Files (x86)", "Steam")

```

</details>

## `resolve_app_root(app_dir)`

Resolves the writable app root the process should chdir into.

`app_dir` (the executable's directory) is used when its config/logs
subdirectories can be created — the normal portable layout. On POSIX, when
the app dir is read-only (e.g. a macOS bundle in /Applications or a Linux
install under /opt), the app falls back to a per-user data directory and
seeds the bundled mods into it on first run, instead of crashing.

<details open><summary>Source</summary>

```python
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

```

</details>

## Variables

### `VERSION`

<details open><summary>Source</summary>

```python
VERSION = "2.0.0"

```

</details>

### `TITLE`

<details open><summary>Source</summary>

```python
TITLE = f"Minify {VERSION}"

```

</details>

### `OS`

<details open><summary>Source</summary>

```python
OS = platform.system()

```

</details>

### `MACHINE`

<details open><summary>Source</summary>

```python
MACHINE = platform.machine().lower().replace("amd64", "x86_64")

```

</details>

### `ARCHITECTURE`

<details open><summary>Source</summary>

```python
ARCHITECTURE = platform.architecture()[0]

```

</details>

### `is_win`

<details open><summary>Source</summary>

```python
is_win = True if OS == "Windows" else False

```

</details>

### `is_linux`

<details open><summary>Source</summary>

```python
is_linux = True if OS == "Linux" else False

```

</details>

### `is_mac`

<details open><summary>Source</summary>

```python
is_mac = True if OS == "Darwin" else False

```

</details>

### `FROZEN`

<details open><summary>Source</summary>

```python
FROZEN = getattr(sys, "frozen", False)

```

</details>

### `HEADLESS`

<details open><summary>Source</summary>

```python
HEADLESS = False

```

</details>

### `original_cwd`

<details open><summary>Source</summary>

```python
original_cwd = ""

```

</details>

### `OWNER`

<details open><summary>Source</summary>

```python
OWNER = "Egezenn"

```

</details>

### `REPO`

<details open><summary>Source</summary>

```python
REPO = "dota2-minify"

```

</details>

### `STEAM_DEFAULT_INSTALLATION_PATH`

<details open><summary>Source</summary>

```python
STEAM_DEFAULT_INSTALLATION_PATH = steam_default_path()

```

</details>

### `DOTA_TOOLS_EXECUTABLE_PATH`

<details open><summary>Source</summary>

```python
DOTA_TOOLS_EXECUTABLE_PATH = os.path.join("steamapps", "common", "dota 2 beta", "game", "bin", "win64", "dota2cfg.exe")

```

</details>

### `DOTA_EXECUTABLE_PATH_FALLBACK`

<details open><summary>Source</summary>

```python
DOTA_EXECUTABLE_PATH_FALLBACK = os.path.join("steamapps", "common", "dota 2 beta", "game", "bin", "win64", "dota2.exe")

```

</details>

### `STEAM_DOTA_ID`

<details open><summary>Source</summary>

```python
STEAM_DOTA_ID = "570"

```

</details>

### `STEAM_DOTA_WORKSHOP_TOOLS_ID`

<details open><summary>Source</summary>

```python
STEAM_DOTA_WORKSHOP_TOOLS_ID = "313250"

```

</details>

### `bin_dir`

<details open><summary>Source</summary>

```python
bin_dir = os.path.join(getattr(sys, "_MEIPASS", ""), "bin") if FROZEN else "bin"

```

</details>

### `build_dir`

<details open><summary>Source</summary>

```python
build_dir = "vpk_build"

```

</details>

### `replace_dir`

<details open><summary>Source</summary>

```python
replace_dir = "vpk_replace"

```

</details>

### `merge_dir`

<details open><summary>Source</summary>

```python
merge_dir = "vpk_merge"

```

</details>

### `logs_dir`

<details open><summary>Source</summary>

```python
logs_dir = "logs"

```

</details>

### `mods_dir`

<details open><summary>Source</summary>

```python
mods_dir = "mods"

```

</details>

### `config_dir`

<details open><summary>Source</summary>

```python
config_dir = "config"

```

</details>

### `cache_dir`

<details open><summary>Source</summary>

```python
cache_dir = "cache"

```

</details>

### `blank_files_dir`

<details open><summary>Source</summary>

```python
blank_files_dir = os.path.join(bin_dir, "blank-files")

```

</details>

### `localization_file_dir`

<details open><summary>Source</summary>

```python
localization_file_dir = os.path.join(bin_dir, "localization.json")

```

</details>

### `rescomp_override_dir`

<details open><summary>Source</summary>

```python
rescomp_override_dir = os.path.join(config_dir, "rescomp_override")

```

</details>

### `log_crashlog`

<details open><summary>Source</summary>

```python
log_crashlog = os.path.join(logs_dir, "crashlog.txt")

```

</details>

### `log_warnings`

<details open><summary>Source</summary>

```python
log_warnings = os.path.join(logs_dir, "warnings.txt")

```

</details>

### `log_unhandled`

<details open><summary>Source</summary>

```python
log_unhandled = os.path.join(logs_dir, "unhandled.txt")

```

</details>

### `log_s2v`

<details open><summary>Source</summary>

```python
log_s2v = os.path.join(logs_dir, "Source2Viewer-CLI.txt")

```

</details>

### `log_rescomp`

<details open><summary>Source</summary>

```python
log_rescomp = os.path.join(logs_dir, "resourcecompiler.txt")

```

</details>

### `dota_steam_inf_cache`

<details open><summary>Source</summary>

```python
dota_steam_inf_cache = os.path.join(cache_dir, "steam.inf")

```

</details>

### `main_config_file_dir`

<details open><summary>Source</summary>

```python
main_config_file_dir = os.path.join(config_dir, "minify_config.json")

```

</details>

### `mods_config_dir`

<details open><summary>Source</summary>

```python
mods_config_dir = os.path.join(config_dir, "mods.json")

```

</details>

### `discord`

<details open><summary>Source</summary>

```python
discord = "https://discord.com/invite/9867CPv7cy"

```

</details>

### `telegram`

<details open><summary>Source</summary>

```python
telegram = "https://t.me/dota2minify"

```

</details>

### `github_io`

<details open><summary>Source</summary>

```python
github_io = f"https://{OWNER}.github.io/{REPO}"

```

</details>
