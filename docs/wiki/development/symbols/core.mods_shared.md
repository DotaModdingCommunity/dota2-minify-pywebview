# core.mods_shared

Shared mod scanning logic

## `_read_states_from_disk()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def _read_states_from_disk() -> dict[str, Any]:
    if not os.path.exists(base.mods_config_dir):
        return {}
    try:
        with utils.open_utf8(base.mods_config_dir) as file:
            data = jsonc.load(file)
        return {mod: enabled for mod, enabled in data.items() if enabled is True}
    except Exception:
        backup_path = base.mods_config_dir + ".corrupt"
        try:
            shutil.copy2(base.mods_config_dir, backup_path)
            message = f"Failed to read mod states; corrupt file backed up to {backup_path}"
        except Exception:
            message = "Failed to read mod states"
        log.write_warning(message, show_traceback=False)
        return {}

```

</details>

## `_write_states_to_disk(states)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def _write_states_to_disk(states: dict[str, Any]) -> None:
    tmp = f"{base.mods_config_dir}.tmp.{os.getpid()}.{threading.get_ident()}"
    with _file_lock:
        try:
            merged = _read_states_from_disk()
            merged.update(states)
            for mod in get_always_on_mods():
                merged[mod] = True
            merged = {mod: enabled for mod, enabled in merged.items() if enabled is True}
            with utils.open_utf8(tmp, "w") as file:
                jsonc.dump(merged, file, indent=2)
            for _ in range(3):
                try:
                    os.replace(tmp, base.mods_config_dir)
                    break
                except OSError:
                    time.sleep(0.1)
        except Exception:
            log.write_warning("Failed to save mod states")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

```

</details>

## `get_always_on_mods()`

Names of mods marked `"always": true` in their manifest (never disabled).

<details open><summary>Source</summary>

```python
def get_always_on_mods() -> set[str]:
    """Names of mods marked `"always": true` in their manifest (never disabled)."""
    global _always_on_mods
    with _always_on_lock:
        if _always_on_mods is None:
            from patch import manifest_utils

            result = set()
            if os.path.isdir(base.mods_dir):
                for mod in os.listdir(base.mods_dir):
                    mod_path = os.path.join(base.mods_dir, mod)
                    if os.path.isdir(mod_path) and manifest_utils.get_mod(mod_path).get("always", False):
                        result.add(mod)
            _always_on_mods = result
        return _always_on_mods

```

</details>

## `get_state(mod)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_state(mod: str) -> bool:
    global _state_cache
    if mod in get_always_on_mods():
        return True
    with _state_lock:
        cache = _state_cache
        if cache is None:
            cache = _read_states_from_disk()
            _state_cache = cache
        return cache.get(mod, False)

```

</details>

## `set_state(mod, value)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def set_state(mod: str, value: bool) -> None:
    global _state_cache
    if mod in get_always_on_mods():
        value = True
    with _state_lock:
        cache = _state_cache
        if cache is None:
            cache = _read_states_from_disk()
            _state_cache = cache
        if value:
            cache[mod] = True
        else:
            cache.pop(mod, None)
    _write_states_to_disk({mod: value})

```

</details>

## `set_state_batch(states)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def set_state_batch(states: dict[str, bool]) -> None:
    global _state_cache
    always = get_always_on_mods()
    states = {mod: True if mod in always else value for mod, value in states.items()}
    with _state_lock:
        cache = _state_cache
        if cache is None:
            cache = _read_states_from_disk()
            _state_cache = cache
        for mod, value in states.items():
            if value:
                cache[mod] = True
            else:
                cache.pop(mod, None)
    _write_states_to_disk(states)

```

</details>

## `enforce_locale_mod_states()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def enforce_locale_mod_states():
    from core import config, constants

    locale = config.get("output_locale", "english")
    for required_mod in constants.LOCALE_MOD_REQUIREMENTS.get(locale, []):
        set_state(required_mod, True)

```

</details>

## `scan_mods(force)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def scan_mods(force: bool = False) -> None:
    global _scanned, _state_cache, _always_on_mods
    if force:
        with _state_lock:
            _state_cache = None
        _always_on_mods = None
    if _scanned and not force:
        return

    from patch import manifest_utils

    global mods_with_order, visually_available_mods, mod_dependencies_list, mod_conflicts_list

    if not os.path.exists(base.mods_dir):
        os.makedirs(base.mods_dir, exist_ok=True)

    _with_order = []
    _available = []
    _dependencies = []
    _conflicts = []

    for mod in sorted(os.listdir(base.mods_dir), key=str.casefold):
        mod_path = os.path.join(base.mods_dir, mod)
        if not mod.startswith("_"):
            if os.path.isdir(mod_path):
                blacklist_exist = os.path.exists(os.path.join(mod_path, "blacklist.txt"))
                cfg = manifest_utils.get_mod(mod_path)
                order = cfg.get("order", 1)
                dependencies = cfg.get("dependencies", None)
                conflicts = cfg.get("conflicts", None)
                visual = cfg.get("visual", True)
                if visual:
                    _available.append(mod)
                if dependencies is not None:
                    _dependencies.append({mod: dependencies})
                if conflicts is not None:
                    _conflicts.append({mod: conflicts})

                if blacklist_exist and not cfg:
                    _with_order.append({mod: 2})
                else:
                    _with_order.append({mod: order})

            elif mod.endswith(".vpk"):
                _available.append(mod)
                _with_order.append({mod: 1})

    temp_sorted = sorted(_with_order, key=lambda d: list(d.values())[0])
    _with_order = [list(d.keys())[0] for d in temp_sorted]

    with _lists_lock:
        mods_with_order[:] = _with_order
        visually_available_mods[:] = _available
        mod_dependencies_list[:] = _dependencies
        mod_conflicts_list[:] = _conflicts
    _scanned = True

```

</details>
