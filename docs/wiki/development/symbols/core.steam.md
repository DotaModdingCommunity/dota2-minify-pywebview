# core.steam

Module to find steam root and library that Dota2 is in (always accounts the Windows' executable path to find if used through an emulation layer).
Also fixes language argument for the user(s)

## `_vdf_get_ci(data)`

Traverse nested VDF dicts with case-insensitive key matching.

<details open><summary>Source</summary>

```python
def _vdf_get_ci(data: dict[str, Any], *keys: str) -> Any:
    """Traverse nested VDF dicts with case-insensitive key matching."""
    current = data
    for key in keys:
        if key in current:
            current = current[key]
        else:
            for k in current:
                if k.lower() == key.lower():
                    current = current[k]
                    break
            else:
                raise KeyError(key)
    return current

```

</details>

## `_remove_lang_arg(arg_string, lang_to_remove)`

Remove `-language` arguments from launch options. If lang_to_remove is set,
only removes that specific language; otherwise removes all of them.

<details open><summary>Source</summary>

```python
def _remove_lang_arg(arg_string: str, lang_to_remove: str | None = None) -> str:
    """Remove `-language` arguments from launch options. If lang_to_remove is set,
    only removes that specific language; otherwise removes all of them."""
    if not arg_string:
        return ""
    it = iter(shlex.split(arg_string.strip()))
    result = []
    for t in it:
        if t != "-language":
            result.append(t)
            continue
        val = next(it, None)
        if val is not None and val.startswith(("-", "+")):
            # "-language" has no value; the next token is another flag.
            if lang_to_remove is None:
                result.append(val)
            else:
                result.append(t)
                result.append(val)
            continue
        if lang_to_remove is None or (val is not None and val == lang_to_remove):
            continue
        result.append(t)
        if val is not None:
            result.append(val)
    return " ".join(result)

```

</details>

## `_launch_prefix()`

Shell prefix that runs `Minify prelaunch` before %command% in launch options.

The whole inner command is shlex.quote()d so paths with spaces or shell
metacharacters survive: on POSIX the shell strips the outer single quotes
and re-quotes via shlex's embedded-quote escapes. macOS uses the guaranteed
/bin/zsh instead of bash 3.2 (the old default login shell).

<details open><summary>Source</summary>

```python
def _launch_prefix() -> str:
    """Shell prefix that runs `Minify prelaunch` before %command% in launch options.

    The whole inner command is shlex.quote()d so paths with spaces or shell
    metacharacters survive: on POSIX the shell strips the outer single quotes
    and re-quotes via shlex's embedded-quote escapes. macOS uses the guaranteed
    /bin/zsh instead of bash 3.2 (the old default login shell).
    """
    if base.is_win:
        return f'cmd /c "{sys.executable}" prelaunch &&'
    if base.is_mac:
        return f"/bin/zsh -c {shlex.quote(f'{sys.executable} prelaunch')} &&"
    return f"bash -c {shlex.quote(f'{sys.executable} prelaunch')} &&"

```

</details>

## `add_conditional_patch_to_launch_options()`

If frozen and patch_on_updates is enabled, prepend the conditional-patch command before %command% in launch options

<details open><summary>Source</summary>

```python
def add_conditional_patch_to_launch_options():
    "If frozen and patch_on_updates is enabled, prepend the conditional-patch command before %command% in launch options"

    if not base.FROZEN:
        return False

    if not config.get("patch_on_updates", False):
        return False

    steam_ids = [account["id"] for account in get_steam_accounts()]

    changed = False
    for steam_id in steam_ids:
        vdf_path = os.path.join(config.get("steam_root"), "userdata", steam_id, "config", "localconfig.vdf")
        if not os.path.exists(vdf_path):
            continue

        with utils.open_utf8R(vdf_path) as file:
            data = vdf.load(file)

        try:
            launch_options = data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID][
                "LaunchOptions"
            ]
        except KeyError:
            continue

        tokens = launch_options.split()

        prefix = _launch_prefix()

        if launch_options.startswith(prefix):
            continue

        other_tokens = [t for t in tokens if t != "%command%"]
        new_tokens = [prefix, "%command%"] + other_tokens
        new_options = " ".join(new_tokens)

        if new_options != launch_options:
            data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID]["LaunchOptions"] = (
                new_options
            )
            with utils.open_utf8R(vdf_path, "w") as file:
                vdf.dump(data, file, pretty=True)
            changed = True

    return changed

```

</details>

## `add_prelaunch_to_launch_options(check_only)`

If frozen and patch_on_launch is enabled, prepend prelaunch command before %command% in launch options

<details open><summary>Source</summary>

```python
def add_prelaunch_to_launch_options(check_only: bool = False):
    "If frozen and patch_on_launch is enabled, prepend prelaunch command before %command% in launch options"

    if not base.FROZEN:
        return False

    if not config.get("patch_on_launch", False):
        return False

    steam_ids = []
    accounts = get_steam_accounts()
    if config.get("apply_for_all", True):
        for account in accounts:
            steam_ids.append(account["id"])
    else:
        steam_ids.append(config.get("steam_id"))

    changed = False
    for steam_id in steam_ids:
        vdf_path = os.path.join(config.get("steam_root"), "userdata", steam_id, "config", "localconfig.vdf")
        if not os.path.exists(vdf_path):
            continue

        with utils.open_utf8R(vdf_path) as file:
            data = vdf.load(file)

        try:
            launch_options = data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID][
                "LaunchOptions"
            ]
        except KeyError:
            continue

        tokens = launch_options.split()

        prefix = _launch_prefix()

        if launch_options.startswith(prefix):
            continue

        other_tokens = [t for t in tokens if t != "%command%"]
        new_tokens = [prefix, "%command%"] + other_tokens
        new_options = " ".join(new_tokens)

        if new_options != launch_options:
            if check_only:
                return True
            data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID]["LaunchOptions"] = (
                new_options
            )
            with utils.open_utf8R(vdf_path, "w") as file:
                vdf.dump(data, file, pretty=True)
            changed = True

    return changed

```

</details>

## `remove_minify_lang()`

Removes `-language minify` argument specifically from launch options only if the locale matches the config.

<details open><summary>Source</summary>

```python
def remove_minify_lang():
    """
    Removes `-language minify` argument specifically from launch options only if the locale matches the config.
    """
    successful_ids = []
    steam_ids = [account["id"] for account in get_steam_accounts()]

    for steam_id in steam_ids:
        vdf_path = os.path.join(config.get("steam_root"), "userdata", steam_id, "config", "localconfig.vdf")
        if not os.path.exists(vdf_path):
            continue

        with utils.open_utf8R(vdf_path) as file:
            data = vdf.load(file)

        locale = config.get("output_locale")
        if locale != "english":
            continue

        try:
            launch_options = data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID][
                "LaunchOptions"
            ]
        except KeyError:
            continue

        if "-language" in launch_options:
            data["UserLocalConfigStore"]["Software"]["Valve"]["Steam"]["apps"][base.STEAM_DOTA_ID]["LaunchOptions"] = (
                _remove_lang_arg(launch_options, config.get_locale())
            )
            with utils.open_utf8(vdf_path, "w") as file:
                vdf.dump(data, file, pretty=True)
            successful_ids.append(steam_id)

    return successful_ids

```

</details>

## `find_library_from_vdf(steam_root)`

Find the Dota2 library from VDF

<details open><summary>Source</summary>

```python
def find_library_from_vdf(steam_root: str) -> bool:
    "Find the Dota2 library from VDF"
    try:
        if (
            steam_root
            and steam_root != "."  # ?
            and os.path.exists(reg_path := os.path.join(steam_root, "config", "libraryfolders.vdf"))
        ):
            with utils.open_utf8R(os.path.join(reg_path)) as dump:
                vdf_data = vdf.load(dump)

            paths = []
            for folder_key in vdf_data.get("libraryfolders", {}):
                folder = vdf_data["libraryfolders"][folder_key]
                # brute
                if "path" in folder:
                    paths.append(folder["path"])

            for path in paths:
                if os.path.exists(os.path.join(path, base.DOTA_EXECUTABLE_PATH)) or os.path.exists(
                    os.path.join(path, base.DOTA_EXECUTABLE_PATH_FALLBACK)
                ):
                    config.set("steam_library", path)
                    return True
        return False

    except Exception:
        log.write_warning("Error reading libraryfolders.vdf")
        config.set("steam_library", "")
        return False

```

</details>

## `get_steam_root_path()`

Get steam root path via
Windows: registry, default
Linux: default(`.local/share/Steam` for most major distrubitions)
MacOS: default

<details open><summary>Source</summary>

```python
def get_steam_root_path():
    """
    Get steam root path via
    Windows: registry, default
    Linux: default(`.local/share/Steam` for most major distrubitions)
    MacOS: default
    """
    steam_root = config.get("steam_root", "")

    if steam_root and os.path.exists(steam_root):
        return steam_root

    found_path = ""
    # registry
    if base.is_win:
        with utils.try_pass():
            import winreg

            # Prefer the 32-bit view (where Steam installs on x64), then fall back to the 64-bit view.
            hkey = None
            try:
                hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
            except OSError:
                try:
                    hkey = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Valve\Steam",
                        access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                    )
                except OSError:
                    hkey = None
            if hkey is not None:
                try:
                    steam_path = winreg.QueryValueEx(hkey, "InstallPath")[0]
                    if os.path.exists(steam_path):
                        found_path = steam_path
                finally:
                    hkey.Close()

    # defaults
    if not found_path and os.path.exists(base.STEAM_DEFAULT_INSTALLATION_PATH):
        found_path = base.STEAM_DEFAULT_INSTALLATION_PATH

    if found_path:
        config.set("steam_root", found_path)
        config.set("steam_library", found_path)  # assume, will be checked anyway
        return found_path

    return ""

```

</details>

## `is_steam_running()`

Check if Steam process exists (cross-platform).

<details open><summary>Source</summary>

```python
def is_steam_running():
    """Check if Steam process exists (cross-platform)."""
    try:
        if base.is_win:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
                capture_output=True,
                text=True,
                timeout=5,
                **_SUBPROCESS_HIDE,
            )
            return "steam.exe" in result.stdout
        elif base.is_mac:
            result = subprocess.run(["pgrep", "-i", "Steam"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        else:
            result = subprocess.run(["pgrep", "-x", "steam"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
    except Exception:
        return False

```

</details>

## `wait_steam_exit(timeout)`

Poll until Steam process exits. Returns True if exited, False on timeout.

<details open><summary>Source</summary>

```python
def wait_steam_exit(timeout: int = 30) -> bool:
    """Poll until Steam process exits. Returns True if exited, False on timeout."""
    deadline = time.time() + timeout
    max_iters = timeout
    iters = 0
    while time.time() < deadline and iters < max_iters:
        if not is_steam_running():
            return True
        time.sleep(1)
        iters += 1
    return False

```

</details>

## `launch_steam()`

Launch Steam silently. Returns True if launched.

<details open><summary>Source</summary>

```python
def launch_steam():
    """Launch Steam silently. Returns True if launched."""
    if not steam_executable_path or not os.path.exists(steam_executable_path):
        return False
    try:
        subprocess.Popen(
            [steam_executable_path, "-silent"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **_SUBPROCESS_HIDE
        )
        return True
    except Exception:
        return False

```

</details>

## `kill_steam()`

Request Steam to exit gracefully. Returns True if request sent.

<details open><summary>Source</summary>

```python
def kill_steam():
    """Request Steam to exit gracefully. Returns True if request sent."""
    if not steam_executable_path or not os.path.exists(steam_executable_path):
        return False
    try:
        subprocess.Popen(
            [steam_executable_path, "-exitsteam"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_SUBPROCESS_HIDE,
        )
        return True
    except Exception:
        return False

```

</details>

## `_resolve_locale(locale)`

Resolve the effective Steam locale, applying Minify's locale aliases.

<details open><summary>Source</summary>

```python
def _resolve_locale(locale: str | None = None) -> str:
    """Resolve the effective Steam locale, applying Minify's locale aliases."""
    if locale is None:
        return config.get_locale()
    from core import constants

    return constants.resolve_locale(locale)

```

</details>

## `_ensure_app_data(data)`

Build the apps[app_id] path into data, returning the app's config dict.

<details open><summary>Source</summary>

```python
def _ensure_app_data(data: dict[str, Any]) -> dict[str, Any]:
    """Build the apps[app_id] path into data, returning the app's config dict."""
    node = data
    for key in ("UserLocalConfigStore", "Software", "Valve", "Steam", "apps"):
        node = node.setdefault(key, {})
    return node.setdefault(str(base.STEAM_DOTA_ID), {})

```

</details>

## `_read_launch_state(root, steam_id, locale)`

Read one account's localconfig.vdf and classify the required action.

Returns (status, vdf_path, data, new_options, launch_options):

  - status: 'no_vdf' | 'no_dota_data' | 'already_set' | 'needs_change' | 'corrupt'
  - vdf_path: path of the localconfig.vdf
  - data: parsed VDF root (None unless status in ('needs_change', 'corrupt'))
  - new_options: rewritten launch options (None unless status in ('needs_change', 'corrupt'))
  - launch_options: current LaunchOptions string

<details open><summary>Source</summary>

```python
def _read_launch_state(
    root: str, steam_id: str, locale: str
) -> tuple[str, str, dict[str, Any] | None, str | None, str]:
    """Read one account's localconfig.vdf and classify the required action.

    Returns (status, vdf_path, data, new_options, launch_options):
      - status: 'no_vdf' | 'no_dota_data' | 'already_set' | 'needs_change' | 'corrupt'
      - vdf_path: path of the localconfig.vdf
      - data: parsed VDF root (None unless status in ('needs_change', 'corrupt'))
      - new_options: rewritten launch options (None unless status in ('needs_change', 'corrupt'))
      - launch_options: current LaunchOptions string
    """
    vdf_path = os.path.join(root, "userdata", steam_id, "config", "localconfig.vdf")
    if not os.path.exists(vdf_path):
        return "no_vdf", vdf_path, None, None, ""
    try:
        with utils.open_utf8R(vdf_path) as f:
            data = vdf.load(f)
    except Exception:
        # Corrupt/unreadable file (e.g. null-filled placeholder). There is no
        # data to preserve, so rebuild a minimal valid VDF on write instead of
        # failing. The original is backed up by the write path.
        data = {}
        _ensure_app_data(data)
        return "corrupt", vdf_path, data, f"-language {locale} {_remove_lang_arg('')}", ""
    try:
        app_data = _vdf_get_ci(data, "UserLocalConfigStore", "Software", "Valve", "Steam", "apps", base.STEAM_DOTA_ID)
    except KeyError:
        return "no_dota_data", vdf_path, None, None, ""

    launch_options = app_data.get("LaunchOptions", "")
    parsed = shlex.split(launch_options.strip()) if launch_options.strip() else []
    lang_values = []
    it = iter(parsed)
    for t in it:
        if t == "-language":
            val = next(it, None)
            if val is not None:
                lang_values.append(val)

    if lang_values == [locale]:
        return "already_set", vdf_path, None, None, launch_options
    return "needs_change", vdf_path, data, f"-language {locale} {_remove_lang_arg(launch_options)}", launch_options

```

</details>

## `check_launch_options(steam_ids, locale)`

Read-only report of per-account launch-option status. Never writes.

Returns list of dicts with per-account result. Never raises.

<details open><summary>Source</summary>

```python
def check_launch_options(steam_ids: list[str], locale: str | None = None) -> list[LaunchStatus]:
    """Read-only report of per-account launch-option status. Never writes.

    Returns list of dicts with per-account result. Never raises.
    """
    locale = _resolve_locale(locale)
    if not locale or not steam_ids:
        return []
    root = config.get("steam_root")
    if not root:
        return [{"steam_id": sid, "name": "?", "status": "no_steam_root"} for sid in steam_ids]

    output.add_text("&checking_launch_options")
    accounts = {a["id"]: a["name"] for a in get_steam_accounts()}
    results = []
    for steam_id in steam_ids:
        name = accounts.get(steam_id, "?")
        status, _path, _data, new_options, launch_options = _read_launch_state(root, steam_id, locale)
        if status == "corrupt":
            # Corrupt files are reported as needs_change; a rebuild is expected.
            status = "needs_change"
        result = {"steam_id": steam_id, "name": name, "status": status}
        if status == "already_set" and launch_options:
            result["launch_options"] = launch_options
        elif status == "needs_change" and new_options:
            result["launch_options"] = new_options
        results.append(result)
    if results and all(r["status"] == "already_set" for r in results):
        output.add_detail("&launch_options_already_set")
    return results

```

</details>

## `_apply_launch_options(steam_ids, locale)`

Write -language <locale> to launch options for given steam_ids.

Only writes where the value differs; expects Steam to be shut down so the
change can't be clobbered by Steam's in-memory flush. Never raises.

<details open><summary>Source</summary>

```python
def _apply_launch_options(steam_ids: list[str], locale: str | None = None) -> list[LaunchStatus]:
    """Write -language <locale> to launch options for given steam_ids.

    Only writes where the value differs; expects Steam to be shut down so the
    change can't be clobbered by Steam's in-memory flush. Never raises.
    """
    locale = _resolve_locale(locale)
    if not locale or not steam_ids:
        return []
    root = config.get("steam_root")
    if not root:
        return [{"steam_id": sid, "name": "?", "status": "no_steam_root"} for sid in steam_ids]

    accounts = {a["id"]: a["name"] for a in get_steam_accounts()}
    results = []

    for steam_id in steam_ids:
        name = accounts.get(steam_id, "?")
        status, vdf_path, data, new_options, launch_options = _read_launch_state(root, steam_id, locale)

        if status == "no_vdf":
            results.append({"steam_id": steam_id, "name": name, "status": "no_vdf"})
            continue
        if status == "no_dota_data":
            results.append({"steam_id": steam_id, "name": name, "status": "no_dota_data"})
            continue
        if status == "already_set":
            results.append(
                {"steam_id": steam_id, "name": name, "status": "already_set", "launch_options": launch_options}
            )
            continue

        output.add_text("&discrepancy_launch_options", name, locale)
        try:
            if status == "corrupt":
                # Preserve the unreadable original before replacing it, in case
                # Steam later rebuilds this account's config from scratch.
                shutil.copy2(vdf_path, vdf_path + ".minify_bak")
            assert data is not None, "launch-option data must be present for needs_change/corrupt status"
            app_data = _vdf_get_ci(
                data, "UserLocalConfigStore", "Software", "Valve", "Steam", "apps", base.STEAM_DOTA_ID
            )
            app_data["LaunchOptions"] = new_options
            tmp = vdf_path + ".tmp"
            with utils.open_utf8R(tmp, "w") as f:
                vdf.dump(data, f, pretty=True)
            os.replace(tmp, vdf_path)
            results.append({"steam_id": steam_id, "name": name, "status": "ok", "launch_options": new_options})
        except PermissionError:
            results.append({"steam_id": steam_id, "name": name, "status": "permission_error"})
        except Exception:
            results.append({"steam_id": steam_id, "name": name, "status": "error"})

    return results

```

</details>

## `apply_and_restart_steam(steam_ids, locale)`

Apply launch options, restart Steam only if changes are needed.

Detects changes read-only first so Steam is only restarted when required;
the single write happens after Steam has fully exited, so Steam's shutdown
flush of localconfig.vdf cannot clobber it.

Returns dict with:

  - apply_results: list of per-account results
  - restart_needed: bool — True when a Steam restart was required and performed
  - steam_killed: bool
  - steam_exited: bool
  - steam_launched: bool

<details open><summary>Source</summary>

```python
def apply_and_restart_steam(steam_ids: list[str], locale: str | None = None) -> dict[str, list[LaunchStatus] | bool]:
    """Apply launch options, restart Steam only if changes are needed.

    Detects changes read-only first so Steam is only restarted when required;
    the single write happens after Steam has fully exited, so Steam's shutdown
    flush of localconfig.vdf cannot clobber it.

    Returns dict with:
      - apply_results: list of per-account results
      - restart_needed: bool — True when a Steam restart was required and performed
      - steam_killed: bool
      - steam_exited: bool
      - steam_launched: bool
    """
    result = {
        "apply_results": [],
        "restart_needed": False,
        "steam_killed": False,
        "steam_exited": False,
        "steam_launched": False,
    }

    locale = _resolve_locale(locale)
    if locale and steam_ids:
        result["apply_results"] = check_launch_options(steam_ids, locale)
        if all(r.get("status") == "already_set" for r in result["apply_results"]):
            return result

    result["restart_needed"] = True
    steam_was_running = is_steam_running()
    if steam_was_running:
        result["steam_killed"] = kill_steam()
        if result["steam_killed"]:
            result["steam_exited"] = wait_steam_exit(timeout=30)
    else:
        result["steam_killed"] = True
        result["steam_exited"] = True

    result["apply_results"] = _apply_launch_options(steam_ids, locale)
    result["steam_launched"] = launch_steam()
    return result

```

</details>

## `ensure_paths_resolved()`

Prompts the user to select their Steam directory if it wasn't found automatically.
Must be called after the pywebview window exists (uses modal + native file dialog).

<details open><summary>Source</summary>

```python
def ensure_paths_resolved():
    """
    Prompts the user to select their Steam directory if it wasn't found automatically.
    Must be called after the pywebview window exists (uses modal + native file dialog).
    """
    init_steam()
    global ROOT, LIBRARY, steam_executable_path
    if ROOT:
        return True

    if base.HEADLESS:
        output.add_text(
            "&steam_not_found_instructions",
            "Steam installation not found. Set 'steam_root' and 'steam_library' in config/minify_config.json",
            msg_type="error",
        )
        return False

    import webview

    if not webview.windows:
        return False

    from ui import localization, modal_shared

    loc = localization.localization_dict
    modal_shared.show(
        title=loc.get("filedialog_steam_modal_title", "Steam Not Found"),
        messages=[
            loc.get(
                "filedialog_steam_modal_msg",
                "We couldn't find your Steam installation. Please select your Steam directory.",
            )
        ],
        buttons=[{"label": loc.get("filedialog_steam_modal_btn", "Select Steam Directory")}],
    )

    selected = webview.windows[0].create_file_dialog(
        webview.FileDialog.FOLDER,
    )
    if not selected:
        return False

    root = os.path.normpath(selected[0])
    config.set("steam_root", root)
    find_library_from_vdf(root)
    ROOT = root
    LIBRARY = config.get("steam_library") or root
    config.set("steam_library", LIBRARY)

    if base.is_win:
        steam_executable_path = os.path.join(ROOT, "steam.exe")
    elif base.is_linux or base.is_mac:
        steam_executable_path = os.path.join(ROOT, "steam")
    else:
        steam_executable_path = ""

    if not config.get("steam_id"):
        for account in get_steam_accounts():
            config.set("steam_id", account["id"])
            break

    return True

```

</details>

## `init_steam()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def init_steam():
    global ROOT, LIBRARY, steam_executable_path
    ROOT = get_steam_root_path()
    if ROOT:
        _lib = config.get("steam_library", "")
        if not os.path.exists(os.path.join(_lib, base.DOTA_EXECUTABLE_PATH)):
            find_library_from_vdf(ROOT)
        current_steam_id = config.get("steam_id")
        if not current_steam_id:
            for account in get_steam_accounts():
                config.set("steam_id", account["id"])
                break

    LIBRARY = config.get("steam_library") or ""

    if not LIBRARY:
        output.add_text("&steam_library_not_found_terminal", msg_type="warning")

    if base.is_win:
        steam_executable_path = os.path.join(ROOT, "steam.exe")
    elif base.is_linux:
        steam_executable_path = os.path.join(ROOT, "steam")
    elif base.is_mac:
        steam_executable_path = os.path.join(ROOT, "steam")
    else:
        steam_executable_path = ""

```

</details>

## `_loginusers_personas()`

Map account id -> persona name from loginusers.vdf (authoritative across accounts).

<details open><summary>Source</summary>

```python
def _loginusers_personas():
    """Map account id -> persona name from loginusers.vdf (authoritative across accounts)."""
    personas = {}
    path = os.path.join(ROOT, "config", "loginusers.vdf")
    if not os.path.exists(path):
        return personas
    try:
        with utils.open_utf8R(path) as f:
            data = vdf.load(f)
        for steam_id, info in data.get("users", {}).items():
            try:
                account_id = str(int(steam_id) - 76561197960265728)
            except (TypeError, ValueError):
                continue
            name = info.get("PersonaName")
            if name:
                personas[account_id] = name
    except Exception:
        log.write_warning("Failed to read loginusers.vdf")
    return personas

```

</details>

## `get_steam_accounts()`

Get all users that have Dota2 data

<details open><summary>Source</summary>

```python
def get_steam_accounts():
    "Get all users that have Dota2 data"
    accounts = []
    if not ROOT or not os.path.exists(os.path.join(ROOT, "userdata")):
        return accounts

    personas = _loginusers_personas()
    try:
        user_ids = sorted(
            [
                x
                for x in os.listdir(os.path.join(ROOT, "userdata"))
                if x.isdigit() and os.path.isdir(os.path.join(ROOT, "userdata", x))
            ],
            key=lambda x: int(x),
        )
        for user_id in user_ids:
            if not os.path.exists(os.path.join(ROOT, "userdata", user_id, base.STEAM_DOTA_ID)):
                continue

            name = personas.get(user_id, "?")
            if name == "?":
                localconfig_path = os.path.join(ROOT, "userdata", user_id, "config", "localconfig.vdf")
                if os.path.exists(localconfig_path):
                    try:
                        with utils.open_utf8R(localconfig_path) as f:
                            data = vdf.load(f)
                            friends = data.get("UserLocalConfigStore", {}).get("friends", {})
                            name = friends.get("PersonaName", "?")
                    except Exception:
                        name = "?"
            accounts.append({"id": user_id, "name": name})
    except Exception:
        log.write_warning("Failed to fetch steam accounts")

    return accounts

```

</details>
