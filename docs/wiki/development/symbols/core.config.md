# core.config

JSON(C) config files

Interactions with main config and mod configs

## `read_json_file(path)`

*No documentation available.*

<details open><summary>Source</summary>

```python
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

```

</details>

## `write_json_file(path, data)`

*No documentation available.*

<details open><summary>Source</summary>

```python
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

```

</details>

## `get(key, default_value)`

*No documentation available.*

<details open><summary>Source</summary>

```python
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

```

</details>

## `set(key, value)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def set(key: str, value: Any) -> Any:
    global _config_cache
    with _config_lock:
        if _config_cache is None:
            _config_cache = read_json_file(base.main_config_file_dir)
        _config_cache[key] = value
        write_json_file(base.main_config_file_dir, _config_cache)
    return value

```

</details>

## `reset_all()`

Reset config to schema defaults, preserving the Steam paths the app uses.

Also clears per-mod config files (mod settings and mod-stored paths).

<details open><summary>Source</summary>

```python
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

```

</details>

## `get_locale(default)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_locale(default: str = "english") -> str:
    from core import constants

    return constants.resolve_locale(get("output_locale", default))

```

</details>

## `get_mod_config(mod_name)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_mod_config(mod_name: str) -> dict[str, Any]:
    if mod_name in _mod_config_cache:
        return _mod_config_cache[mod_name]
    path = os.path.join(base.config_dir, f"{mod_name} config.json")
    data = read_json_file(path)
    _mod_config_cache[mod_name] = data
    return data

```

</details>

## `save_mod_config(mod_name, data)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def save_mod_config(mod_name: str, data: dict[str, Any]) -> None:
    path = os.path.join(base.config_dir, f"{mod_name} config.json")
    write_json_file(path, data)
    _mod_config_cache[mod_name] = data

```

</details>

## `remove_mod_config(mod_name)`

Delete a mod's config file so it is treated as unconfigured (re-prompts in setup).

<details open><summary>Source</summary>

```python
def remove_mod_config(mod_name: str) -> None:
    """Delete a mod's config file so it is treated as unconfigured (re-prompts in setup)."""
    with _config_lock:
        _mod_config_cache.pop(mod_name, None)
    try:
        os.remove(os.path.join(base.config_dir, f"{mod_name} config.json"))
    except FileNotFoundError:
        pass

```

</details>

## `validate()`

Validate config against schema, apply defaults for missing/invalid keys.

<details open><summary>Source</summary>

```python
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

```

</details>
