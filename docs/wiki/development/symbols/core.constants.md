# core.constants

Variables that depend on 3rd parties

## `init_paths()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def init_paths():
    global rescomp_override
    global minify_dota_compile_input_path, minify_dota_compile_output_path, dota_resource_compiler_path
    global minify_dota_tools_required_path, minify_default_dota_pak_output_path
    global minify_dota_possible_language_output_paths, dota2_tools_executable
    global dota_game_pak_path, dota_core_pak_path, dota_steam_inf_path, dota_tools_paths
    global dota_tools_extraction_paths

    rescomp_override = os.path.exists(base.rescomp_override_dir)
    minify_dota_compile_input_path = os.path.join(
        steam.LIBRARY, "steamapps", "common", "dota 2 beta", "content", "dota_addons", "minify"
    )
    minify_dota_compile_output_path = os.path.join(
        steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_addons", "minify"
    )
    dota_resource_compiler_path = os.path.join(
        steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "bin", "win64", "resourcecompiler.exe"
    )
    minify_dota_tools_required_path = os.path.join(
        steam.LIBRARY, "steamapps", "common", "dota 2 beta", "content", "dota_dutch"
    )
    minify_default_dota_pak_output_path = os.path.join(
        steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_dutch"
    )
    minify_dota_possible_language_output_paths = [
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_brazilian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_bulgarian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_czech"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_danish"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_dutch"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_finnish"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_french"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_german"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_greek"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_hungarian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_italian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_japanese"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_koreana"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_latam"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_norwegian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_polish"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_portuguese"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_romanian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_russian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_schinese"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_spanish"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_swedish"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_tchinese"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_thai"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_turkish"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_ukrainian"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota_vietnamese"),
    ]
    dota2_tools_executable = os.path.join(steam.LIBRARY, base.DOTA_TOOLS_EXECUTABLE_PATH)
    dota_game_pak_path = os.path.join(
        steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota", "pak01_dir.vpk"
    )
    dota_core_pak_path = os.path.join(
        steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "core", "pak01_dir.vpk"
    )
    dota_steam_inf_path = os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota", "steam.inf")
    dota_tools_paths = [
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "bin"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "core"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota", "bin"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota", "tools"),
        os.path.join(steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota", "gameinfo.gi"),
    ]
    dota_tools_extraction_paths = [
        os.path.join(base.rescomp_override_dir, "game", "bin"),
        os.path.join(base.rescomp_override_dir, "game", "core"),
        os.path.join(base.rescomp_override_dir, "game", "dota", "bin"),
        os.path.join(base.rescomp_override_dir, "game", "dota", "tools"),
        os.path.join(base.rescomp_override_dir, "game", "dota", "gameinfo.gi"),
    ]

    recalc_rescomp_dirs()

```

</details>

## `recalc_rescomp_dirs()`

Swaps the variables for resourcecompiler.exe when extracted

<details open><summary>Source</summary>

```python
def recalc_rescomp_dirs():
    "Swaps the variables for resourcecompiler.exe when extracted"
    global minify_dota_compile_input_path, minify_dota_compile_output_path, dota_resource_compiler_path
    if rescomp_override:
        minify_dota_compile_input_path = os.path.join(base.rescomp_override_dir, "content", "dota_addons", "minify")
        minify_dota_compile_output_path = os.path.join(base.rescomp_override_dir, "game", "dota_addons", "minify")
        dota_resource_compiler_path = os.path.join(
            base.rescomp_override_dir, "game", "bin", "win64", "resourcecompiler.exe"
        )

```

</details>

## `resolve_locale(locale)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def resolve_locale(locale: str) -> str:
    return LOCALE_ALIASES.get(locale, locale)

```

</details>

## Variables

### `LOCALE_ALIASES`

<details open><summary>Source</summary>

```python
LOCALE_ALIASES: dict[str, str] = {
    "english": "dutch",
}

```

</details>

### `LOCALE_MOD_REQUIREMENTS`

<details open><summary>Source</summary>

```python
LOCALE_MOD_REQUIREMENTS: dict[str, list[str]] = {
    "english": ["#English Fix"],
}

```

</details>

### `LOCALE_ALIASES`

<details open><summary>Source</summary>

```python
LOCALE_ALIASES = {
    "english": "dutch",
}

```

</details>

### `LOCALE_MOD_REQUIREMENTS`

<details open><summary>Source</summary>

```python
LOCALE_MOD_REQUIREMENTS = {
    "english": ["#English Fix"],
}

```

</details>

### `minify_output_list`

<details open><summary>Source</summary>

```python
minify_output_list = [
    "english",
    "brazilian",
    "bulgarian",
    "czech",
    "danish",
    "dutch",
    "finnish",
    "french",
    "german",
    "greek",
    "hungarian",
    "italian",
    "japanese",
    "koreana",
    "latam",
    "norwegian",
    "polish",
    "portuguese",
    "romanian",
    "russian",
    "schinese",
    "spanish",
    "swedish",
    "tchinese",
    "thai",
    "turkish",
    "ukrainian",
    "vietnamese",
]

```

</details>

### `minify_output_names`

<details open><summary>Source</summary>

```python
minify_output_names: dict[str, str] = {
    "english": "English",
    "brazilian": "Portuguese (Brazil)",
    "bulgarian": "Bulgarian",
    "czech": "Czech",
    "danish": "Danish",
    "dutch": "Dutch",
    "finnish": "Finnish",
    "french": "French",
    "german": "German",
    "greek": "Greek",
    "hungarian": "Hungarian",
    "italian": "Italian",
    "japanese": "Japanese",
    "koreana": "Korean",
    "latam": "Spanish (Latin America)",
    "norwegian": "Norwegian",
    "polish": "Polish",
    "portuguese": "Portuguese",
    "romanian": "Romanian",
    "russian": "Russian",
    "schinese": "Chinese (Simplified)",
    "spanish": "Spanish (Spain)",
    "swedish": "Swedish",
    "tchinese": "Chinese (Traditional)",
    "thai": "Thai",
    "turkish": "Turkish",
    "ukrainian": "Ukrainian",
    "vietnamese": "Vietnamese",
}

```

</details>

### `s2v_cli_ver`

<details open><summary>Source</summary>

```python
s2v_cli_ver = "18.0"

```

</details>

### `rg_ver`

<details open><summary>Source</summary>

```python
rg_ver = "15.1.0"

```

</details>

### `mods_with_order`

<details open><summary>Source</summary>

```python
mods_with_order = mods_shared.mods_with_order

```

</details>

### `visually_available_mods`

<details open><summary>Source</summary>

```python
visually_available_mods = mods_shared.visually_available_mods

```

</details>

### `mod_dependencies_list`

<details open><summary>Source</summary>

```python
mod_dependencies_list = mods_shared.mod_dependencies_list

```

</details>

### `mod_conflicts_list`

<details open><summary>Source</summary>

```python
mod_conflicts_list = mods_shared.mod_conflicts_list

```

</details>
