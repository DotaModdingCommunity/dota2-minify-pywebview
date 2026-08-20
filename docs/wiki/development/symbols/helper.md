# helper

Dangling random functions

## `get_blank_file_extensions()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_blank_file_extensions() -> list[str]:
    extensions = []
    for file in os.listdir(base.blank_files_dir):
        extensions.append(os.path.splitext(file)[1])
    return extensions

```

</details>

## `get_output_path()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_output_path() -> str:
    locale = config.get_locale() or "dutch"
    for p in constants.minify_dota_possible_language_output_paths:
        if locale in p:
            return p
    return constants.minify_default_dota_pak_output_path

```

</details>

## `run_resource_compiler()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def run_resource_compiler() -> None:
    compile()

```

</details>

## `compile()`

A wrapper for the Dota 2 Resource Compiler.

<details open><summary>Source</summary>

```python
def compile() -> None:
    """
    A wrapper for the Dota 2 Resource Compiler.
    """
    with open(base.log_rescomp, "wb") as file:
        command = [
            constants.dota_resource_compiler_path,
            "-i",
            constants.minify_dota_compile_input_path + os.sep + "*",
            "-r",
        ]

        if not base.is_win:
            if shutil.which("wine") is None:
                raise RuntimeError(
                    "wine is required to run the Resource Compiler on Linux/macOS. Install wine — see the troubleshooting FAQ."
                )
            command.insert(0, "wine")

        rescomp = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # compiler complains if minify_dota_compile_input_path is empty
            creationflags=subprocess.CREATE_NO_WINDOW if base.is_win else 0,
        )
        if rescomp.stdout != b"":
            file.write(rescomp.stdout)
        if rescomp.returncode != 0:
            if rescomp.stderr != b"":
                file.write(rescomp.stderr)
            raise RuntimeError(f"Resource Compiler failed with exit code {rescomp.returncode}")

```

</details>

## `compile_assets(input_path, output_path, pak_path)`

resourcecompiler's friendly cousin
Automagically handles image compilation

<details open><summary>Source</summary>

```python
def compile_assets(input_path: str | None = None, output_path: str | None = None, pak_path: str | None = None) -> None:
    """
    resourcecompiler's friendly cousin
    Automagically handles image compilation
    """
    if not input_path:
        return
    if not output_path:
        output_path = os.path.join(os.path.dirname(input_path), "#Minify_compiled")

    input_abs = os.path.abspath(input_path)
    output_abs = os.path.abspath(output_path)
    if (
        output_abs == input_abs
        or output_abs.startswith(input_abs + os.sep)
        or input_abs.startswith(output_abs + os.sep)
    ):
        raise ValueError("output_path must not equal or contain input_path (it is cleared before compiling)")

    if os.path.exists(input_path):
        output.add_text("&compile_init", input_path)
        img_list = [str(f.relative_to(input_path)) for f in Path(input_path).rglob("*.png") if f.is_file()]
        ref_xml_path = os.path.join(input_path, f".minify_ref_{os.urandom(4).hex()}.xml")
        fs.remove_path(constants.minify_dota_compile_input_path, output_path)
        fs.create_dirs(constants.minify_dota_compile_input_path)

        with utils.open_utf8(ref_xml_path, "w") as file:
            file.write(create_img_ref_xml(img_list))

        try:
            for item in os.listdir(input_path):
                item_path = os.path.join(input_path, item)
                dest = os.path.join(constants.minify_dota_compile_input_path, item)
                if os.path.isdir(item_path):
                    shutil.copytree(item_path, dest)
                else:
                    shutil.copy2(item_path, dest)

            compile()

            fs.create_dirs(output_path)
            for item in os.listdir(constants.minify_dota_compile_output_path):
                src = os.path.join(constants.minify_dota_compile_output_path, item)
                dst = os.path.join(output_path, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            output.add_text("&compile_successful", output_path)

            if pak_path:
                vpk_file = vpk.new(output_path)
                vpk_file.save(pak_path)
                output.add_text("&compile_created_pak", pak_path)
        finally:
            ref_compiled = os.path.splitext(os.path.basename(ref_xml_path))[0] + ".vxml_c"
            fs.remove_path(
                constants.minify_dota_compile_input_path,
                constants.minify_dota_compile_output_path,
                ref_xml_path,
                os.path.join(output_path, ref_compiled),
            )
            fs.create_dirs(constants.minify_dota_tools_required_path)
    else:
        output.add_text("&compile_no_path")

```

</details>

## `create_img_ref_xml(img_path_list)`

Helper function to create reference XMLs for images

<details open><summary>Source</summary>

```python
def create_img_ref_xml(img_path_list: list[str]) -> str:
    "Helper function to create reference XMLs for images"
    xml_list = []
    for img_path in img_path_list:
        xml_list.append(f'\t\t\t<Image src="file://{img_path}" />')

    xml_joined = "\n".join(xml_list)
    return f"""<root>
    <Panel class="AddonLoadingRoot">
{xml_joined}
    </Panel>
</root>"""

```

</details>

## `exec_script(script_path, mod_name, order_name, terminal_output, mod_cfg)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def exec_script(
    script_path: str,
    mod_name: str,
    order_name: str,
    terminal_output: bool = True,
    mod_cfg: dict[str, Any] | None = None,
) -> Any:
    if not os.path.exists(script_path):
        return None
    if terminal_output:
        output.add_text("&script_execution", mod_name, order_name)
    result = exec_script_function(script_path, mod_name, "main", cfg=mod_cfg)
    if terminal_output:
        output.add_text("&script_success", mod_name, order_name, msg_type="success")
    return result

    return None

```

</details>

## `bulk_exec_script(order_name, terminal_output)`

Injects required mod instructions in bulk

`script_initial.py`
`script_after_decompile.py`
`script_after_recompile.py`
`script_after_patch.py`
`script_prelaunch.py`
`script_uninstall.py`

Note: `script_setup.py` and `script_utility.py` are not bulk-run — the former is
invoked during mod setup and the latter is loaded on demand via `exec_script_function`.

<details open><summary>Source</summary>

```python
def bulk_exec_script(order_name: str, terminal_output: bool = True) -> bool:
    """
    Injects required mod instructions in bulk

    `script_initial.py`
    `script_after_decompile.py`
    `script_after_recompile.py`
    `script_after_patch.py`
    `script_prelaunch.py`
    `script_uninstall.py`

    Note: `script_setup.py` and `script_utility.py` are not bulk-run — the former is
    invoked during mod setup and the latter is loaded on demand via `exec_script_function`.
    """
    bulk_name = f"script_{order_name}.py"
    any_ran = False
    for mod_name in mods_shared.mods_with_order:
        root = os.path.join(base.mods_dir, mod_name)
        if not os.path.exists(os.path.join(root, bulk_name)):
            continue
        cfg = manifest_utils.get_mod(root)

        if "browser" in cfg:
            continue

        always = cfg.get("always", False)

        if always or order_name in ["initial", "uninstall"] or mods_shared.get_state(mod_name):
            result = exec_script(
                os.path.join(root, bulk_name), mod_name, order_name, terminal_output=terminal_output, mod_cfg=cfg
            )
            if result:
                any_ran = True

    return any_ran

```

</details>

## `exec_script_function(script_path, mod_name, function_name, cfg)`

Executes a specific function from a Python script file

<details open><summary>Source</summary>

```python
def exec_script_function(
    script_path: str,
    mod_name: str,
    function_name: str = "main",
    cfg: dict[str, Any] | None = None,
) -> Any:
    """
    Executes a specific function from a Python script file
    """
    if os.path.exists(script_path):
        mod_dir = os.path.dirname(script_path)
        if cfg is None:
            cfg = manifest_utils.get_mod(mod_dir)
        if cfg.get("browser"):
            log.write_warning(f"Python script execution is disabled for browser mods: {mod_name}")
            return

        script_dir = os.path.dirname(script_path)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)

        module_name = f"mod_{os.path.splitext(os.path.basename(script_path))[0]}_{hash(script_path) & 0x7FFFFFFF:x}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load script module: {script_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            if sys.path and sys.path[0] == script_dir:
                sys.path.pop(0)

        func = getattr(module, function_name, None)
        if callable(func):
            return func()
        else:
            log.write_warning(f"Function '{function_name}' not found in {script_path}")
            return None
    else:
        log.write_warning(f"Script file not found: {script_path}")
        return None

```

</details>
